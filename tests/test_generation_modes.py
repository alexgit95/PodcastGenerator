from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
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

    def setUp(self):
        repository.update_generation_mode(self.profile["id"], "llm")
        repository.update_audio_generation_mode(self.profile["id"], "local")
        repository.update_deterministic_global_settings(
            self.profile["id"],
            {
                "version": 1,
                "target_duration_sec": 600,
                "speech_rate_wpm": 155,
                "freshness_hours_max": 48,
                "max_items_per_category_default": 3,
                "min_items_per_category_default": 1,
                "scoring_weights": repository.DETERMINISTIC_SCORING_WEIGHTS,
                "extractive_rules": repository.DETERMINISTIC_EXTRACTIVE_RULES,
                "trim_policy": repository.DETERMINISTIC_TRIM_POLICY,
                "fallback_policy": repository.DETERMINISTIC_FALLBACK_POLICY,
            },
        )

    def _patch_feed(self):
        published_at = datetime.now(timezone.utc) - timedelta(hours=1)
        return patch.object(
            rss_collection,
            "_fetch_source_items",
            return_value=[
                {
                    "title": "Fresh item A",
                    "link": "https://example.com/fresh-a",
                    "published_at": published_at,
                },
                {
                    "title": "Fresh item B",
                    "link": "https://example.com/fresh-b",
                    "published_at": published_at - timedelta(minutes=5),
                },
                {
                    "title": "Fresh item C",
                    "link": "https://example.com/fresh-c",
                    "published_at": published_at - timedelta(minutes=10),
                },
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

    def test_llm_mode_logs_provider_failure_before_returning_502(self):
        with patch.dict(os.environ, LLM_ENV, clear=False), self._patch_feed(), self.assertLogs(
            flask_app.logger.name,
            level="ERROR",
        ) as captured, patch.object(
            main_module,
            "generate_script_with_single_provider",
            side_effect=main_module.ScriptGenerationError("HTTP 502: upstream unavailable"),
        ):
            response = self.client.post(
                "/api/generate/script",
                json={"duration_target_minutes": 1, "category_ids": [self.category["id"]]},
            )

        self.assertEqual(response.status_code, 502)
        payload = response.get_json()
        self.assertEqual(payload["status"], "generation_error")
        self.assertIn("HTTP 502", payload["error"])
        self.assertTrue(any("Script generation failed in provider mode" in entry for entry in captured.output))

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
                json={"duration_target_minutes": 3, "category_ids": [self.category["id"]]},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["mode_used"], "deterministic")
        self.assertIn("Fresh item A", payload["script"])

        with patch.dict(os.environ, LLM_ENV, clear=False):
            self.client.put("/api/settings/mode", json={"generation_mode": "llm"})

    def test_deterministic_mode_does_not_repeat_first_item_in_category_intro(self):
        with patch.dict(os.environ, {}, clear=True), self._patch_feed(), patch.object(
            main_module,
            "generate_script_with_single_provider",
            side_effect=AssertionError("LLM provider must not be called in deterministic mode"),
        ):
            mode_response = self.client.put("/api/settings/mode", json={"generation_mode": "deterministic"})
            self.assertEqual(mode_response.status_code, 200)

            response = self.client.post(
                "/api/generate/script",
                json={"duration_target_minutes": 3, "category_ids": [self.category["id"]]},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["script"].count("Fresh item A"), 1)

        with patch.dict(os.environ, LLM_ENV, clear=False):
            self.client.put("/api/settings/mode", json={"generation_mode": "llm"})

    def test_script_generation_no_longer_returns_audio_artifact(self):
        with patch.dict(os.environ, LLM_ENV, clear=False), self._patch_feed(), patch.object(
            main_module,
            "generate_script_with_single_provider",
            return_value={
                "script": "script llm",
                "usage": {"input_tokens": 12, "output_tokens": 34, "total_tokens": 46},
                "raw": {},
            },
        ):
            response = self.client.post(
                "/api/generate/script",
                json={"duration_target_minutes": 1, "category_ids": [self.category["id"]]},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertNotIn("audio", payload)
        self.assertEqual(payload["script"], "script llm")

    def test_audio_generation_requires_script_text_and_uses_separate_endpoint(self):
        with patch.dict(os.environ, LLM_ENV, clear=False), patch.object(
            main_module,
            "generate_local_mp3",
            return_value={
                "audio_file_name": "job-1.mp3",
                "audio_download_url": "/api/generation-jobs/job-1/audio",
                "audio_format": "mp3",
                "audio_mode_used": "local",
            },
        ):
            response = self.client.post("/api/generate/audio", json={"script_text": "Bonjour"})

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["audio"]["audio_download_url"], "/api/generation-jobs/job-1/audio")

    def test_scheduled_generation_runs_script_then_audio_in_local_mode(self):
        with patch.dict(os.environ, LLM_ENV, clear=False), self._patch_feed(), patch.object(
            main_module,
            "generate_script_with_single_provider",
            return_value={
                "script": "script llm cron",
                "usage": {"input_tokens": 12, "output_tokens": 34, "total_tokens": 46},
                "raw": {},
            },
        ), patch.object(
            main_module,
            "generate_local_mp3",
            return_value={
                "audio_file_name": "job-1.mp3",
                "audio_download_url": "/api/generation-jobs/job-1/audio",
                "audio_format": "mp3",
                "audio_mode_used": "local",
            },
        ):
            self.client.put("/api/settings/audio-mode", json={"audio_generation_mode": "local"})
            response = self.client.post(
                "/api/generate/scheduled",
                json={"duration_target_minutes": 1, "category_ids": [self.category["id"]]},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["script_stage"]["status"], "succeeded")
        self.assertEqual(payload["audio_stage"]["status"], "succeeded")
        self.assertEqual(payload["audio_stage"]["audio"]["audio_download_url"], "/api/generation-jobs/job-1/audio")

    def test_scheduled_generation_blocks_audio_stage_in_cloud_mode(self):
        with patch.dict(os.environ, LLM_ENV, clear=False), self._patch_feed(), patch.object(
            main_module,
            "generate_script_with_single_provider",
            return_value={
                "script": "script llm cron",
                "usage": {"input_tokens": 12, "output_tokens": 34, "total_tokens": 46},
                "raw": {},
            },
        ):
            self.client.put("/api/settings/audio-mode", json={"audio_generation_mode": "cloud"})
            response = self.client.post(
                "/api/generate/scheduled",
                json={"duration_target_minutes": 1, "category_ids": [self.category["id"]]},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["status"], "partial_success")
        self.assertEqual(payload["script_stage"]["status"], "succeeded")
        self.assertEqual(payload["audio_stage"]["status"], "blocked")
        self.assertEqual(payload["audio_stage"]["mode_used"], "cloud")
        self.assertIn("audio_mode_not_local", payload["audio_stage"]["reason"])

        with patch.dict(os.environ, LLM_ENV, clear=False):
            self.client.put("/api/settings/audio-mode", json={"audio_generation_mode": "local"})

    def test_latest_audio_endpoint_returns_latest_downloadable_audio(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)

            def _fake_generate_local_mp3(_script_text: str, job_id: str):
                (output_dir / f"{job_id}.mp3").write_bytes(b"mp3")
                return {
                    "audio_file_name": f"{job_id}.mp3",
                    "audio_download_url": f"/api/generation-jobs/{job_id}/audio",
                    "audio_format": "mp3",
                    "audio_mode_used": "local",
                }

            with patch.object(main_module, "AUDIO_OUTPUT_DIR", output_dir), patch.object(
                main_module,
                "generate_local_mp3",
                side_effect=_fake_generate_local_mp3,
            ):
                generate_response = self.client.post("/api/generate/audio", json={"script_text": "Bonjour"})
                self.assertEqual(generate_response.status_code, 200)

                latest_response = self.client.get("/api/generate/audio/latest")

            self.assertEqual(latest_response.status_code, 200)
            payload = latest_response.get_json()
            generated_job_id = generate_response.get_json()["job_id"]
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["job_id"], generated_job_id)
            self.assertEqual(payload["download_url"], f"/api/generation-jobs/{generated_job_id}/audio")

    def test_latest_audio_endpoint_reports_missing_artifact(self):
        profile = repository.get_or_create_default_profile()
        audio_job_id = repository.create_generation_job(
            profile["id"],
            "audio_generation",
            "running",
            {"mode_used": "local"},
        )
        repository.update_generation_job(
            audio_job_id,
            "succeeded",
            {
                "mode_used": "local",
                "audio": {
                    "audio_file_name": f"{audio_job_id}.mp3",
                    "audio_download_url": f"/api/generation-jobs/{audio_job_id}/audio",
                    "audio_format": "mp3",
                    "audio_mode_used": "local",
                },
            },
        )

        response = self.client.get("/api/generate/audio/latest")
        self.assertEqual(response.status_code, 404)
        payload = response.get_json()
        self.assertEqual(payload["status"], "not_found")
        self.assertEqual(payload["reason"], "audio_artifact_missing")

    def test_invalid_mode_payload_is_rejected(self):
        response = self.client.put("/api/settings/mode", json={"generation_mode": "hybrid"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("generation_mode", response.get_json()["error"])

    def test_version_endpoint_returns_fallback_when_env_missing(self):
        with patch.dict(os.environ, {"PODCAST_BUILD_COMMIT_SHA": ""}, clear=False):
            response = self.client.get("/api/version")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["commit_sha"], "unknown")
        self.assertEqual(payload["commit_short"], "unknown")

    def test_version_endpoint_returns_short_sha_from_env(self):
        with patch.dict(os.environ, {"PODCAST_BUILD_COMMIT_SHA": "abcdef1234567890"}, clear=False):
            response = self.client.get("/api/version")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["commit_sha"], "abcdef1234567890")
        self.assertEqual(payload["commit_short"], "abcdef1")

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

    def test_invalid_brief_seconds_setting_is_rejected(self):
        response = self.client.put(
            "/api/settings/deterministic/global",
            json={
                "version": 1,
                "target_duration_sec": 600,
                "speech_rate_wpm": 155,
                "freshness_hours_max": 48,
                "max_items_per_category_default": 3,
                "min_items_per_category_default": 1,
                "scoring_weights": {"freshness": 0.45},
                "extractive_rules": {"briefSecondsTarget": 2},
                "trim_policy": {"order": ["conclusion"]},
                "fallback_policy": {"ifNoItems": "skipCategoryAndRebalance"},
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("between 5 and 180", response.get_json()["error"])

    def test_deterministic_brief_seconds_and_alignment_are_applied(self):
        with patch.dict(os.environ, {}, clear=True), self._patch_feed(), patch.object(
            main_module,
            "generate_script_with_single_provider",
            side_effect=AssertionError("LLM provider must not be called in deterministic mode"),
        ):
            mode_response = self.client.put("/api/settings/mode", json={"generation_mode": "deterministic"})
            self.assertEqual(mode_response.status_code, 200)

            settings_response = self.client.put(
                "/api/settings/deterministic/global",
                json={
                    "version": 1,
                    "target_duration_sec": 600,
                    "speech_rate_wpm": 155,
                    "freshness_hours_max": 48,
                    "max_items_per_category_default": 3,
                    "min_items_per_category_default": 1,
                    "scoring_weights": {"freshness": 0.45, "sourceCredibility": 0.3, "textRichness": 0.15, "diversity": 0.1},
                    "extractive_rules": {
                        "maxSentencesPerItem": 2,
                        "minSentenceChars": 40,
                        "maxSentenceChars": 220,
                        "stripQuotesIfLong": True,
                        "briefSecondsTarget": 20,
                        "durationAlignmentEnabled": True,
                    },
                    "trim_policy": {"order": ["conclusion", "transitions", "lowestPriorityItem"], "stepSec": 15, "hardFloorSec": 540},
                    "fallback_policy": {"ifTooShortAdd": ["whyItMatters", "watchNext"], "ifNoItems": "skipCategoryAndRebalance"},
                },
            )
            self.assertEqual(settings_response.status_code, 200)
            settings_payload = settings_response.get_json()
            self.assertEqual(settings_payload["extractive_rules"]["briefSecondsTarget"], 20)
            self.assertTrue(settings_payload["extractive_rules"]["durationAlignmentEnabled"])

            response = self.client.post(
                "/api/generate/script",
                json={"duration_target_minutes": 3, "category_ids": [self.category["id"]]},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["preview"]["brief_seconds"], 20)
        brief_lines = [line for line in payload["script"].splitlines() if "Fresh item" in line]
        self.assertTrue(brief_lines)
        # With alignment enabled, at least one brief line should be expanded beyond a short one-liner.
        self.assertTrue(any(len(line.split()) >= 18 for line in brief_lines))

        with patch.dict(os.environ, LLM_ENV, clear=False):
            self.client.put("/api/settings/mode", json={"generation_mode": "llm"})

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
