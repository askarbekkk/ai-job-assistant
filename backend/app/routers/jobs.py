"""FR5 — browse and filter job postings."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..crud import job_out
from ..database import get_db
from ..models import Job, JobSkill, Skill
from ..schemas import JobMeta, JobOut, JobPage
from ..services.matching import EMPLOYMENT_TYPES, KOREAN_LEVELS

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=JobPage)
def list_jobs(
    q: str | None = Query(None, max_length=100, description="Search in title, company and description"),
    location: str | None = None,
    employment_type: str | None = None,
    korean_level: str | None = Query(None, description="Your Korean level; harder postings are hidden"),
    skill: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Job)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Job.title).like(like),
                func.lower(Job.company).like(like),
                func.lower(Job.description).like(like),
            )
        )
    if location:
        stmt = stmt.where(func.lower(Job.location) == location.lower())
    if employment_type:
        stmt = stmt.where(func.lower(Job.employment_type) == employment_type.lower())
    if korean_level in KOREAN_LEVELS:
        allowed = KOREAN_LEVELS[: KOREAN_LEVELS.index(korean_level) + 1]
        stmt = stmt.where(Job.korean_required.in_(allowed))
    if skill:
        stmt = stmt.where(
            Job.job_id.in_(
                select(JobSkill.job_id).join(Skill).where(func.lower(Skill.name) == skill.lower())
            )
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    jobs = db.scalars(
        stmt.order_by(Job.collected_date.desc(), Job.job_id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return JobPage(total=total, page=page, page_size=page_size, items=[job_out(j) for j in jobs])


@router.get("/meta", response_model=JobMeta)
def jobs_meta(db: Session = Depends(get_db)):
    locations = db.scalars(select(Job.location).distinct().order_by(Job.location)).all()
    types = db.scalars(select(Job.employment_type).distinct()).all()
    ordered_types = [t for t in EMPLOYMENT_TYPES if t in types] + sorted(t for t in types if t not in EMPLOYMENT_TYPES)
    return JobMeta(locations=list(locations), employment_types=ordered_types, korean_levels=KOREAN_LEVELS)


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    return job_out(job)
