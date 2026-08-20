import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from app.runtime_settings import RuntimeSettingsError, validate_runtime_settings
from app.script_generation import ScriptGenerationError, generate_script_with_single_provider


class SingleProviderExecutionTests(unittest.TestCase):
    def test_openai_compatible_adapter_dispatch(self):
        expected = {"script": "ok", "usage": {"total_tokens": 42}, "raw": {}}
        with patch("app.script_generation._generate_with_openai_compatible_api", return_value=expected) as mocked:
            result = generate_script_with_single_provider(
                provider="openrouter",
                provider_adapter="openai_compatible",
                prompt_text="bonjour",
                api_url="https://openrouter.ai/api/v1/chat/completions",
                api_key="key",
                api_model="openai/gpt-4o-mini",
                max_retries=1,
                per_episode_token_cap=10000,
            )

        self.assertEqual(result, expected)
        mocked.assert_called_once()

    def test_unsupported_adapter_raises(self):
        with self.assertRaises(ScriptGenerationError) as ctx:
            generate_script_with_single_provider(
                provider="openai",
                provider_adapter="unknown_adapter",
                prompt_text="bonjour",
                api_url="https://api.openai.com/v1/chat/completions",
                api_key="key",
                api_model="gpt-4o-mini",
                max_retries=1,
                per_episode_token_cap=10000,
            )
        self.assertIn("Unsupported provider adapter", str(ctx.exception))

    def test_openai_compatible_http_error_is_logged(self):
        http_error = HTTPError(
            url="https://api.openai.com/v1/chat/completions",
            code=502,
            msg="Bad Gateway",
            hdrs=None,
            fp=io.BytesIO(b'{"error":"upstream unavailable"}'),
        )

        with self.assertLogs("app.script_generation", level="WARNING") as captured, patch(
            "app.script_generation.urlopen",
            side_effect=http_error,
        ):
            with self.assertRaises(ScriptGenerationError) as ctx:
                generate_script_with_single_provider(
                    provider="openai",
                    provider_adapter="openai_compatible",
                    prompt_text="bonjour",
                    api_url="https://api.openai.com/v1/chat/completions",
                    api_key="key",
                    api_model="gpt-4o-mini",
                    max_retries=0,
                    per_episode_token_cap=10000,
                )

        self.assertIn("HTTP 502", str(ctx.exception))
        self.assertTrue(
            any("Script generation provider request failed with HTTP error" in entry for entry in captured.output)
        )


class RuntimeConfigValidationTests(unittest.TestCase):
    def test_supported_provider_is_normalized_and_typed(self):
        settings = {
            "api_provider": "OpenRouter",
            "api_url": "https://openrouter.ai/api/v1/chat/completions",
            "api_key": "key",
            "api_model": "openai/gpt-4o-mini",
            "max_retries": "2",
            "max_prompt_chars": "15000",
            "input_cents_per_million": "20",
            "output_cents_per_million": "70",
        }

        normalized = validate_runtime_settings(settings)
        self.assertEqual(normalized["api_provider"], "openrouter")
        self.assertEqual(normalized["provider_adapter"], "openai_compatible")
        self.assertEqual(normalized["max_retries"], 2)
        self.assertEqual(normalized["max_prompt_chars"], 15000)
        self.assertEqual(normalized["input_cents_per_million"], 20)
        self.assertEqual(normalized["output_cents_per_million"], 70)

    def test_missing_provider_raises(self):
        with self.assertRaises(RuntimeSettingsError) as ctx:
            validate_runtime_settings(
                {
                    "api_provider": "",
                    "api_url": "https://api.openai.com/v1/chat/completions",
                    "api_model": "gpt-4o-mini",
                    "max_retries": "1",
                    "max_prompt_chars": "20000",
                    "input_cents_per_million": "15",
                    "output_cents_per_million": "60",
                }
            )
        self.assertIn("Missing provider selection", str(ctx.exception))

    def test_invalid_provider_raises(self):
        with self.assertRaises(RuntimeSettingsError) as ctx:
            validate_runtime_settings(
                {
                    "api_provider": "some-new-provider",
                    "api_url": "https://api.example.com/v1/chat/completions",
                    "api_model": "model",
                    "max_retries": "1",
                    "max_prompt_chars": "20000",
                    "input_cents_per_million": "15",
                    "output_cents_per_million": "60",
                }
            )
        self.assertIn("Unsupported provider", str(ctx.exception))

    def test_invalid_url_scheme_raises(self):
        with self.assertRaises(RuntimeSettingsError) as ctx:
            validate_runtime_settings(
                {
                    "api_provider": "openai",
                    "api_url": "ftp://api.openai.com/v1/chat/completions",
                    "api_model": "gpt-4o-mini",
                    "max_retries": "1",
                    "max_prompt_chars": "20000",
                    "input_cents_per_million": "15",
                    "output_cents_per_million": "60",
                }
            )
        self.assertIn("must start with http:// or https://", str(ctx.exception))

    def test_invalid_numeric_values_raise(self):
        with self.assertRaises(RuntimeSettingsError) as ctx:
            validate_runtime_settings(
                {
                    "api_provider": "openai",
                    "api_url": "https://api.openai.com/v1/chat/completions",
                    "api_model": "gpt-4o-mini",
                    "max_retries": "-1",
                    "max_prompt_chars": "20000",
                    "input_cents_per_million": "15",
                    "output_cents_per_million": "60",
                }
            )
        self.assertIn("PODCAST_LLM_MAX_RETRIES must be >= 0", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
