from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import re
from typing import Any


class PlatformNotFoundError(KeyError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "website"


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


@dataclass(slots=True)
class WebsiteUser:
    user_id: str
    website_id: str
    external_user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_utc_now)


@dataclass(slots=True)
class UsageRecord:
    website_id: str
    user_id: str
    channel: str
    messages: int
    tokens: int
    outcome: str | None = None
    created_at: str = field(default_factory=_utc_now)


@dataclass(slots=True)
class DealRecord:
    website_id: str
    user_id: str
    stage: str
    value: float
    currency: str = "USD"
    note: str = ""
    created_at: str = field(default_factory=_utc_now)


class SalespersonPlatform:
    def __init__(self, agent_base_url: str = "https://agent.example.com") -> None:
        self.agent_base_url = agent_base_url.rstrip("/")
        self._websites: dict[str, Website] = {}
        self._users: dict[str, dict[str, WebsiteUser]] = {}
        self._usage: dict[str, list[UsageRecord]] = {}
        self._deals: dict[str, list[DealRecord]] = {}
        self._user_sequence: dict[str, int] = {}

    def create_website(
        self,
        *,
        name: str,
        domain: str,
        llm_provider: str,
        llm_model: str,
        llm_api_base: str | None = None,
    ) -> dict[str, Any]:
        if not name.strip():
            raise ValueError("Website name is required.")
        if not domain.strip():
            raise ValueError("Website domain is required.")
        if not llm_provider.strip() or not llm_model.strip():
            raise ValueError("LLM provider and model are required.")
        website_id = self._next_website_id(name or domain)
        widget_url = f"{self.agent_base_url}/widget.js"
        plugin = {
            "script_url": widget_url,
            "embed_code": (
                f'<script src="{widget_url}" data-website-id="{website_id}" '
                f'data-api-base="{self.agent_base_url}"></script>'
            ),
        }
        website = Website(
            website_id=website_id,
            name=name,
            domain=domain,
            llm=LLMConfig(provider=llm_provider, model=llm_model, api_base=llm_api_base),
            plugin=plugin,
            behavior=SalesBehavior(
                system_prompt="Guide shoppers to the right product and capture deal context.",
            ),
        )
        self._websites[website_id] = website
        self._users[website_id] = {}
        self._usage[website_id] = []
        self._deals[website_id] = []
        self._user_sequence[website_id] = 0
        return self.get_website(website_id)

    def get_website(self, website_id: str) -> dict[str, Any]:
        website = self._require_website(website_id)
        return {
            "website_id": website.website_id,
            "name": website.name,
            "domain": website.domain,
            "llm": asdict(website.llm),
            "plugin": website.plugin,
            "behavior": asdict(website.behavior),
        }

    def create_user(
        self,
        website_id: str,
        *,
        external_user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._require_website(website_id)
        next_number = self._user_sequence[website_id] + 1
        self._user_sequence[website_id] = next_number
        user = WebsiteUser(
            user_id=f"{website_id}-user-{next_number}",
            website_id=website_id,
            external_user_id=external_user_id,
            metadata=metadata or {},
        )
        self._users[website_id][user.user_id] = user
        return asdict(user)

    def set_behavior(
        self,
        website_id: str,
        *,
        system_prompt: str,
        tone: str = "consultative",
        sales_goals: list[str] | None = None,
    ) -> dict[str, Any]:
        website = self._require_website(website_id)
        if not system_prompt.strip():
            raise ValueError("Sales behavior prompt is required.")
        website.behavior = SalesBehavior(
            system_prompt=system_prompt,
            tone=tone,
            sales_goals=sales_goals or [],
        )
        return asdict(website.behavior)

    def record_usage(
        self,
        website_id: str,
        *,
        user_id: str,
        channel: str,
        messages: int,
        tokens: int,
        outcome: str | None = None,
    ) -> dict[str, Any]:
        self._require_user(website_id, user_id)
        if messages < 0 or tokens < 0:
            raise ValueError("Usage messages and tokens must be non-negative.")
        usage = UsageRecord(
            website_id=website_id,
            user_id=user_id,
            channel=channel,
            messages=messages,
            tokens=tokens,
            outcome=outcome,
        )
        self._usage[website_id].append(usage)
        return asdict(usage)

    def trace_deal(
        self,
        website_id: str,
        *,
        user_id: str,
        stage: str,
        value: float,
        currency: str = "USD",
        note: str = "",
    ) -> dict[str, Any]:
        self._require_user(website_id, user_id)
        if not stage.strip():
            raise ValueError("Deal stage is required.")
        if value < 0:
            raise ValueError("Deal value must be non-negative.")
        deal = DealRecord(
            website_id=website_id,
            user_id=user_id,
            stage=stage,
            value=float(value),
            currency=currency,
            note=note,
        )
        self._deals[website_id].append(deal)
        return asdict(deal)

    def get_summary(self, website_id: str) -> dict[str, Any]:
        website = self._require_website(website_id)
        usage = self._usage[website_id]
        deals = self._deals[website_id]
        return {
            "website": self.get_website(website_id),
            "tracked_users": len(self._users[website_id]),
            "usage_events": len(usage),
            "messages": sum(item.messages for item in usage),
            "tokens": sum(item.tokens for item in usage),
            "deals": len(deals),
            "deal_value": round(sum(item.value for item in deals), 2),
            "latest_behavior": asdict(website.behavior),
            "recent_usage": [asdict(item) for item in usage[-5:]],
            "recent_deals": [asdict(item) for item in deals[-5:]],
        }

    def _next_website_id(self, value: str) -> str:
        base = _slugify(value)
        if base not in self._websites:
            return base
        suffix = 2
        while f"{base}-{suffix}" in self._websites:
            suffix += 1
        return f"{base}-{suffix}"

    def _require_website(self, website_id: str) -> Website:
        try:
            return self._websites[website_id]
        except KeyError as exc:
            raise PlatformNotFoundError(f"Unknown website '{website_id}'.") from exc

    def _require_user(self, website_id: str, user_id: str) -> WebsiteUser:
        self._require_website(website_id)
        try:
            return self._users[website_id][user_id]
        except KeyError as exc:
            raise PlatformNotFoundError(f"Unknown user '{user_id}' for website '{website_id}'.") from exc
