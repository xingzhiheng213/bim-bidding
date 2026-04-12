"""Tests for params snapshot key_requirements / legacy bim_requirements compatibility."""
import unittest

from app.params_compat import (
    LEGACY_REQUIREMENTS_JSON_KEY,
    REQUIREMENTS_JSON_KEY,
    coalesce_requirements_from_llm_raw,
    extract_requirements_list,
    params_snapshot_has_requirements_list,
)
from tasks.params import _normalize_params


class TestCoalesceRequirementsFromLlmRaw(unittest.TestCase):
    def test_legacy_only(self):
        raw = {LEGACY_REQUIREMENTS_JSON_KEY: ["a", "b"]}
        self.assertEqual(coalesce_requirements_from_llm_raw(raw), ["a", "b"])

    def test_new_only(self):
        raw = {REQUIREMENTS_JSON_KEY: ["x"]}
        self.assertEqual(coalesce_requirements_from_llm_raw(raw), ["x"])

    def test_both_new_wins_even_if_empty(self):
        """If key_requirements is present (including []), ignore legacy list."""
        raw = {REQUIREMENTS_JSON_KEY: [], LEGACY_REQUIREMENTS_JSON_KEY: ["legacy"]}
        self.assertEqual(coalesce_requirements_from_llm_raw(raw), [])

    def test_both_new_nonempty_uses_new(self):
        raw = {
            REQUIREMENTS_JSON_KEY: ["new"],
            LEGACY_REQUIREMENTS_JSON_KEY: ["old"],
        }
        self.assertEqual(coalesce_requirements_from_llm_raw(raw), ["new"])

    def test_invalid_new_type_yields_empty(self):
        raw = {REQUIREMENTS_JSON_KEY: "not a list", LEGACY_REQUIREMENTS_JSON_KEY: ["z"]}
        self.assertEqual(coalesce_requirements_from_llm_raw(raw), [])


class TestExtractRequirementsList(unittest.TestCase):
    def test_prefers_new_when_both(self):
        out = {REQUIREMENTS_JSON_KEY: ["n"], LEGACY_REQUIREMENTS_JSON_KEY: ["o"]}
        self.assertEqual(extract_requirements_list(out), ["n"])

    def test_legacy_snapshot(self):
        out = {LEGACY_REQUIREMENTS_JSON_KEY: ["p", "q"]}
        self.assertEqual(extract_requirements_list(out), ["p", "q"])


class TestParamsSnapshotGate(unittest.TestCase):
    def test_new_list_ok(self):
        self.assertTrue(params_snapshot_has_requirements_list({REQUIREMENTS_JSON_KEY: []}))

    def test_legacy_list_ok(self):
        self.assertTrue(params_snapshot_has_requirements_list({LEGACY_REQUIREMENTS_JSON_KEY: []}))

    def test_missing_fails(self):
        self.assertFalse(params_snapshot_has_requirements_list({"project_info": {}}))


class TestNormalizeParamsPersist(unittest.TestCase):
    def test_normalize_writes_key_requirements_from_legacy_llm(self):
        raw = {
            "project_info": {},
            LEGACY_REQUIREMENTS_JSON_KEY: ["r1"],
            "risk_points": [],
            "scoring_items": [],
        }
        n = _normalize_params(raw)
        self.assertIn(REQUIREMENTS_JSON_KEY, n)
        self.assertNotIn(LEGACY_REQUIREMENTS_JSON_KEY, n)
        self.assertEqual(n[REQUIREMENTS_JSON_KEY], ["r1"])


if __name__ == "__main__":
    unittest.main()
