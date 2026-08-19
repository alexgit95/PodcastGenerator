from __future__ import annotations

import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

LLM_ENV = {
    "PODCAST_LLM_PROVIDER": "openai",
    "PODCAST_LLM_API_URL": "https://api.openai.com/v1/chat/completions",
    "PODCAST_LLM_API_KEY": "test-key",
    "PODCAST_LLM_MODEL": "gpt-4o-mini",
    "PODCAST_LLM_MAX_RETRIES": "1",
    "PODCAST_LLM_MAX_PROMPT_CHARS": "20000",
    "PODCAST_LLM_INPUT_CENTS_PER_MILLION": "15",
    "PODCAST_LLM_OUTPUT_CENTS_PER_MILLION": "60",
}

with patch.dict(os.environ, LLM_ENV, clear=False):
    try:
        from app import repository
        from app.db import get_connection
        from app.main import app as flask_app
        import app.main as main_module
        import app.rss_collection as rss_collection
        FLASK_AVAILABLE = True
    except ModuleNotFoundError:
        FLASK_AVAILABLE = False


if not FLASK_AVAILABLE:
    raise unittest.SkipTest("Flask is not installed in the embedded Python environment")


class GenerationModeApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = flask_app.test_client()
        cls.profile = repository.get_or_create_default_profile()
        with get_connection() as conn:
            conn.execute("DELETE FROM monthly_api_spend WHERE profile_id = ?", (cls.profile["id"],))
            conn.commit()

        category_name = f"Test Cat {datetime.utcnow().timestamp()}"
        source_url = f"https://example.com/{datetime.utcnow().timestamp()}.xml"
        cls.category = repository.create_category(
            {
                "name": category_name,
                "description": "Test category",
                "enabled": True,
                "default_weight": 1,
            }
        )
        cls.source = repository.create_source(
            {
                "url": source_url,
                "title": "Test Source",
                "enabled": True,
            }
        )
        repository.create_mapping(cls.category["id"], cls.source["id"])

    @classmethod
    def tearDownClass(cls):
        with patch.dict(os.environ, LLM_ENV, clear=False):
            cls.client.put("/api/settings/mode", json={"generation_mode": "llm"})

    def _patch_feed(self):
        published_at = datetime.now(timezone.utc) - timedelta(hours=1)
        return patch.object(
            rss_collection,
            "_fetch_source_items",
            return_value=[
                {
                    "title": "Fresh item",
                    "link": "https://example.com/fresh",
                    "published_at": published_at,
                }
            ],
        )

    def test_llm_mode_dispatches_to_provider(self):
        with patch.dict(os.environ, LLM_ENV, clear=False), self._patch_feed(), patch.object(
            main_module,
            "generate_script_with_single_provider",
            return_value={
                "script": "script llm",
                "usage": {"input_tokens": 12, "output_tokens": 34, "total_tokens": 46},
                "raw": {},
            },
        ) as mocked_generate:
            response = self.client.post(
                "/api/generate/script",
                json={"duration_target_minutes": 1, "category_ids": [self.category["id"]]},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["mode_used"], "llm")
        self.assertEqual(payload["script"], "script llm")
        self.assertTrue(mocked_generate.called)

    def test_deterministic_mode_runs_without_llm_credentials(self):
        with patch.dict(os.environ, {}, clear=True), self._patch_feed(), patch.object(
            main_module,
            "generate_script_with_single_provider",
            side_effect=AssertionError("LLM provider must not be called in deterministic mode"),
        ):
            mode_response = self.client.put("/api/settings/mode", json={"generation_mode": "deterministic"})
            self.assertEqual(mode_response.status_code, 200)

            response = self.client.post(
                "/api/generate/script",
                json={"duration_target_minutes": 1, "category_ids": [self.category["id"]]},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["mode_used"], "deterministic")
        self.assertIn("Bonjour", payload["script"])

        with patch.dict(os.environ, LLM_ENV, clear=False):
            self.client.put("/api/settings/mode", json={"generation_mode": "llm"})

    def test_invalid_mode_payload_is_rejected(self):
        response = self.client.put("/api/settings/mode", json={"generation_mode": "hybrid"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("generation_mode", response.get_json()["error"])

    def test_invalid_deterministic_global_payload_is_rejected(self):
        response = self.client.put(
            "/api/settings/deterministic/global",
            json={
                "target_duration_sec": 60,
                "speech_rate_wpm": 155,
                "freshness_hours_max": 48,
                "max_items_per_category_default": 3,
                "min_items_per_category_default": 1,
                "scoring_weights": {"freshness": 0.45},
                "extractive_rules": {"maxSentencesPerItem": 2},
                "trim_policy": {"order": ["conclusion"]},
                "fallback_policy": {"ifNoItems": "skipCategoryAndRebalance"},
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("between 120 and 3600", response.get_json()["error"])

    def test_invalid_deterministic_category_payload_is_rejected(self):
        response = self.client.put(
            f"/api/settings/deterministic/categories/{self.category['id']}",
            json={
                "enabled": True,
                "weight": 0,
                "max_items": 2,
                "templates": {"leadIn": "test"},
                "scoring_override": {"freshness": 0.5},
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("weight", response.get_json()["error"].lower())


if __name__ == "__main__":
    unittest.main()
