"""P1 isolation regression tests: async owner guard, scoped slug uniqueness, upload path."""

from __future__ import annotations

import uuid

from app import config
from app.auth import verify_api_key
from app.database import SessionLocal
from app.main import app
from app.models import TaskStep
from fastapi.testclient import TestClient
from tasks.extract import run_extract


async def _verify_api_key_override() -> None:
    return None


def _headers(tenant_id: str, user_id: str) -> dict[str, str]:
    return {
        "X-Debug-Tenant-Id": tenant_id,
        "X-Debug-User-Id": user_id,
    }


def _pdf_bytes_for_upload() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def test_extract_worker_scope_guard_rejects_mismatched_identity():
    app.dependency_overrides[verify_api_key] = _verify_api_key_override
    try:
        tenant = f"t-{uuid.uuid4().hex[:8]}"
        a = _headers(tenant, "user-a")
        client = TestClient(app)

        created = client.post("/api/tasks", json={"name": "scope-guard"}, headers=a)
        assert created.status_code == 201
        task_id = int(created.json()["id"])

        run_extract(task_id, tenant_id=tenant, user_id="user-b")

        db = SessionLocal()
        try:
            step = (
                db.query(TaskStep)
                .filter(TaskStep.task_id == task_id, TaskStep.step_key == "extract")
                .first()
            )
            assert step is not None
            assert step.status == "failed"
            assert step.error_message == "任务归属校验失败"
        finally:
            db.close()
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


def test_extract_worker_scope_guard_allows_owner_identity():
    app.dependency_overrides[verify_api_key] = _verify_api_key_override
    try:
        tenant = f"t-{uuid.uuid4().hex[:8]}"
        a = _headers(tenant, "user-a")
        client = TestClient(app)

        created = client.post("/api/tasks", json={"name": "scope-guard-ok"}, headers=a)
        assert created.status_code == 201
        task_id = int(created.json()["id"])

        run_extract(task_id, tenant_id=tenant, user_id="user-a")

        db = SessionLocal()
        try:
            step = (
                db.query(TaskStep)
                .filter(TaskStep.task_id == task_id, TaskStep.step_key == "extract")
                .first()
            )
            assert step is not None
            assert step.status == "failed"
            assert step.error_message == "请先完成上传"
        finally:
            db.close()
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


def test_prompt_profile_slug_is_unique_per_tenant_and_user():
    app.dependency_overrides[verify_api_key] = _verify_api_key_override
    try:
        tenant = f"t-{uuid.uuid4().hex[:8]}"
        a = _headers(tenant, "user-a")
        b = _headers(tenant, "user-b")
        client = TestClient(app)
        slug = f"slug-{uuid.uuid4().hex[:8]}"

        created_a = client.post(
            "/api/prompt-profiles",
            json={"name": "A profile", "discipline": "建筑", "slug": slug},
            headers=a,
        )
        assert created_a.status_code == 201

        duplicate_same_user = client.post(
            "/api/prompt-profiles",
            json={"name": "A profile 2", "discipline": "建筑", "slug": slug},
            headers=a,
        )
        assert duplicate_same_user.status_code == 400

        same_slug_other_user = client.post(
            "/api/prompt-profiles",
            json={"name": "B profile", "discipline": "建筑", "slug": slug},
            headers=b,
        )
        assert same_slug_other_user.status_code == 201
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


def test_upload_path_and_delete_cleanup_regression():
    app.dependency_overrides[verify_api_key] = _verify_api_key_override
    try:
        tenant = f"t-{uuid.uuid4().hex[:8]}"
        user = f"user-{uuid.uuid4().hex[:6]}"
        headers = _headers(tenant, user)
        client = TestClient(app)

        created = client.post("/api/tasks", json={"name": "upload-cleanup"}, headers=headers)
        assert created.status_code == 201
        task_id = int(created.json()["id"])

        upload_resp = client.post(
            f"/api/tasks/{task_id}/upload",
            headers=headers,
            files={"file": ("sample.pdf", _pdf_bytes_for_upload(), "application/pdf")},
        )
        assert upload_resp.status_code == 201
        stored_path = upload_resp.json()["stored_path"]
        expected_prefix = f"tenant_{tenant}/user_{user}/task_{task_id}/"
        assert stored_path.startswith(expected_prefix)

        physical_file = config.UPLOAD_DIR / stored_path
        assert physical_file.exists()

        delete_resp = client.delete(f"/api/tasks/{task_id}", headers=headers)
        assert delete_resp.status_code == 204

        scoped_dir = config.UPLOAD_DIR / f"tenant_{tenant}" / f"user_{user}" / f"task_{task_id}"
        assert not scoped_dir.exists()
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
