"""Functional tests — one group per requirement FR1–FR8 (Section 12.1) plus security."""

from pathlib import Path

from app.config import settings


# FR1 — sign up and log in
def test_fr1_register_and_login(client, register):
    headers, email = register()
    assert client.get("/api/auth/me", headers=headers).json()["email"] == email

    r = client.post("/api/auth/login", json={"email": email.upper(), "password": "password123"})
    assert r.status_code == 200 and r.json()["access_token"]

    assert client.post("/api/auth/login", json={"email": email, "password": "wrong-pass"}).status_code == 401
    dup = client.post("/api/auth/register", json={"name": "X", "email": email, "password": "password123"})
    assert dup.status_code == 409
    assert client.get("/api/auth/me").status_code == 401


def test_fr1_short_password_rejected(client):
    r = client.post("/api/auth/register", json={"name": "X", "email": "short@example.com", "password": "123"})
    assert r.status_code == 422


# FR2 — upload a PDF resume
def test_fr2_upload_pdf(client, register, resume_pdf):
    headers, _ = register()
    r = client.post("/api/resume", headers=headers, files={"file": ("cv.pdf", resume_pdf, "application/pdf")})
    assert r.status_code == 201


def test_fr2_rejects_non_pdf_and_anonymous(client, register, resume_pdf):
    headers, _ = register()
    r = client.post("/api/resume", headers=headers, files={"file": ("cv.txt", b"hello world", "text/plain")})
    assert r.status_code == 422
    r = client.post("/api/resume", files={"file": ("cv.pdf", resume_pdf, "application/pdf")})
    assert r.status_code == 401


# FR3 — extract skills, education and experience
def test_fr3_extraction(client, user_with_resume):
    resume = client.get("/api/resume", headers=user_with_resume).json()
    for skill in ("Python", "SQL", "Pandas", "Tableau", "scikit-learn"):
        assert skill in resume["skills"]
    assert "University" in resume["education"]
    assert resume["experience_years"] == 0.0 or resume["experience_years"] > 0


# FR4 — view and edit extracted skills
def test_fr4_edit_skills_are_normalized(client, user_with_resume):
    r = client.put(
        "/api/resume/skills",
        headers=user_with_resume,
        json={"skills": ["python3", "ML", "sklearn", "파이썬", "Some New Skill"]},
    )
    assert r.status_code == 200
    assert r.json()["skills"] == ["Machine Learning", "Python", "scikit-learn", "Some New Skill"]
    assert "Machine Learning" in client.get("/api/skills?q=machine").json()


# FR5 — browse and filter postings
def test_fr5_browse_and_filter(client):
    all_jobs = client.get("/api/jobs?page_size=100").json()
    assert all_jobs["total"] == 25  # 26 rows minus one duplicate

    interns = client.get("/api/jobs?employment_type=Internship&page_size=100").json()["items"]
    assert interns and all(j["employment_type"] == "Internship" for j in interns)

    no_korean = client.get("/api/jobs?korean_level=None&page_size=100").json()["items"]
    assert no_korean and all(j["korean_required"] == "None" for j in no_korean)

    daejeon = client.get("/api/jobs?location=daejeon&page_size=100").json()["items"]
    assert {j["job_id"] for j in daejeon} == {"J0002", "J0006", "J0017"}

    assert client.get("/api/jobs?skill=Kotlin").json()["items"][0]["job_id"] == "J0009"
    assert client.get("/api/jobs?q=robots").json()["total"] == 1
    assert "Daejeon" in client.get("/api/jobs/meta").json()["locations"]
    assert client.get("/api/jobs/J9999").status_code == 404


# FR6 — top-10 recommendations with a match score
def test_fr6_recommendations(client, user_with_resume):
    r = client.get("/api/matches", headers=user_with_resume)
    assert r.status_code == 200
    body = r.json()
    scores = [m["score"] for m in body["results"]]
    assert len(scores) == 10
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= s <= 100 for s in scores)
    assert "J0001" in [m["job"]["job_id"] for m in body["results"][:3]]
    assert body["elapsed_ms"] < 5000  # NFR performance


def test_fr6_filters_apply_to_recommendations(client, user_with_resume):
    body = client.get("/api/matches?korean_level=None&employment_type=Internship", headers=user_with_resume).json()
    assert body["results"]
    assert all(m["job"]["korean_required"] == "None" for m in body["results"])
    assert all(m["job"]["employment_type"] == "Internship" for m in body["results"])


def test_fr6_requires_resume(client, register):
    headers, _ = register()
    assert client.get("/api/matches", headers=headers).status_code == 400


# FR7 — missing skills per posting
def test_fr7_missing_skills(client, user_with_resume):
    body = client.get("/api/matches", headers=user_with_resume).json()
    user_skills = {s.lower() for s in client.get("/api/resume", headers=user_with_resume).json()["skills"]}
    for m in body["results"]:
        required = m["job"]["required_skills"] or m["job"]["preferred_skills"]
        assert sorted(m["missing_skills"] + m["matched_skills"]) == sorted(required)
        assert not {s.lower() for s in m["missing_skills"]} & user_skills
    assert body["skill_gap"] and body["skill_gap"][0]["count"] >= body["skill_gap"][-1]["count"]

    single = client.get("/api/matches/J0001", headers=user_with_resume).json()
    assert single["job"]["job_id"] == "J0001" and "Python" in single["matched_skills"]


# FR8 — save postings
def test_fr8_save_jobs(client, user_with_resume):
    h = user_with_resume
    assert client.post("/api/saved/J0001", headers=h).status_code == 204
    assert client.post("/api/saved/J0001", headers=h).status_code == 204  # idempotent
    assert [s["job"]["job_id"] for s in client.get("/api/saved", headers=h).json()] == ["J0001"]
    assert client.get("/api/matches/J0001", headers=h).json()["saved"] is True

    assert client.delete("/api/saved/J0001", headers=h).status_code == 204
    assert client.get("/api/saved", headers=h).json() == []
    assert client.post("/api/saved/J9999", headers=h).status_code == 404


# Security — resumes are private; users can delete their data
def test_resume_visible_only_to_owner(client, user_with_resume, register):
    other, _ = register()
    assert client.get("/api/resume", headers=other).status_code == 404


def test_delete_account_removes_data(client, register, resume_pdf):
    headers, email = register()
    client.post("/api/resume", headers=headers, files={"file": ("cv.pdf", resume_pdf, "application/pdf")})
    client.post("/api/saved/J0002", headers=headers)
    user_id = client.get("/api/auth/me", headers=headers).json()["user_id"]
    user_dir = Path(settings.upload_dir) / str(user_id)
    assert any(user_dir.iterdir())

    assert client.delete("/api/users/me", headers=headers).status_code == 204
    assert not user_dir.exists()
    assert client.post("/api/auth/login", json={"email": email, "password": "password123"}).status_code == 401
