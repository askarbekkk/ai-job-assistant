"""Tests run on a throw-away SQLite DB with keyword extraction and TF-IDF,
so they need neither PostgreSQL nor an API key nor the SBERT model."""

import os
import tempfile
import uuid
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="jobs-test-"))
os.environ.update(
    DATABASE_URL=f"sqlite:///{(_TMP / 'test.db').as_posix()}",
    SKILL_EXTRACTOR="keyword",
    EMBEDDING_BACKEND="tfidf",
    UPLOAD_DIR=str(_TMP / "uploads"),
    CACHE_DIR=str(_TMP / "cache"),
    JWT_SECRET="test-secret-test-secret-test-secret-0123",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import PROJECT_DIR  # noqa: E402
from app.main import app  # noqa: E402
from scripts import import_jobs  # noqa: E402
from scripts.make_pdf import text_to_pdf  # noqa: E402

DATA = PROJECT_DIR / "data"


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        import_jobs.run(DATA / "jobs_sample.csv", replace=True, spot_check_rate=0)
        yield c


@pytest.fixture
def register(client):
    def _register(password: str = "password123") -> tuple[dict, str]:
        email = f"user-{uuid.uuid4().hex[:8]}@example.com"
        r = client.post("/api/auth/register", json={"name": "Test", "email": email, "password": password})
        assert r.status_code == 201, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}, email

    return _register


@pytest.fixture(scope="session")
def resume_pdf() -> bytes:
    return text_to_pdf((DATA / "eval" / "resumes" / "r01.txt").read_text(encoding="utf-8"))


@pytest.fixture
def user_with_resume(client, register, resume_pdf):
    headers, email = register()
    r = client.post("/api/resume", headers=headers, files={"file": ("cv.pdf", resume_pdf, "application/pdf")})
    assert r.status_code == 201, r.text
    return headers
