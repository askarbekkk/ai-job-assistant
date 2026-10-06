"""Import Script — clean · validate · load (Section 7).

    cd backend
    python -m scripts.import_jobs ../data/jobs_sample.csv            # upsert
    python -m scripts.import_jobs ../data/jobs.csv --replace         # wipe jobs first
    python -m scripts.import_jobs ../data/jobs.csv --dry-run         # only validate

Steps: read the team CSV (Google Sheets export) -> clean values and drop
duplicates -> extract required/preferred skills (Claude or keywords) ->
normalize skills -> upsert into the database -> write a ~10% spot-check sheet
for manual review of the extracted skills.

LLM results are cached in data/cache/job_skills.json, so re-running the import
does not pay for postings that were already processed.
"""

import argparse
import csv
import hashlib
import json
import random
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import delete, select

from app.config import PROJECT_DIR, settings
from app.crud import set_job_skills
from app.database import SessionLocal, init_db
from app.models import Job
from app.services import extraction, similarity

FIELDS = [
    "job_id", "company", "title", "employment_type", "location",
    "korean_required", "description", "source_url", "collected_date",
]

EMPLOYMENT_TYPES = {
    "internship": "Internship", "intern": "Internship", "인턴": "Internship", "인턴십": "Internship",
    "체험형 인턴": "Internship", "채용연계형 인턴": "Internship",
    "full-time": "Full-time", "full time": "Full-time", "fulltime": "Full-time", "정규직": "Full-time",
    "신입": "Full-time", "new grad": "Full-time", "entry-level": "Full-time", "entry level": "Full-time",
}

KOREAN_LEVELS = {
    "none": "None", "not required": "None", "no": "None", "not needed": "None", "무관": "None", "불필요": "None",
    "basic": "Basic", "beginner": "Basic", "intermediate": "Basic", "conversational": "Basic",
    "topik 1": "Basic", "topik 2": "Basic", "topik 3": "Basic", "topik 4": "Basic", "기초": "Basic",
    "fluent": "Fluent", "business": "Fluent", "advanced": "Fluent", "native": "Fluent",
    "topik 5": "Fluent", "topik 6": "Fluent", "필수": "Fluent", "능통": "Fluent", "원어민": "Fluent",
}


@dataclass
class Report:
    read: int = 0
    duplicates: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    imported: int = 0
    methods: dict[str, int] = field(default_factory=dict)
    cached: int = 0


def _clean_text(value) -> str:
    return re.sub(r"[ \t]+", " ", str(value or "")).strip()


def _parse_date(value: str) -> date | None:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y. %m. %d"):
        try:
            return datetime.strptime(value.rstrip("."), fmt).date()
        except ValueError:
            continue
    return None


def _dedupe_key(row: dict) -> str:
    url = row["source_url"].lower().rstrip("/")
    if url:
        return url
    return "|".join(row[k].lower() for k in ("company", "title", "location"))


def read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = [c for c in FIELDS if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"CSV is missing columns: {', '.join(missing)}. Use data/jobs_template.csv.")
        return list(reader)


def clean_rows(raw_rows: list[dict], report: Report) -> list[dict]:
    """Validate and normalize rows; drop duplicates. Invalid rows are reported, not guessed."""
    rows: list[dict] = []
    seen_keys: dict[str, str] = {}
    seen_ids: set[str] = set()

    for line_no, raw in enumerate(raw_rows, start=2):  # line 1 is the header
        report.read += 1
        row = {k: _clean_text(raw.get(k)) for k in FIELDS}
        row["description"] = str(raw.get("description") or "").strip()
        where = f"line {line_no} ({row['job_id'] or 'no id'})"

        missing = [k for k in ("company", "title", "description") if not row[k]]
        if missing:
            report.errors.append(f"{where}: empty {', '.join(missing)}")
            continue

        emp = EMPLOYMENT_TYPES.get(row["employment_type"].lower())
        if emp is None:
            report.errors.append(f"{where}: unknown employment_type '{row['employment_type']}'")
            continue
        row["employment_type"] = emp

        kor = KOREAN_LEVELS.get(row["korean_required"].lower())
        if kor is None:
            report.errors.append(
                f"{where}: unknown korean_required '{row['korean_required']}' (use None / Basic / Fluent)"
            )
            continue
        row["korean_required"] = kor

        if not row["location"]:
            row["location"] = "Unknown"
            report.warnings.append(f"{where}: empty location -> 'Unknown'")
        if not row["source_url"]:
            report.warnings.append(f"{where}: empty source_url")
        raw_date = row["collected_date"]
        row["collected_date"] = _parse_date(raw_date) if raw_date else None
        if raw_date and row["collected_date"] is None:
            report.warnings.append(f"{where}: cannot parse collected_date '{raw_date}'")

        key = _dedupe_key(row)
        if key in seen_keys:
            report.duplicates.append(f"{where}: duplicate of {seen_keys[key]}")
            continue

        job_id = row["job_id"].upper()
        if job_id and job_id in seen_ids:
            report.warnings.append(f"{where}: job_id {job_id} used twice -> new id assigned")
            job_id = ""
        row["job_id"] = job_id
        if job_id:
            seen_ids.add(job_id)
        seen_keys[key] = job_id or where
        rows.append(row)

    next_num = max((int(m.group(1)) for i in seen_ids if (m := re.fullmatch(r"J(\d+)", i))), default=0) + 1
    for row in rows:
        if not row["job_id"]:
            row["job_id"] = f"J{next_num:04d}"
            next_num += 1
    return rows


# ---------------------------------------------------------------- skills cache


def _cache_path() -> Path:
    return settings.cache_dir / "job_skills.json"


def _load_cache() -> dict:
    path = _cache_path()
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def _save_cache(cache: dict) -> None:
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    _cache_path().write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")


def _cache_key(description: str) -> str:
    return hashlib.sha256(f"{extraction.model_name()}\n{description}".encode("utf-8")).hexdigest()


def extract_skills(rows: list[dict], report: Report) -> None:
    use_llm = extraction.llm_enabled()
    cache = _load_cache() if use_llm else {}
    for i, row in enumerate(rows, start=1):
        key = _cache_key(row["description"])
        if use_llm and key in cache:
            row["required"], row["preferred"] = cache[key]["required"], cache[key]["preferred"]
            method = "llm"
            report.cached += 1
        else:
            result = extraction.extract_job_skills(row["description"])
            row["required"], row["preferred"], method = result.required, result.preferred, result.method
            if method == "llm":
                cache[key] = {"required": result.required, "preferred": result.preferred}
                _save_cache(cache)  # save as we go: a crash halfway keeps what was paid for
        report.methods[method] = report.methods.get(method, 0) + 1
        if use_llm and i % 10 == 0:
            print(f"  extracted {i}/{len(rows)}", file=sys.stderr)


def load_into_db(db, rows: list[dict], replace: bool, report: Report) -> list[Job]:
    if replace:
        db.execute(delete(Job))
        db.flush()
    jobs = []
    for row in rows:
        job = db.get(Job, row["job_id"]) or Job(job_id=row["job_id"])
        for k in ("company", "title", "employment_type", "location", "korean_required",
                  "description", "source_url", "collected_date"):
            setattr(job, k, row[k])
        job.embedding = None  # text may have changed
        db.add(job)
        set_job_skills(db, job, row["required"], row["preferred"])
        jobs.append(job)
    if jobs and similarity.backend() == "sbert":
        print(f"  computing embeddings for {len(jobs)} postings...", file=sys.stderr)
        vectors = similarity.encode([similarity.job_text(j) for j in jobs])
        for job, vector in zip(jobs, vectors):
            job.embedding = {"model": settings.embedding_model, "vector": vector}
    db.commit()
    report.imported = len(jobs)
    return jobs


def write_spot_check(rows: list[dict], path: Path, rate: float, seed: int) -> int:
    if not rows:
        return 0
    sample = random.Random(seed).sample(rows, max(1, round(len(rows) * rate)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["job_id", "title", "required_skills", "preferred_skills", "correct (y/n)", "missing or wrong skills"])
        for r in sorted(sample, key=lambda r: r["job_id"]):
            w.writerow([r["job_id"], r["title"], "; ".join(r["required"]), "; ".join(r["preferred"]), "", ""])
    return len(sample)


def run(csv_path: Path, replace: bool = False, dry_run: bool = False,
        spot_check_rate: float = 0.1, spot_check_out: Path | None = None, seed: int = 42) -> Report:
    report = Report()
    rows = clean_rows(read_csv(csv_path), report)
    if not dry_run:
        extract_skills(rows, report)
        init_db()
        with SessionLocal() as db:
            load_into_db(db, rows, replace, report)
        if spot_check_rate > 0:
            out = spot_check_out or PROJECT_DIR / "data" / "spot_check.csv"
            n = write_spot_check(rows, out, spot_check_rate, seed)
            report.warnings.append(f"spot-check sheet with {n} postings written to {out}")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("csv", type=Path)
    p.add_argument("--replace", action="store_true", help="delete all jobs before importing")
    p.add_argument("--dry-run", action="store_true", help="only validate and clean, do not write to the DB")
    p.add_argument("--spot-check-rate", type=float, default=0.1)
    p.add_argument("--spot-check-out", type=Path)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    print(f"Skill extraction: {'LLM (' + extraction.model_name() + ')' if extraction.llm_enabled() else 'keywords'}")
    report = run(args.csv, args.replace, args.dry_run, args.spot_check_rate, args.spot_check_out, args.seed)

    print(f"\nRows read:   {report.read}")
    print(f"Duplicates:  {len(report.duplicates)}")
    print(f"Invalid:     {len(report.errors)}")
    if not args.dry_run:
        print(f"Imported:    {report.imported}  (extraction: {report.methods}, from cache: {report.cached})")
    for title, items in (("Duplicates", report.duplicates), ("Errors", report.errors), ("Notes", report.warnings)):
        if items:
            print(f"\n{title}:")
            for item in items:
                print(f"  - {item}")


if __name__ == "__main__":
    main()
