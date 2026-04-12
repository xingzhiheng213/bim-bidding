"""User-defined semantic prompt profiles (Phase A: table only; CRUD in Phase B)."""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.task import Base


class PromptProfile(Base):
    """Stores optional per-slot semantic overrides; empty table is valid at Phase A."""

    __tablename__ = "prompt_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    discipline: Mapped[str] = mapped_column(String(32), nullable=False, default="建筑")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # dict[slot_key, str] — keys must be subset of semantic_slots.SEMANTIC_SLOT_KEYS
    semantic_overrides: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
