"""FR2–FR4 — upload a PDF resume, extract skills, view and edit them."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from ..config import settings
from ..crud import get_or_create_skills, latest_resume, resume_out
from ..database import get_db
from ..models import Match, Resume, User
from ..schemas import ResumeOut, SkillsIn
from ..security import get_current_user
from ..services import similarity
from ..services.extraction import ExtractionError, extract_resume
from ..services.pdf_text import PdfError, extract_text
from ..services.skill_normalizer import get_normalizer

router = APIRouter(prefix="/api", tags=["resume"])


@router.post("/resume", response_model=ResumeOut, status_code=status.HTTP_201_CREATED)
def upload_resume(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = file.file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"Max file size is {settings.max_upload_mb} MB")
    try:
        text = extract_text(data)
    except PdfError as exc:
        raise HTTPException(422, str(exc))
    try:
        info = extract_resume(text)
    except ExtractionError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Skill extraction failed: {exc}")

    # Keep only the latest resume per user (privacy: no stale copies on disk).
    for old in list(user.resumes):
        Path(old.file_path).unlink(missing_ok=True)
        db.delete(old)
    db.query(Match).filter(Match.user_id == user.user_id).delete()

    user_dir = settings.upload_dir / str(user.user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    path = user_dir / f"{uuid.uuid4().hex}.pdf"
    path.write_bytes(data)

    resume = Resume(
        user_id=user.user_id,
        file_path=str(path),
        raw_text=text,
        education=info.education,
        experience=info.experience,
        experience_years=info.experience_years,
        extraction_method=info.method,
        skills=get_or_create_skills(db, info.skills),
    )
    if similarity.backend() == "sbert":
        resume.embedding = similarity.embedding_record(text)
    db.add(resume)
    db.commit()
    return resume_out(resume)


@router.get("/resume", response_model=ResumeOut)
def get_resume(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = latest_resume(db, user)
    if resume is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No resume uploaded yet")
    return resume_out(resume)


@router.put("/resume/skills", response_model=ResumeOut)
def update_skills(body: SkillsIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume = latest_resume(db, user)
    if resume is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No resume uploaded yet")
    resume.skills = get_or_create_skills(db, get_normalizer().normalize_many(body.skills))
    db.query(Match).filter(Match.user_id == user.user_id).delete()
    db.commit()
    return resume_out(resume)


@router.get("/skills", response_model=list[str])
def search_skills(q: str = Query("", max_length=60), limit: int = Query(20, ge=1, le=200)):
    """Standard skill names for autocomplete when the user edits skills."""
    return get_normalizer().search(q, limit)
