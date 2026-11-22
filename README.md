# AI Job & Internship Assistant

Upload your PDF resume and get the **top 10 matching internships and entry-level jobs in Korea**. Each match shows a score (0–100), the skills you already have, and the skills you are missing.

## How it works

1. **Resume → skills.** Text is taken from the PDF. Skills are extracted by an LLM (Claude or a free local model via Ollama) or by dictionary matching.
2. **Normalization.** Different spellings become one name, e.g. `ML` → `Machine Learning`, `파이썬` → `Python`.
3. **Live job search.** Right after the upload, the resume's skills become web searches (Tavily API) on Wanted, Jumpit and JobKorea. Posting pages are parsed (company, title, internship or full-time, city, Korean level), senior roles are dropped, re-posts are merged, and the new postings are added to the database.
4. **Matching.** `Score = 100 × (0.7 × skill overlap + 0.3 × text similarity)`. Postings are filtered first by location, job type and Korean level.

**Stack:** React + Vite · FastAPI · SQLAlchemy (PostgreSQL or SQLite) · Tavily search API · Docker

Live search needs a free key from [tavily.com](https://tavily.com) in `backend/.env` (`TAVILY_API_KEY=...`). Without it the app matches against the imported postings only.

## Docker (one container)

```bash
docker build -t job-assistant .
docker run -p 7860:7860 -e TAVILY_API_KEY=... -e JWT_SECRET=... job-assistant   # http://localhost:7860
```

The image serves the API and the built React app together, loads the sample postings on start, and uses keyword extraction and TF-IDF, so it needs no GPU or model download.

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
