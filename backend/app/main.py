"""FastAPI app: health check and optional DB check on startup."""
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import check_db, engine
from app.models import Base
from sqlalchemy import text
from app.routers import compare, settings, tasks

logger = logging.getLogger(__name__)
app = FastAPI(title="BIM 标书生成 API", version="0.1.0")
app.include_router(tasks.router)
app.include_router(compare.router, prefix="/api")
app.include_router(settings.router, prefix="/api/settings")

# CORS: allow frontend dev server (e.g. localhost:5173)
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").strip().split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Test DB connection and create tables if not exist."""
    try:
        check_db()
        logger.info("Database connection OK")
    except Exception as e:
        logger.warning("Database connection check failed: %s", e)
    # Create tables (tasks, task_steps) if not exist
    import app.models  # noqa: F401 - register models with Base.metadata
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created or already exist")
    # Add output_snapshot_before_regenerate to task_steps if missing (6.1 optional)
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE task_steps ADD COLUMN output_snapshot_before_regenerate TEXT"
            ))
            conn.commit()
        logger.info("Added column output_snapshot_before_regenerate to task_steps")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            logger.debug("Column output_snapshot_before_regenerate already exists")
        else:
            logger.warning("Could not add output_snapshot_before_regenerate: %s", e)

    # Add name to tasks if missing (task naming)
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE tasks ADD COLUMN name VARCHAR(255)"
            ))
            conn.commit()
        logger.info("Added column name to tasks")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            logger.debug("Column name already exists")
        else:
            logger.warning("Could not add name to tasks: %s", e)

    # Add celery_task_id to task_steps if missing (for one-click cancel revoke)
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "ALTER TABLE task_steps ADD COLUMN celery_task_id VARCHAR(255)"
            ))
            conn.commit()
        logger.info("Added column celery_task_id to task_steps")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            logger.debug("Column celery_task_id already exists")
        else:
            logger.warning("Could not add celery_task_id: %s", e)


@app.get("/health")
def health():
    """Health check: returns status ok."""
    return {"status": "ok"}
