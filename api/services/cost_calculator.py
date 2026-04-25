from __future__ import annotations

import os
from decimal import Decimal, ROUND_HALF_UP


def _decimal_from_env(name: str, default: str) -> Decimal:
    return Decimal(os.getenv(name, default))


class CostCalculator:
    """Demo cost estimator. Pricing is configurable and not authoritative."""

    def __init__(self) -> None:
        self.input_price_per_1m = _decimal_from_env(
            "DEMO_MODEL_INPUT_PRICE_PER_1M_TOKENS",
            "0.15",
        )
        self.output_price_per_1m = _decimal_from_env(
            "DEMO_MODEL_OUTPUT_PRICE_PER_1M_TOKENS",
            "0.60",
        )

    def estimate_cost_usd(self, prompt_tokens: int, completion_tokens: int) -> float:
        prompt_cost = Decimal(prompt_tokens) * self.input_price_per_1m / Decimal(1_000_000)
        completion_cost = (
            Decimal(completion_tokens) * self.output_price_per_1m / Decimal(1_000_000)
        )
        total = prompt_cost + completion_cost
        return float(total.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))

    def estimate_prompt_tokens(self, text: str) -> int:
        # Good enough for pre-call guardrails in the local MVP.
        return max(1, len(text.split()) * 2)

