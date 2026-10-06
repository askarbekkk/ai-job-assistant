from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://jobs:jobs@localhost:5432/jobs"

    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60 * 24

    upload_dir: Path = BACKEND_DIR / "uploads"
    max_upload_mb: int = 5
    skills_file: Path = PROJECT_DIR / "data" / "skills.json"
    cache_dir: Path = PROJECT_DIR / "data" / "cache"

    # auto | llm | keyword
    skill_extractor: str = "auto"
    # anthropic | ollama
    llm_provider: str = "anthropic"
    anthropic_api_key: str | None = None
    llm_model: str = "claude-opus-5-5"
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "exaone3.5:2.4b-instruct-q4_K_M"

    # auto | sbert | tfidf
    embedding_backend: str = "auto"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    weight_skill: float = 0.7
    weight_text: float = 0.3
    top_k: int = 10

    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
