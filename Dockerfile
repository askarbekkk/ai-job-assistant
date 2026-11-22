# One container: FastAPI serves the API and the built React app.
# Works on Hugging Face Spaces (port 7860) and any Docker host.

FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ .
COPY data/ /app/data/
COPY --from=web /web/dist ./static

# SQLite in /tmp: rebuilt on every start from data/jobs_live.csv, a snapshot of real postings
# (refresh: python -m scripts.snapshot_live ../data/jobs_live.csv); uploads add fresh ones on top.
# Keyword skill extraction and TF-IDF keep the image small and fast (no GPU, no model download).
ENV DATABASE_URL=sqlite:////tmp/jobs.db \
    UPLOAD_DIR=/tmp/uploads \
    CACHE_DIR=/tmp/cache \
    SKILL_EXTRACTOR=keyword \
    EMBEDDING_BACKEND=tfidf \
    PORT=7860
EXPOSE 7860

CMD python -m scripts.import_jobs ../data/jobs_live.csv --spot-check-rate 0 && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
