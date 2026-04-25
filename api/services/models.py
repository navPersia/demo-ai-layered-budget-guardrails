from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetDecision:
    allowed: bool
    reason: str | None = None


@dataclass(frozen=True)
class ChatResult:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

