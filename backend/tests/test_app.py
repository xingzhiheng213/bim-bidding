"""FastAPI 应用冒烟：健康检查（不依赖数据库/Redis）。"""
from app.main import app
from fastapi.testclient import TestClient


def test_health_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
