# AI Job & Internship Assistant

Upload your PDF resume and get the **top 10 matching internships and entry-level jobs in Korea**. Each match shows a score (0–100), the skills you already have, and the skills you are missing.

## How it works

1. **Resume → skills.** Text is taken from the PDF. Skills are extracted by an LLM (Claude or a free local model via Ollama) or by dictionary matching.
2. **Normalization.** Different spellings become one name, e.g. `ML` → `Machine Learning`, `파이썬` → `Python`.
3. **Matching.** `Score = 100 × (0.7 × skill overlap + 0.3 × text similarity)`. Postings are filtered first by location, job type and Korean level.

**Stack:** React + Vite · FastAPI · SQLAlchemy (PostgreSQL or SQLite)

## Quick start (Windows)

Requires Python 3.11+ and Node 18+.

```powershell
# Backend
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # set DATABASE_URL=sqlite:///./dev.db to skip Docker
python -m scripts.import_jobs ..\data\jobs_sample.csv
uvicorn app.main:app --reload # http://localhost:8000/docs

# Frontend (second terminal)
cd frontend
npm install
npm run dev                   # http://localhost:5173
```

## Skill extraction options (`backend/.env`)

| Setting | Result |
|---|---|
| nothing set | Dictionary matching (free, no setup) |
| `LLM_PROVIDER=ollama` | Free local LLM via [Ollama](https://ollama.com) |
| `ANTHROPIC_API_KEY=...` | Claude API |

## Tests

```powershell
cd backend
pytest
```

More details (dataset workflow, evaluation, API): [docs/GUIDE.md](docs/GUIDE.md)
