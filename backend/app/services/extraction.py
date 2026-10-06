"""Module 1b — skill extraction from resumes and job postings.

Two extractors:
  * "llm"     — Claude API or a local Ollama model (LLM_PROVIDER), constrained
                to a JSON schema (structured output).
  * "keyword" — dictionary matching against data/skills.json. Used when no API
                key is configured, when the API call fails in "auto" mode, and as
                the baseline in scripts/evaluate.py.

All skills are passed through the Skill Normalizer afterwards.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field

import anthropic
import httpx

from ..config import settings
from .skill_normalizer import get_normalizer

log = logging.getLogger(__name__)


class ExtractionError(RuntimeError):
    pass


@dataclass
class ResumeInfo:
    skills: list[str]
    education: str = ""
    experience: str = ""
    experience_years: float = 0.0
    method: str = "keyword"


@dataclass
class JobSkills:
    required: list[str]
    preferred: list[str] = field(default_factory=list)
    method: str = "keyword"


# ---------------------------------------------------------------- LLM (Claude)

_RESUME_SYSTEM = """You extract structured data from resumes of students and entry-level job seekers.
Resumes may be written in English, Korean, or a mix.
- skills: concrete technical and professional skills the person actually has: programming
  languages, frameworks, libraries, tools, platforms, methods (e.g. "Machine Learning",
  "A/B Testing"), spoken languages other than the native one, and a few clear soft skills.
  Use short canonical English names ("Python", "PyTorch", "SQL", "Data Visualization").
  Do not invent skills that are not supported by the text. Do not include course names,
  job titles or company names.
- education: one line, highest or current degree, e.g. "B.S. Computer Science, KAIST (2027, expected)".
  Empty string if not stated.
- experience: one or two sentences summarizing work/internship/project experience.
- experience_years: total professional experience in years (internships count; projects
  and coursework do not). 0 if none."""

_RESUME_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {"type": "array", "items": {"type": "string"}},
        "education": {"type": "string"},
        "experience": {"type": "string"},
        "experience_years": {"type": "number"},
    },
    "required": ["skills", "education", "experience", "experience_years"],
    "additionalProperties": False,
}

_JOB_SYSTEM = """You extract skill requirements from job and internship postings in Korea.
Postings may be written in English, Korean, or a mix.
- required_skills: skills the posting lists as required / qualifications / 자격요건 / 필수.
- preferred_skills: skills listed as preferred / nice to have / 우대사항.
If the posting does not separate them, put the skills that are clearly central to the
role in required_skills. Use short canonical English names ("Python", "Spring Boot",
"Data Analysis"). Do not include degrees, years of experience, or the Korean
language level (that is stored separately). Do not invent skills."""

_JOB_SCHEMA = {
    "type": "object",
    "properties": {
        "required_skills": {"type": "array", "items": {"type": "string"}},
        "preferred_skills": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["required_skills", "preferred_skills"],
    "additionalProperties": False,
}

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if settings.anthropic_api_key:
            _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        else:
            _client = anthropic.Anthropic()  # env var or `ant auth login` profile
    return _client


def _use_ollama() -> bool:
    return settings.llm_provider.lower() == "ollama"


def model_name() -> str:
    return settings.ollama_model if _use_ollama() else settings.llm_model


def llm_enabled() -> bool:
    mode = settings.skill_extractor.lower()
    if mode == "llm":
        return True
    if mode == "keyword":
        return False
    if _use_ollama():
        return True
    return bool(settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY"))


def _call_llm(system: str, text: str, schema: dict) -> dict:
    return _call_ollama(system, text, schema) if _use_ollama() else _call_claude(system, text, schema)


def _call_ollama(system: str, text: str, schema: dict) -> dict:
    """Local model through Ollama (free); `format` constrains the output to the JSON schema."""
    try:
        r = httpx.post(
            f"{settings.ollama_url.rstrip('/')}/api/chat",
            json={
                "model": settings.ollama_model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": text}],
                "format": schema,
                "stream": False,
                # Ollama's default context is too small for a full resume and cuts it silently.
                "options": {"temperature": 0, "num_ctx": 8192},
            },
            timeout=600,  # CPU-only machines are slow
        )
        r.raise_for_status()
    except httpx.ConnectError as exc:
        raise ExtractionError(f"Cannot reach Ollama at {settings.ollama_url} — is it running?") from exc
    except httpx.HTTPStatusError as exc:
        raise ExtractionError(f"Ollama error {exc.response.status_code}: {exc.response.text[:200]}") from exc
    except httpx.HTTPError as exc:
        raise ExtractionError(f"Ollama request failed: {exc}") from exc

    data = r.json()
    if data.get("done_reason") == "length":
        raise ExtractionError("The model output was cut off.")
    try:
        return json.loads(data["message"]["content"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise ExtractionError("The model did not return valid JSON.") from exc


def _call_claude(system: str, text: str, schema: dict) -> dict:
    try:
        response = _get_client().beta.messages.create(
            model=settings.llm_model,
            max_tokens=8000,
            system=system,
            messages=[{"role": "user", "content": text}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": schema}},
            # If a safety classifier declines, the API retries on a fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.APIConnectionError as exc:
        raise ExtractionError(f"Cannot reach the Claude API: {exc}") from exc
    except anthropic.APIStatusError as exc:
        raise ExtractionError(f"Claude API error {exc.status_code}: {exc.message}") from exc

    if response.stop_reason == "refusal":
        raise ExtractionError("The model declined to process this text.")
    if response.stop_reason == "max_tokens":
        raise ExtractionError("The model output was cut off (max_tokens).")
    text_out = next((b.text for b in response.content if b.type == "text"), "")
    try:
        return json.loads(text_out)
    except json.JSONDecodeError as exc:
        raise ExtractionError("The model did not return valid JSON.") from exc


# ---------------------------------------------------------------- keyword

_EDU_LINE = re.compile(
    r"(university|college|institute|b\.?s\.?|b\.?a\.?|m\.?s\.?|bachelor|master|ph\.?d|"
    r"대학교|대학원|학사|석사|박사)",
    re.IGNORECASE,
)
_YEARS = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?|년)", re.IGNORECASE)


def keyword_resume(text: str) -> ResumeInfo:
    normalizer = get_normalizer()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    education = next((ln for ln in lines if _EDU_LINE.search(ln)), "")
    years = [float(m.group(1)) for m in _YEARS.finditer(text) if float(m.group(1)) < 50]
    return ResumeInfo(
        skills=normalizer.extract_keywords(text),
        education=education[:300],
        experience="",
        experience_years=max(years, default=0.0),
        method="keyword",
    )


_PREFERRED_SECTION = re.compile(r"^[\s\-*•]*(preferred|nice[\s-]to[\s-]have|bonus|우대)", re.IGNORECASE | re.MULTILINE)


def keyword_job(description: str) -> JobSkills:
    """Skills after a "Preferred:" / "우대사항" heading count as preferred, the rest as required."""
    normalizer = get_normalizer()
    m = _PREFERRED_SECTION.search(description)
    required_text, preferred_text = (description[: m.start()], description[m.start():]) if m else (description, "")
    required = normalizer.extract_keywords(required_text)
    preferred = [s for s in normalizer.extract_keywords(preferred_text) if s not in required]
    return JobSkills(required=required, preferred=preferred, method="keyword")


# ---------------------------------------------------------------- facade


def extract_resume(text: str) -> ResumeInfo:
    normalizer = get_normalizer()
    if llm_enabled():
        try:
            data = _call_llm(_RESUME_SYSTEM, text, _RESUME_SCHEMA)
            return ResumeInfo(
                skills=normalizer.normalize_many(data["skills"]),
                education=data["education"].strip(),
                experience=data["experience"].strip(),
                experience_years=max(0.0, float(data["experience_years"])),
                method="llm",
            )
        except ExtractionError:
            if settings.skill_extractor.lower() == "llm":
                raise
            log.warning("LLM resume extraction failed, falling back to keywords", exc_info=True)
    return keyword_resume(text)


def extract_job_skills(description: str) -> JobSkills:
    normalizer = get_normalizer()
    if llm_enabled():
        try:
            data = _call_llm(_JOB_SYSTEM, description, _JOB_SCHEMA)
            required = normalizer.normalize_many(data["required_skills"])
            required_lower = {s.lower() for s in required}
            preferred = [
                s for s in normalizer.normalize_many(data["preferred_skills"]) if s.lower() not in required_lower
            ]
            return JobSkills(required=required, preferred=preferred, method="llm")
        except ExtractionError:
            if settings.skill_extractor.lower() == "llm":
                raise
            log.warning("LLM job extraction failed, falling back to keywords", exc_info=True)
    return keyword_job(description)
