import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from .config import BACKEND_DIR, settings
from .database import init_db
from .routers import auth, jobs, matches, resume, saved
from .services import extraction, similarity

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    logging.getLogger("app").info(
        "Skill extractor: %s | similarity: %s",
        "llm (" + extraction.model_name() + ")" if extraction.llm_enabled() else "keyword",
        similarity.backend(),  # loads the SBERT model once at startup
    )
    yield


app = FastAPI(title="AI Job & Internship Search Assistant", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.router, resume.router, jobs.router, matches.router, saved.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "skill_extractor": "llm" if extraction.llm_enabled() else "keyword",
        "similarity_backend": similarity.backend(),
    }


# In the Docker image the built React app sits in backend/static and is served
# from here, so one container is the whole site. In development Vite serves it.
STATIC_DIR = (BACKEND_DIR / "static").resolve()
if STATIC_DIR.is_dir():

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        file = (STATIC_DIR / path).resolve()
        if path and file.is_file() and file.is_relative_to(STATIC_DIR):
            return FileResponse(file)
        return FileResponse(STATIC_DIR / "index.html")  # client-side routes
