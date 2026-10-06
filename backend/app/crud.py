from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Job, JobSkill, Resume, Skill, User
from .schemas import JobOut, ResumeOut


def get_or_create_skills(db: Session, names: list[str]) -> list[Skill]:
    if not names:
        return []
    lowered = {n.lower() for n in names}
    existing = db.scalars(select(Skill).where(func.lower(Skill.name).in_(lowered))).all()
    by_lower = {s.name.lower(): s for s in existing}
    result = []
    for name in names:
        skill = by_lower.get(name.lower())
        if skill is None:
            skill = Skill(name=name)
            db.add(skill)
            by_lower[name.lower()] = skill
        if skill not in result:
            result.append(skill)
    db.flush()
    return result


def set_job_skills(db: Session, job: Job, required: list[str], preferred: list[str]) -> None:
    job.job_skills.clear()
    db.flush()
    required_lower = {r.lower() for r in required}
    for skill in get_or_create_skills(db, required):
        job.job_skills.append(JobSkill(skill=skill, is_required=True))
    for skill in get_or_create_skills(db, [p for p in preferred if p.lower() not in required_lower]):
        job.job_skills.append(JobSkill(skill=skill, is_required=False))


def latest_resume(db: Session, user: User) -> Resume | None:
    return db.scalars(
        select(Resume).where(Resume.user_id == user.user_id).order_by(Resume.uploaded_at.desc()).limit(1)
    ).first()


def resume_out(resume: Resume) -> ResumeOut:
    return ResumeOut(
        resume_id=resume.resume_id,
        education=resume.education,
        experience=resume.experience,
        experience_years=resume.experience_years,
        extraction_method=resume.extraction_method,
        skills=sorted((s.name for s in resume.skills), key=str.lower),
        uploaded_at=resume.uploaded_at,
    )


def job_out(job: Job) -> JobOut:
    return JobOut.model_validate(job)
