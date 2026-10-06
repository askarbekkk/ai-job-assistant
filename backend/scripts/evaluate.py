"""Evaluation — Section 12.

Recommendation quality (12.2): Precision@K of the system vs a keyword-only baseline.

    cd backend
    python -m scripts.evaluate ranking --resumes ../data/eval/resumes --labels ../data/eval/labels.csv
    python -m scripts.evaluate ranking ... --tune      # grid-search the 0.7 / 0.3 weights

  labels.csv: resume_id,job_id,relevant   (relevant = 1 or 0; ~20 postings per resume)
  resume_id is the file name without extension (resumes/r01.pdf -> r01).
  With two labelers per resume, merge their labels first (e.g. relevant only if both say 1).

Skill extraction check (12.3): extracted skills vs hand-marked skills.

    python -m scripts.evaluate extraction --resumes ../data/eval/resumes --gold ../data/eval/skills_gold.csv

  skills_gold.csv: resume_id,skills   (skills separated by ';')

Jobs are read from the database, so run the import script first.
"""

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean

from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import Job
from app.services import similarity
from app.services.extraction import extract_resume, llm_enabled
from app.services.matching import compare_skills, score_jobs
from app.services.pdf_text import extract_text
from app.services.skill_normalizer import get_normalizer


def load_resumes(folder: Path) -> dict[str, str]:
    texts = {}
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() == ".pdf":
            texts[path.stem] = extract_text(path.read_bytes())
        elif path.suffix.lower() == ".txt":
            texts[path.stem] = path.read_text(encoding="utf-8")
    if not texts:
        raise SystemExit(f"No .pdf or .txt resumes in {folder}")
    return texts


def precision_at_k(ranked: list[str], relevant: set[str], k: int) -> float:
    top = ranked[:k]
    return sum(1 for j in top if j in relevant) / len(top) if top else 0.0


# ---------------------------------------------------------------- ranking


def _read_labels(path: Path) -> dict[str, dict[str, int]]:
    labels: dict[str, dict[str, int]] = defaultdict(dict)
    with open(path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            labels[row["resume_id"].strip()][row["job_id"].strip().upper()] = int(row["relevant"])
    return labels


def evaluate_ranking(resumes_dir: Path, labels_path: Path, k: int, tune: bool) -> None:
    texts = load_resumes(resumes_dir)
    labels = _read_labels(labels_path)
    normalizer = get_normalizer()

    with SessionLocal() as db:
        all_jobs = db.scalars(select(Job)).all()
    if not all_jobs:
        raise SystemExit("No jobs in the database — run scripts.import_jobs first.")
    jobs_by_id = {j.job_id: j for j in all_jobs}
    job_keywords = {j.job_id: normalizer.extract_keywords(f"{j.title}\n{j.description}") for j in all_jobs}

    print(f"Extractor: {'llm' if llm_enabled() else 'keyword'} | similarity: {similarity.backend()} | K={k}\n")

    prepared = []  # (resume_id, skills, candidates, sims, relevant)
    for rid, job_labels in sorted(labels.items()):
        if rid not in texts:
            print(f"  ! no resume file for {rid}, skipped")
            continue
        candidates = [jobs_by_id[j] for j in job_labels if j in jobs_by_id]
        unknown = [j for j in job_labels if j not in jobs_by_id]
        if unknown:
            print(f"  ! {rid}: unknown job ids {unknown}")
        # IDF / embeddings over the whole collection, then keep the labeled ones.
        sims_all = dict(zip(jobs_by_id, similarity.similarities(texts[rid], None, all_jobs)))
        sims = [sims_all[j.job_id] for j in candidates]
        skills = extract_resume(texts[rid]).skills
        relevant = {j for j, v in job_labels.items() if v == 1}
        prepared.append((rid, skills, candidates, sims, relevant, normalizer.extract_keywords(texts[rid])))

    def run(w_skill: float, w_text: float) -> dict[str, float]:
        return {
            rid: precision_at_k(
                [m.job.job_id for m in score_jobs(skills, cands, sims, w_skill, w_text)], relevant, k
            )
            for rid, skills, cands, sims, relevant, _ in prepared
        }

    def baseline() -> dict[str, float]:
        result = {}
        for rid, _, cands, _, relevant, resume_kw in prepared:
            ranked = sorted(
                cands, key=lambda j: (-compare_skills(resume_kw, job_keywords[j.job_id]).overlap, j.job_id)
            )
            result[rid] = precision_at_k([j.job_id for j in ranked], relevant, k)
        return result

    system = run(settings.weight_skill, settings.weight_text)
    base = baseline()
    print(f"{'resume':<12}{'system P@'+str(k):>14}{'baseline P@'+str(k):>16}")
    for rid in system:
        print(f"{rid:<12}{system[rid]:>14.2f}{base[rid]:>16.2f}")
    print("-" * 42)
    print(f"{'MEAN':<12}{mean(system.values()):>14.3f}{mean(base.values()):>16.3f}")
    print(f"\nweights: skill={settings.weight_skill}, text={settings.weight_text}; target P@5 >= 0.6")

    if tune:
        print("\nWeight grid (w_text = 1 - w_skill):")
        grid = []
        for i in range(11):
            ws = i / 10
            score = mean(run(ws, 1 - ws).values())
            grid.append((score, ws))
            print(f"  w_skill={ws:.1f}  P@{k}={score:.3f}")
        # On ties prefer the weight closest to the current setting.
        best_score, best_ws = max(grid, key=lambda g: (g[0], -abs(g[1] - settings.weight_skill)))
        print(f"\nBest: w_skill={best_ws:.1f}, w_text={1 - best_ws:.1f}, P@{k}={best_score:.3f}")
        print("Note: tuning and reporting on the same resumes overestimates quality — "
              "tune on half of the resumes and report on the other half.")


# ---------------------------------------------------------------- extraction


def evaluate_extraction(resumes_dir: Path, gold_path: Path) -> None:
    texts = load_resumes(resumes_dir)
    normalizer = get_normalizer()
    gold: dict[str, set[str]] = {}
    with open(gold_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            skills = [s for s in row["skills"].split(";") if s.strip()]
            gold[row["resume_id"].strip()] = {s.lower() for s in normalizer.normalize_many(skills)}

    print(f"Extractor: {'llm' if llm_enabled() else 'keyword'}\n")
    print(f"{'resume':<12}{'gold':>6}{'found':>7}{'correct':>9}{'precision':>11}{'recall':>8}")
    tp_total = found_total = gold_total = 0
    for rid, gold_skills in sorted(gold.items()):
        if rid not in texts:
            print(f"  ! no resume file for {rid}, skipped")
            continue
        found = {s.lower() for s in extract_resume(texts[rid]).skills}
        tp = len(found & gold_skills)
        tp_total, found_total, gold_total = tp_total + tp, found_total + len(found), gold_total + len(gold_skills)
        p = tp / len(found) if found else 0.0
        r = tp / len(gold_skills) if gold_skills else 0.0
        print(f"{rid:<12}{len(gold_skills):>6}{len(found):>7}{tp:>9}{p:>11.2f}{r:>8.2f}")
        missed = sorted(gold_skills - found)
        if missed:
            print(f"{'':<12}missed: {', '.join(missed)}")
    p = tp_total / found_total if found_total else 0.0
    r = tp_total / gold_total if gold_total else 0.0
    f1 = 2 * p * r / (p + r) if p + r else 0.0
    print(f"\nTotal: {tp_total}/{gold_total} gold skills found; precision={p:.3f} recall={r:.3f} F1={f1:.3f}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("ranking")
    r.add_argument("--resumes", type=Path, required=True)
    r.add_argument("--labels", type=Path, required=True)
    r.add_argument("--k", type=int, default=5)
    r.add_argument("--tune", action="store_true")
    e = sub.add_parser("extraction")
    e.add_argument("--resumes", type=Path, required=True)
    e.add_argument("--gold", type=Path, required=True)
    args = p.parse_args()

    if args.cmd == "ranking":
        evaluate_ranking(args.resumes, args.labels, args.k, args.tune)
    else:
        evaluate_extraction(args.resumes, args.gold)


if __name__ == "__main__":
    main()
