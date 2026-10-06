# AI Job & Internship Search Assistant

Upload a PDF resume and get the top-10 matching internships and entry-level jobs in Korea. Each match comes with a score from 0 to 100, the skills you already have, and the skills you are missing.

```
User ─ Web App (React) ─HTTPS/JSON─ REST API (FastAPI)
                                       │
         LLM API ── 1 Resume Parser → 2 Skill Normalizer → 3 Matching Engine → 4 Score & Skill Gap
                                                                                     │
Job Dataset (CSV) → Import Script ──────────────────────────────────────────→ PostgreSQL
```

| Diagram block | Code |
|---|---|
| Web App (React) | `frontend/src/` |
| REST API | `backend/app/main.py`, `backend/app/routers/` |
| 1. Resume Parser | `services/pdf_text.py` (PDF → text), `services/extraction.py` (LLM → skills JSON) |
| 2. Skill Normalizer | `services/skill_normalizer.py` + `data/skills.json` (~190 skills, EN/KO aliases) |
| 3. Matching Engine | `services/matching.py` (filters, skill overlap), `services/similarity.py` (text similarity) |
| 4. Score & Skill Gap | `services/matching.py` (`final_score`, `skill_gap_summary`) |
| PostgreSQL | `app/models.py` (tables from Section 11), `docker-compose.yml` |
| Import Script | `backend/scripts/import_jobs.py` |
| Evaluation (Section 12) | `backend/scripts/evaluate.py`, `backend/tests/` |

---

## Quick start (Windows / PowerShell)

Requirements: Python 3.11+, Node 18+, Docker Desktop (for PostgreSQL).

```powershell
# 1. Database
docker compose up -d

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env            # then set JWT_SECRET (and ANTHROPIC_API_KEY if you have one)
python -m scripts.import_jobs ..\data\jobs_sample.csv
uvicorn app.main:app --reload     # http://localhost:8000/docs

# 3. Frontend (second terminal)
cd frontend
npm install
npm run dev                       # http://localhost:5173
```

To try it without Docker, set `DATABASE_URL=sqlite:///./dev.db` in `backend/.env`.

Demo resume: `python -m scripts.make_pdf ..\data\eval\resumes\r01.txt ..\data\sample_resume.pdf`, then upload `data/sample_resume.pdf`.

### Optional components

| Feature | Enable with | Without it |
|---|---|---|
| AI skill extraction (Claude) | `ANTHROPIC_API_KEY=...` in `backend/.env` | Dictionary keyword matching |
| Sentence-BERT text similarity | `pip install -r requirements-ml.txt` | TF-IDF cosine similarity |

`GET /api/health` shows which skill extractor and similarity backend are in use.

The LLM is used only to turn text into a skills JSON (structured output, low effort). It runs once per uploaded resume and once per posting at import. Import results are cached in `data/cache/job_skills.json`, so running the import again does not call the API (and is not billed) for postings it already processed. The default model is `claude-opus-5-5`; you can change it with `LLM_MODEL`.

---

## Job dataset workflow (Section 7)

1. Each team member fills a shared Google Sheet with the columns in `data/jobs_template.csv`:
   `job_id, company, title, employment_type, location, korean_required, description, source_url, collected_date`
   - `employment_type`: `Internship` / `Full-time`. Common variants are accepted: `intern`, `인턴`, `정규직`, `신입`, …
   - `korean_required`: `None` / `Basic` / `Fluent`. Also accepted: `not required`, `TOPIK 4`, `무관`, `필수`, …
   - `description`: paste the full posting text. Keep headings such as "Requirements / Preferred" or "자격요건 / 우대사항".
2. Export the sheet as CSV and run `python -m scripts.import_jobs ..\data\jobs.csv`. The script then:
   - removes duplicates (same URL, or same company + title + location);
   - reports invalid rows instead of guessing values (fix those rows in the sheet and run it again);
   - extracts and normalizes required and preferred skills, then loads everything into the database;
   - writes `data/spot_check.csv`, a random ~10% of postings for manual checking of the extracted skills.
3. Useful flags: `--dry-run` only validates the file, `--replace` deletes all jobs before importing.

`data/jobs_sample.csv` contains **25 synthetic postings** (companies marked "(sample)") for development and tests. Replace them with the real collected data.

## Matching (Section 10)

```
Match = 100 × (0.7 × skill_overlap + 0.3 × text_similarity)
skill_overlap   = |required ∩ user skills| / |required|
missing skills  = required − user skills
```

Before scoring, postings are filtered by location, job type and the user's Korean level. A posting that needs a higher Korean level than the user has is hidden. Change the weights with `WEIGHT_SKILL` / `WEIGHT_TEXT`.

Typical similarity values differ between backends: TF-IDF gives about 0.0–0.3, Sentence-BERT about 0.2–0.7. Tune the weights separately for the backend you use.

## Evaluation (Section 12)

```powershell
cd backend
pytest                                     # FR1–FR8 functional tests + unit tests (no DB/API key needed)

python -m scripts.evaluate ranking --resumes ..\data\eval\resumes --labels ..\data\eval\labels.csv [--tune]
python -m scripts.evaluate extraction --resumes ..\data\eval\resumes --gold ..\data\eval\skills_gold.csv
```

- `ranking` compares Precision@5 of the system against a keyword-only baseline. `--tune` runs a grid search over the 0.7 / 0.3 weights; tune on one half of the resumes and report on the other half.
- `extraction` compares extracted skills with hand-marked skills (precision, recall, F1).
- `data/eval/` contains 3 example resumes with labels. Replace them with your 20 resumes × 20 labeled postings. If two people label each resume, merge their labels before running the script.

## REST API

| Method | Path | FR |
|---|---|---|
| POST | `/api/auth/register`, `/api/auth/login` | FR1 |
| GET | `/api/auth/me` | FR1 |
| DELETE | `/api/users/me`: deletes the account, resume file, matches and saved jobs | Security |
| POST | `/api/resume` (multipart PDF) | FR2, FR3 |
| GET | `/api/resume` | FR4 |
| PUT | `/api/resume/skills` `{"skills": [...]}` | FR4 |
| GET | `/api/skills?q=` (autocomplete) | FR4 |
| GET | `/api/jobs?q=&location=&employment_type=&korean_level=&skill=&page=` | FR5 |
| GET | `/api/jobs/meta`, `/api/jobs/{id}` | FR5 |
| GET | `/api/matches?location=&employment_type=&korean_level=&limit=10` | FR6, FR7 |
| GET | `/api/matches/{job_id}` | FR7 |
| GET / POST / DELETE | `/api/saved`, `/api/saved/{job_id}` | FR8 |

Interactive docs: http://localhost:8000/docs

## Known limitations

- Only text PDFs are supported. Scanned (image) resumes are rejected with a clear message.
- The dataset is a fixed snapshot, so some postings will expire.
- The keyword extractor is a fallback and baseline. It can miss skills phrased unusually and may pick up skills mentioned outside the requirements.
- Tables are created on startup (`create_all`). If the schema changes after real data is loaded, add Alembic migrations.
