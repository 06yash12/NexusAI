from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("nexus.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schemas...")
    Base.metadata.create_all(bind=engine)
    logger.info("NEXUS AI Enterprise Platform engine ready.")
    yield

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Enterprise Platform for Local-First Natural Language Analytics and Hybrid Document RAG",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)

@app.get("/health")
def health():
    db_type = "sqlite" if str(engine.url).startswith("sqlite") else "postgresql"
    return {
        "status": "healthy",
        "application": settings.app_name,
        "database": db_type,
        "chat_model": settings.ollama_chat_model,
        "embed_model": settings.ollama_embed_model
    }
