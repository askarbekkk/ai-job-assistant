from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ---------- auth ----------
class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password must be at most 72 bytes")
        return v


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    name: str
    email: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------- resume ----------
class ResumeOut(BaseModel):
    resume_id: int
    education: str
    experience: str
    experience_years: float
    extraction_method: str
    skills: list[str]
    uploaded_at: datetime
    live_jobs_found: int | None = None  # postings found by live search right after this upload


class SkillsIn(BaseModel):
    skills: list[str] = Field(max_length=200)


# ---------- jobs ----------
class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: str
    company: str
    title: str
    employment_type: str
    location: str
    korean_required: str
    topik_level: int  # 0 = Korean not required, else TOPIK 1-6
    topik_stated: bool  # True: the posting says it; False: estimated
    description: str
    source_url: str
    collected_date: date | None
    required_skills: list[str]
    preferred_skills: list[str]


class JobPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[JobOut]


class JobMeta(BaseModel):
    locations: list[str]
    employment_types: list[str]
    korean_levels: list[str]


# ---------- matches ----------
class MatchOut(BaseModel):
    job: JobOut
    score: float
    skill_overlap: float
    text_similarity: float
    matched_skills: list[str]
    missing_skills: list[str]
    missing_preferred: list[str]
    saved: bool = False


class SkillGapItem(BaseModel):
    skill: str
    count: int


class BoostJob(BaseModel):
    job_id: str
    title: str
    company: str
    score_now: float
    score_with_skill: float


class SkillBoostOut(BaseModel):
    skill: str
    unlocked: int  # postings that would become strong matches (70+)
    improved: int  # postings whose score would rise
    jobs: list[BoostJob]


class RecommendationsOut(BaseModel):
    resume_id: int
    similarity_backend: str
    weights: dict[str, float]
    total_candidates: int
    elapsed_ms: int
    results: list[MatchOut]
    skill_gap: list[SkillGapItem]
    skill_boosts: list[SkillBoostOut] = []


class SavedJobOut(BaseModel):
    job: JobOut
    saved_at: datetime
