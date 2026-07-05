from __future__ import annotations

from salesperson.config import LLM_PROVIDER
from salesperson.providers.base import LLMProvider
from salesperson.providers.stub import StubLLMProvider

_DEMO_ALIASES = {"demo", "stub", ""}


def create_provider(name: str | None = None) -> LLMProvider:
    provider = (name or LLM_PROVIDER).strip().lower()
    if provider in _DEMO_ALIASES:
        return StubLLMProvider()
    raise ValueError(
        f"Unsupported LLM provider {provider!r}. "
        "Use demo (default) for local development; openai/anthropic coming soon."
    )
