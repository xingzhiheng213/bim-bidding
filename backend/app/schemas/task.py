"""Pydantic schemas for Task and TaskStep."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

DEFAULT_INITIAL_STEPS = ["upload", "analyze", "framework", "chapters", "export"]


class CreateTaskRequest(BaseModel):
    """Request body for POST /api/tasks."""
    initial_steps: list[str] | None = None  # default applied in route
    name: str | None = None


class AcceptFrameworkRequest(BaseModel):
    """Request body for POST /api/tasks/{id}/steps/framework/accept."""
    added_points: list[str] = []  # empty = accept and continue without adding points


class RunChaptersRequest(BaseModel):
    """Request body for POST /api/tasks/{id}/steps/chapters/run."""
    chapter_numbers: list[int] | None = None  # None or empty = all chapters


class SaveChapterPointsRequest(BaseModel):
    """Request body for POST /api/tasks/{id}/steps/chapters/save-points."""
    chapter_number: int
    added_points: list[str]


class RegenerateChapterRequest(BaseModel):
    """Request body for POST /api/tasks/{id}/steps/chapters/regenerate."""
    chapter_number: int
    added_points: list[str] | None = None


class AcceptReviewRequest(BaseModel):
    """Request body for POST /api/tasks/{id}/steps/review/accept."""
    chapter_number: int
    accepted_items: list[str]  # user-selected review item descriptions -> chapter_points


class TaskStepSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    step_key: str
    status: str
    input_snapshot: str | None
    output_snapshot: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class CreateTaskResponse(BaseModel):
    """Response for POST /api/tasks."""
    id: int
    name: str | None = None
    status: str
    created_at: datetime


class TaskDetailResponse(BaseModel):
    """Response for GET /api/tasks/{id} (task + steps)."""
    id: int
    user_id: str | None
    name: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    steps: list[TaskStepSchema]


class TaskCompareSummary(BaseModel):
    """Summary flags for compare capability on a task."""

    has_framework: bool
    chapter_count: int


class TaskSummary(BaseModel):
    """Brief task for GET /api/tasks list."""
    id: int
    name: str | None = None
    status: str
    created_at: datetime
    compare_summary: TaskCompareSummary | None = None