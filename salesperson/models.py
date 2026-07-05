from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class LLMConfig:
    provider: str
    model: str
    api_base: str | None = None


@dataclass(slots=True)
class SalesBehavior:
    system_prompt: str
    tone: str = "consultative"
    sales_goals: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Website:
    website_id: str
    name: str
    domain: str
    llm: LLMConfig
    plugin: dict[str, Any]
    behavior: SalesBehavior
    api_key_hash: str = ""


@dataclass(slots=True)
class WebsiteUser:
    user_id: str
    website_id: str
    external_user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class UsageRecord:
    website_id: str
    user_id: str
    channel: str
    messages: int
    tokens: int
    outcome: str | None = None
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class DealRecord:
    website_id: str
    user_id: str
    stage: str
    value: float
    currency: str = "USD"
    note: str = ""
    created_at: str = field(default_factory=utc_now)


@dataclass(slots=True)
class ChatMessage:
    role: str
    content: str


@dataclass(slots=True)
class ChatCompletionRequest:
    messages: list[ChatMessage]
    user_id: str | None = None
    channel: str = "website-widget"


@dataclass(slots=True)
class TokenUsage:
    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass(slots=True)
class ChatCompletionResponse:
    id: str
    message: ChatMessage
    usage: TokenUsage
    website_id: str
