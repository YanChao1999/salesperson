from __future__ import annotations

from typing import Protocol

from salesperson.models import ChatMessage, LLMConfig, SalesBehavior, TokenUsage


class LLMProvider(Protocol):
    def complete(
        self,
        *,
        llm: LLMConfig,
        behavior: SalesBehavior,
        messages: list[ChatMessage],
    ) -> tuple[ChatMessage, TokenUsage]: ...
