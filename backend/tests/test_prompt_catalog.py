"""Prompt catalog API and REVIEW_SYSTEM split consistency."""
from app.auth import verify_api_key
from app.main import app
from app.prompts import REVIEW_OUTPUT_FORMAT_SPEC, REVIEW_SYSTEM, REVIEW_SYSTEM_SEMANTIC
from fastapi.testclient import TestClient


async def _verify_api_key_override() -> None:
    """Bypass ADMIN_API_KEY for this test module only."""
    return None


def test_review_system_equals_semantic_plus_output_spec():
    assert REVIEW_SYSTEM == REVIEW_SYSTEM_SEMANTIC + "\n\n" + REVIEW_OUTPUT_FORMAT_SPEC


def test_get_prompt_catalog_ok():
    app.dependency_overrides[verify_api_key] = _verify_api_key_override
    try:
        client = TestClient(app)
        r = client.get("/api/settings/prompt-catalog")
        assert r.status_code == 200
        data = r.json()
        assert "contract_items" in data and "semantic_items" in data
        contract = data["contract_items"]
        semantic = data["semantic_items"]
        assert len(contract) >= 8 and len(semantic) >= 10
        contract_text = "\n".join(x["content"] for x in contract)
        assert "key_requirements" in contract_text
        semantic_text = "\n".join(x["content"] for x in semantic)
        assert "BIM技术标" in semantic_text or "BIM" in semantic_text
    finally:
        app.dependency_overrides.pop(verify_api_key, None)
