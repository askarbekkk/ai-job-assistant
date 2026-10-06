"""Modules 3 & 4 — Matching Engine and Score & Skill Gap (Section 10).

1. Filter:          drop postings that fail location / job type / Korean level.
2. Skill overlap:   share of the job's required skills the user has.
3. Text similarity: cosine similarity of resume and posting (see similarity.py).
4. Final score:     Match = 100 * (w_skill * overlap + w_text * similarity).
5. Skill gap:       required skills of the posting minus the user's skills.
"""

from collections import Counter
from dataclasses import dataclass, field

from ..config import settings

KOREAN_LEVELS = ["None", "Basic", "Fluent"]
EMPLOYMENT_TYPES = ["Internship", "Full-time"]


@dataclass
class Filters:
    location: str | None = None
    employment_type: str | None = None
    # The user's own Korean level: postings requiring more than this are removed.
    korean_level: str | None = None


@dataclass
class SkillComparison:
    overlap: float
    matched: list[str]
    missing: list[str]
    missing_preferred: list[str] = field(default_factory=list)


@dataclass
class JobMatch:
    job: object
    score: float
    skill_overlap: float
    text_similarity: float
    matched_skills: list[str]
    missing_skills: list[str]
    missing_preferred: list[str]


def passes_filters(job, filters: Filters) -> bool:
    if filters.location and job.location.lower() != filters.location.lower():
        return False
    if filters.employment_type and job.employment_type.lower() != filters.employment_type.lower():
        return False
    if filters.korean_level in KOREAN_LEVELS:
        required = KOREAN_LEVELS.index(job.korean_required) if job.korean_required in KOREAN_LEVELS else 2
        if required > KOREAN_LEVELS.index(filters.korean_level):
            return False
    return True


def compare_skills(user_skills: list[str], required: list[str], preferred: list[str] = ()) -> SkillComparison:
    have = {s.lower() for s in user_skills}
    # A posting with no explicit required skills is judged on its preferred ones.
    target = list(required) or list(preferred)
    matched = [s for s in target if s.lower() in have]
    missing = [s for s in target if s.lower() not in have]
    missing_preferred = [s for s in preferred if s.lower() not in have and s not in missing]
    overlap = len(matched) / len(target) if target else 0.0
    return SkillComparison(overlap, matched, missing, missing_preferred)


def final_score(skill_overlap: float, text_similarity: float, w_skill: float, w_text: float) -> float:
    score = 100 * (w_skill * skill_overlap + w_text * text_similarity)
    return round(max(0.0, min(100.0, score)), 1)


def score_jobs(
    user_skills: list[str],
    jobs: list,
    sims: list[float],
    w_skill: float | None = None,
    w_text: float | None = None,
) -> list[JobMatch]:
    w_skill = settings.weight_skill if w_skill is None else w_skill
    w_text = settings.weight_text if w_text is None else w_text
    results = []
    for job, sim in zip(jobs, sims):
        cmp = compare_skills(user_skills, job.required_skills, job.preferred_skills)
        results.append(
            JobMatch(
                job=job,
                score=final_score(cmp.overlap, sim, w_skill, w_text),
                skill_overlap=round(cmp.overlap, 3),
                text_similarity=round(sim, 3),
                matched_skills=cmp.matched,
                missing_skills=cmp.missing,
                missing_preferred=cmp.missing_preferred,
            )
        )
    results.sort(key=lambda m: (-m.score, -m.skill_overlap, m.job.job_id))
    return results


def skill_gap_summary(matches: list[JobMatch], top: int = 8) -> list[tuple[str, int]]:
    """Most frequently missing required skills across the given (top) matches."""
    counts = Counter(skill for m in matches for skill in m.missing_skills)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
