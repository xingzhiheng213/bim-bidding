"""FastAPI app: health check and optional DB check on startup."""
import logging
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app import config
from app.auth import verify_api_key
from app.database import check_db, engine
from app.models import Base
from app.routers import (
    chapters as chapters_router,
)
from app.routers import (
    compare,
    settings,
    steps,
    tasks,
    upload,
)
from app.routers import (
    export as export_router,
)
from app.routers import (
    framework as framework_router,
)
from app.routers import (
    review as review_router,
)
from app.routers import prompt_profiles as prompt_profiles_router

logger = logging.getLogger(__name__)
app = FastAPI(
    title="BIM 标书生成 API",
    version="0.1.0",
    dependencies=[Depends(verify_api_key)],
)
app.include_router(tasks.router)
app.include_router(upload.router)
app.include_router(steps.router)
app.include_router(framework_router.router)
app.include_router(chapters_router.router)
app.include_router(review_router.router)
app.include_router(export_router.router)
app.include_router(compare.router, prefix="/api")
app.include_router(settings.router, prefix="/api/settings")
app.include_router(prompt_profiles_router.router)

# CORS: allow frontend dev server (localhost) + optional LAN Vite (same port 5173)
_cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").strip().split(",")
_cors_allow_lan_vite = os.getenv("CORS_ALLOW_LAN_VITE", "1").strip().lower() not in ("0", "false", "no", "")
# 内网用 IP 打开 Vite（如 http://192.168.2.14:5173）时与 API 不同源，需放行对应 Origin
_LAN_VITE_ORIGIN_REGEX = (
    r"^http://("
    r"localhost|127\.0\.0\.1|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}"
    r"):5173$"
)
# SEC-03: 显式 methods/headers，避免通配符与 credentials 组合过宽
_CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
_CORS_ALLOW_HEADERS = [
    "Content-Type",
    "Authorization",
    "X-API-Key",
    "Accept",
    "Accept-Language",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins if o.strip()],
    allow_origin_regex=_LAN_VITE_ORIGIN_REGEX if _cors_allow_lan_vite else None,
    allow_credentials=True,
    allow_methods=_CORS_ALLOW_METHODS,
    allow_headers=_CORS_ALLOW_HEADERS,
)


@app.on_event("startup")
async def startup():
    """Test DB connection and create tables if not exist."""
    if not (config.ADMIN_API_KEY or "").strip():
        logger.warning(
            "ADMIN_API_KEY is not set: HTTP API authentication is disabled. "
            "Set ADMIN_API_KEY in .env for production."
        )
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

    # Add composite index on (task_id, step_key) for task_steps — highest-frequency query path
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_task_steps_task_id_step_key"
                " ON task_steps (task_id, step_key)"
            ))
            conn.commit()
        logger.info("Index ix_task_steps_task_id_step_key ensured on task_steps")
    except Exception as e:
        logger.warning("Could not create index ix_task_steps_task_id_step_key: %s", e)

    # Add profile_id to tasks (PromptProfile binding, Phase B)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN profile_id INTEGER"))
            conn.commit()
        logger.info("Added column profile_id to tasks")
    except Exception as e:
        err = str(e).lower()
        if "duplicate" in err or "already exists" in err or "exists" in err:
            logger.debug("Column profile_id already exists on tasks")
        else:
            logger.warning("Could not add profile_id to tasks: %s", e)

    # Add discipline to prompt_profiles (semantic profile specialty)
    try:
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE prompt_profiles ADD COLUMN discipline VARCHAR(32)"))
            conn.commit()
        logger.info("Added column discipline to prompt_profiles")
    except Exception as e:
        err = str(e).lower()
        if "duplicate" in err or "already exists" in err or "exists" in err:
            logger.debug("Column discipline already exists on prompt_profiles")
        else:
            logger.warning("Could not add discipline to prompt_profiles: %s", e)
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "UPDATE prompt_profiles SET discipline = '建筑' "
                    "WHERE discipline IS NULL OR TRIM(discipline) = ''"
                )
            )
            conn.commit()
        logger.info("Backfilled prompt_profiles.discipline where null")
    except Exception as e:
        logger.warning("Could not backfill prompt_profiles.discipline: %s", e)


@app.get("/health")
def health():
    """Health check: returns status ok."""
    return {"status": "ok"}
