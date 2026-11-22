import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

try:
    from app.core.config import settings
except ImportError:
    from .config import settings

logger = logging.getLogger("nexus.database")

def create_resilient_engine():
    target_url: str = str(settings.database_url)
    connect_args = {"check_same_thread": False} if target_url.startswith("sqlite") else {}
    
    try:
        eng = create_engine(target_url, connect_args=connect_args, pool_pre_ping=True)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connected to database: %s", target_url.split("@")[-1] if "@" in target_url else target_url)
        return eng
    except Exception as exc:
        if not target_url.startswith("sqlite"):
            logger.warning(
                "PostgreSQL connection to %s failed (%s). Falling back to SQLite local store.",
                target_url.split("@")[-1] if "@" in target_url else target_url,
                exc
            )
            fallback_url = "sqlite:///./nexus_metadata.db"
            eng = create_engine(fallback_url, connect_args={"check_same_thread": False}, pool_pre_ping=True)
            return eng
        raise exc

engine = create_resilient_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
