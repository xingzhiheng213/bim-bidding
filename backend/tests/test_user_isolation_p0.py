"""P0 isolation tests: task/profile/settings are scoped by tenant+user."""
from __future__ import annotations

import uuid

from app.auth import verify_api_key
from app.main import app
from fastapi.testclient import TestClient


async def _verify_api_key_override() -> None:
    return None


def _headers(tenant_id: str, user_id: str) -> dict[str, str]:
    return {
        "X-Debug-Tenant-Id": tenant_id,
        "X-Debug-User-Id": user_id,
    }


def test_tasks_are_isolated_by_user():
    app.dependency_overrides[verify_api_key] = _verify_api_key_override
    try:
        tenant = f"t-{uuid.uuid4().hex[:8]}"
        a = _headers(tenant, "user-a")
        b = _headers(tenant, "user-b")
        client = TestClient(app)

        created = client.post("/api/tasks", json={"name": "A 的任务"}, headers=a)
        assert created.status_code == 201
        task_id = created.json()["id"]

        list_a = client.get("/api/tasks", headers=a)
        assert list_a.status_code == 200
        assert any(int(x["id"]) == int(task_id) for x in list_a.json())

        list_b = client.get("/api/tasks", headers=b)
        assert list_b.status_code == 200
        assert all(int(x["id"]) != int(task_id) for x in list_b.json())

        detail_b = client.get(f"/api/tasks/{task_id}", headers=b)
        assert detail_b.status_code == 404
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


def test_prompt_profiles_are_isolated_by_user():
    app.dependency_overrides[verify_api_key] = _verify_api_key_override
    try:
        tenant = f"t-{uuid.uuid4().hex[:8]}"
        a = _headers(tenant, "user-a")
        b = _headers(tenant, "user-b")
        client = TestClient(app)

        created = client.post(
            "/api/prompt-profiles",
            json={"name": "A-profile", "discipline": "建筑"},
            headers=a,
        )
        assert created.status_code == 201
        profile_id = created.json()["id"]

        list_a = client.get("/api/prompt-profiles", headers=a)
        assert list_a.status_code == 200
        assert any(int(x["id"]) == int(profile_id) for x in list_a.json())

        list_b = client.get("/api/prompt-profiles", headers=b)
        assert list_b.status_code == 200
        assert all(int(x["id"]) != int(profile_id) for x in list_b.json())

        detail_b = client.get(f"/api/prompt-profiles/{profile_id}", headers=b)
        assert detail_b.status_code == 404
    finally:
        app.dependency_overrides.pop(verify_api_key, None)


def test_llm_settings_are_isolated_by_user():
    app.dependency_overrides[verify_api_key] = _verify_api_key_override
    try:
        tenant = f"t-{uuid.uuid4().hex[:8]}"
        a = _headers(tenant, "user-a")
        b = _headers(tenant, "user-b")
        client = TestClient(app)

        save_a = client.post(
            "/api/settings/llm",
            json={"provider": "deepseek", "api_key": "sk-test-user-a"},
            headers=a,
        )
        assert save_a.status_code == 200
        assert save_a.json()["configured"] is True

        get_a = client.get("/api/settings/llm", headers=a)
        assert get_a.status_code == 200
        provider_a = next(x for x in get_a.json()["providers"] if x["provider"] == "deepseek")
        assert provider_a["configured"] is True

        get_b = client.get("/api/settings/llm", headers=b)
        assert get_b.status_code == 200
        provider_b = next(x for x in get_b.json()["providers"] if x["provider"] == "deepseek")
        assert provider_b["configured"] is False
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
