"""Task and TaskStep models for BIM bidding workflow."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Human-friendly name for task list; optional but recommended
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    steps: Mapped[list["TaskStep"]] = relationship("TaskStep", back_populates="task", order_by="TaskStep.id")


class TaskStep(Base):
    __tablename__ = "task_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    step_key: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    input_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Snapshot of output before last regenerate (for diff: 要点变更前). Framework: full JSON; chapters: JSON {"chapter_N": "text"}.
    output_snapshot_before_regenerate: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    task: Mapped["Task"] = relationship("Task", back_populates="steps")
