"""Database tables — Section 11 of the proposal.

Beyond the proposal's columns, `resumes` keeps the extracted raw text and
`resumes`/`jobs` keep a cached sentence embedding, so text similarity does not
have to re-encode 300 postings on every request.
"""

from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


resume_skills = Table(
    "resume_skills",
    Base.metadata,
    Column("resume_id", ForeignKey("resumes.resume_id", ondelete="CASCADE"), primary_key=True),
    Column("skill_id", ForeignKey("skills.skill_id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", order_by="Resume.uploaded_at.desc()"
    )
    matches: Mapped[list["Match"]] = relationship(cascade="all, delete-orphan")
    saved_jobs: Mapped[list["SavedJob"]] = relationship(cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    skill_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)


class Resume(Base):
    __tablename__ = "resumes"

    resume_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    raw_text: Mapped[str] = mapped_column(Text, default="")
    education: Mapped[str] = mapped_column(Text, default="")
    experience: Mapped[str] = mapped_column(Text, default="")
    experience_years: Mapped[float] = mapped_column(Float, default=0.0)
    extraction_method: Mapped[str] = mapped_column(String(20), default="keyword")
    embedding: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="resumes")
    skills: Mapped[list[Skill]] = relationship(secondary=resume_skills, order_by=Skill.name)


class Job(Base):
    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    company: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300))
    employment_type: Mapped[str] = mapped_column(String(20), index=True)
    location: Mapped[str] = mapped_column(String(100), index=True)
    korean_required: Mapped[str] = mapped_column(String(10), index=True)
    description: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(String(1000), default="")
    collected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    embedding: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    job_skills: Mapped[list["JobSkill"]] = relationship(
        back_populates="job", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def required_skills(self) -> list[str]:
        return sorted(js.skill.name for js in self.job_skills if js.is_required)

    @property
    def preferred_skills(self) -> list[str]:
        return sorted(js.skill.name for js in self.job_skills if not js.is_required)


class JobSkill(Base):
    __tablename__ = "job_skills"

    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.job_id", ondelete="CASCADE"), primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skills.skill_id", ondelete="CASCADE"), primary_key=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)

    job: Mapped[Job] = relationship(back_populates="job_skills")
    skill: Mapped[Skill] = relationship(lazy="joined")


class Match(Base):
    __tablename__ = "matches"

    match_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.job_id", ondelete="CASCADE"))
    score: Mapped[float] = mapped_column(Float)
    missing_skills: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SavedJob(Base):
    __tablename__ = "saved_jobs"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.job_id", ondelete="CASCADE"), primary_key=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job: Mapped[Job] = relationship(lazy="joined")
