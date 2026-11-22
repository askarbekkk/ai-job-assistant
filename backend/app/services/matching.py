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
from .skill_normalizer import get_normalizer

KOREAN_LEVELS = ["None", "Basic", "Fluent"]
EMPLOYMENT_TYPES = ["Internship", "Full-time"]


@dataclass
class Filters:
    location: str | None = None
    employment_type: str | None = None
    # The user's own Korean level: postings requiring more than this are removed.
    korean_level: str | None = None
    # Same idea as a TOPIK level (0 = no Korean); compared with the posting's TOPIK requirement.
    topik: int | None = None


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
    if filters.topik is not None and job.topik_level > filters.topik:
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


STRONG_MATCH = 70  # same line as the green score ring


@dataclass
class SkillBoost:
    skill: str
    unlocked: int  # postings that would cross STRONG_MATCH
    improved: int  # postings whose score would rise
    jobs: list[tuple[object, float, float]]  # (job, score now, score with the skill), best first


def skill_boosts(matches: list[JobMatch], top: int = 6, per_skill: int = 5) -> list[SkillBoost]:
    """What-if: for each missing required skill, how the scores would change if the user had it.

    Only skill overlap changes (the resume text stays the same), so the new score is the
    formula re-applied with one more matched skill. Ranked by postings unlocked as strong
    matches, then by total score gain.
    """
    # Suggest things one can learn and put on a resume: not soft skills or languages
    # (Korean has its own TOPIK filter).
    categories = get_normalizer().categories
    skip = {"Soft Skill", "Language"}
    by_skill: dict[str, list[tuple[object, float, float]]] = {}
    for m in matches:
        total = len(m.matched_skills) + len(m.missing_skills)
        if not total:
            continue
        after = final_score((len(m.matched_skills) + 1) / total, m.text_similarity, settings.weight_skill, settings.weight_text)
        for skill in m.missing_skills:
            if categories.get(skill) not in skip:
                by_skill.setdefault(skill, []).append((m.job, m.score, after))

    boosts = []
    for skill, rows in by_skill.items():
        rows.sort(key=lambda r: -r[2])
        unlocked = sum(1 for _, before, after in rows if before < STRONG_MATCH <= after)
        boosts.append((unlocked, sum(a - b for _, b, a in rows), SkillBoost(skill, unlocked, len(rows), rows[:per_skill])))
    boosts.sort(key=lambda b: (-b[0], -b[1], b[2].skill))
    return [b[2] for b in boosts[:top]]


def skill_gap_summary(matches: list[JobMatch], top: int = 8) -> list[tuple[str, int]]:
    """Most frequently missing required skills across the given (top) matches."""
    counts = Counter(skill for m in matches for skill in m.missing_skills)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top]
