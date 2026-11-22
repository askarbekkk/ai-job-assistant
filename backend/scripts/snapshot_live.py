"""Save a snapshot of real postings from Wanted, Jumpit and JobKorea to a CSV.

    cd backend
    python -m scripts.snapshot_live ../data/jobs_live.csv

The deployed app imports this file on start, so the job list is real from the first
visit; each resume upload then adds fresh postings on top. Re-run it to refresh.
Needs TAVILY_API_KEY in backend/.env.
"""

import argparse
import csv
from datetime import date
from pathlib import Path

from app.services import live_jobs
from scripts.import_jobs import FIELDS

# One search per common profile of the people this app is for.
PROFILES = [
    ["Python", "PyTorch", "LLM"],
    ["Python", "Deep Learning", "Computer Vision"],
    ["Python", "SQL", "Pandas"],
    ["SQL", "Tableau", "Data Analysis"],
    ["React", "TypeScript", "JavaScript"],
    ["Java", "Spring", "SQL"],
    ["Node.js", "TypeScript", "AWS"],
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("out", type=Path)
    args = p.parse_args()
    if not live_jobs.enabled():
        raise SystemExit("Set TAVILY_API_KEY in backend/.env first.")

    rows, seen = {}, set()
    for skills in PROFILES:
        found = live_jobs.find_postings(skills)
        for row in found:
            key = f"{row['company']}|{row['title']}".lower()  # re-posts share company + title
            if key not in seen and row["job_id"] not in rows:
                seen.add(key)
                rows[row["job_id"]] = row
        print(f"{' '.join(skills):40} {len(found):3} found, {len(rows):3} total")

    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in rows.values():
            w.writerow({**row, "collected_date": date.today().isoformat()})
    print(f"Wrote {len(rows)} postings to {args.out}")


if __name__ == "__main__":
    main()
