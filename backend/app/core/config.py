from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    app_name: str = "NEXUS AI"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./nexus_metadata.db"
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3:4b"
    ollama_embed_model: str = "nomic-embed-text"
    duckdb_dir: Path = BASE_DIR / "data" / "duckdb"
    chroma_dir: Path = BASE_DIR / "data" / "chroma"
    upload_dir: Path = BASE_DIR / "storage" / "uploads"
    max_upload_mb: int = 150
    max_sql_rows: int = 500
    duckdb_memory_limit: str = "1GB"
    duckdb_threads: int = 4
    query_timeout_seconds: int = 30
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    max_context_turns: int = 6

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        extra="ignore",
        env_file_encoding="utf-8"
    )

settings = Settings()
for directory in (settings.duckdb_dir, settings.chroma_dir, settings.upload_dir):
    directory.mkdir(parents=True, exist_ok=True)
