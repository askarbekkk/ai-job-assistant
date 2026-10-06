"""FR8 — save postings."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..crud import job_out
from ..database import get_db
from ..models import Job, SavedJob, User
from ..schemas import SavedJobOut
from ..security import get_current_user

router = APIRouter(prefix="/api/saved", tags=["saved"])


@router.get("", response_model=list[SavedJobOut])
def list_saved(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(SavedJob).where(SavedJob.user_id == user.user_id).order_by(SavedJob.saved_at.desc())
    ).all()
    return [SavedJobOut(job=job_out(r.job), saved_at=r.saved_at) for r in rows]


@router.post("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def save_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.get(Job, job_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found")
    if db.get(SavedJob, (user.user_id, job_id)) is None:
        db.add(SavedJob(user_id=user.user_id, job_id=job_id))
        db.commit()


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def unsave_job(job_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(SavedJob, (user.user_id, job_id))
    if row is not None:
        db.delete(row)
        db.commit()
