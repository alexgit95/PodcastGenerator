import unittest

from app.guardrails import (
    is_monthly_budget_exhausted,
    is_prompt_cap_exceeded,
    would_exceed_monthly_budget,
)
from app.script_generation import estimate_cost_cents, estimate_tokens_from_text


class GuardrailTests(unittest.TestCase):
    def test_prompt_cap_blocks_when_equal_or_higher(self):
        self.assertTrue(is_prompt_cap_exceeded(100, 100))
        self.assertTrue(is_prompt_cap_exceeded(101, 100))
        self.assertFalse(is_prompt_cap_exceeded(99, 100))

    def test_monthly_budget_exhaustion(self):
        self.assertTrue(is_monthly_budget_exhausted(100, 100))
        self.assertTrue(is_monthly_budget_exhausted(120, 100))
        self.assertFalse(is_monthly_budget_exhausted(99, 100))

    def test_monthly_budget_would_exceed(self):
        self.assertTrue(would_exceed_monthly_budget(95, 10, 100))
        self.assertFalse(would_exceed_monthly_budget(90, 10, 100))

    def test_estimation_helpers(self):
        text = "Bonjour le monde"
        tokens = estimate_tokens_from_text(text)
        self.assertGreater(tokens, 0)

        cost = estimate_cost_cents(
            input_tokens=20_000,
            output_tokens=8_000,
            input_cents_per_million=15,
            output_cents_per_million=60,
        )
        self.assertGreaterEqual(cost, 1)


if __name__ == "__main__":
    unittest.main()
