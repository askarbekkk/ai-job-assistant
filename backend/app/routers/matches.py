"""FR6–FR7 — top-10 recommendations with match score and missing skills."""

import time

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..crud import job_out, latest_resume
from ..database import get_db
from ..models import Job, Match, Resume, SavedJob, User
from ..schemas import MatchOut, RecommendationsOut, SkillGapItem
from ..security import get_current_user
from ..services import similarity
from ..services.matching import Filters, JobMatch, passes_filters, score_jobs, skill_gap_summary

router = APIRouter(prefix="/api/matches", tags=["matches"])


def _require_resume(db: Session, user: User) -> Resume:
    resume = latest_resume(db, user)
    if resume is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Upload a resume first")
    return resume


def _match_out(m: JobMatch, saved_ids: set[str]) -> MatchOut:
    return MatchOut(
        job=job_out(m.job),
        score=m.score,
        skill_overlap=m.skill_overlap,
        text_similarity=m.text_similarity,
        matched_skills=m.matched_skills,
        missing_skills=m.missing_skills,
        missing_preferred=m.missing_preferred,
        saved=m.job.job_id in saved_ids,
    )


def _saved_ids(db: Session, user: User) -> set[str]:
    return set(db.scalars(select(SavedJob.job_id).where(SavedJob.user_id == user.user_id)).all())


@router.get("", response_model=RecommendationsOut)
def recommendations(
    location: str | None = None,
    employment_type: str | None = None,
    korean_level: str | None = None,
    limit: int = Query(settings.top_k, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resume = _require_resume(db, user)
    started = time.perf_counter()

    filters = Filters(location=location, employment_type=employment_type, korean_level=korean_level)
    candidates = [j for j in db.scalars(select(Job)).all() if passes_filters(j, filters)]
    sims = similarity.similarities(resume.raw_text, resume.embedding, candidates)
    top = score_jobs([s.name for s in resume.skills], candidates, sims)[:limit]

    db.query(Match).filter(Match.user_id == user.user_id).delete()
    for m in top:
        db.add(Match(user_id=user.user_id, job_id=m.job.job_id, score=m.score, missing_skills=m.missing_skills))
    db.commit()  # also stores any job embeddings computed above

    saved = _saved_ids(db, user)
    return RecommendationsOut(
        resume_id=resume.resume_id,
        similarity_backend=similarity.backend(),
        weights={"skill": settings.weight_skill, "text": settings.weight_text},
        total_candidates=len(candidates),
        elapsed_ms=int((time.perf_counter() - started) * 1000),
        results=[_match_out(m, saved) for m in top],
        skill_gap=[SkillGapItem(skill=s, count=c) for s, c in skill_gap_summary(top)],
    )


@router.get("/{job_id}", response_model=MatchOut)
def match_for_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Score and skill gap for one posting (used on the job detail page)."""
    resume = _require_resume(db, user)
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    # TF-IDF needs the whole collection for IDF, so score against all jobs.
    jobs = db.scalars(select(Job)).all()
    sims = similarity.similarities(resume.raw_text, resume.embedding, jobs)
    db.commit()
    result = next(m for m in score_jobs([s.name for s in resume.skills], jobs, sims) if m.job.job_id == job_id)
    return _match_out(result, _saved_ids(db, user))
