from __future__ import annotations

from dataclasses import asdict
import re
from typing import Any

from .auth.keys import generate_api_key, hash_api_key
from .errors import PlatformNotFoundError
from .gateway.service import ChatGateway
from .models import DealRecord, SalesBehavior, LLMConfig, UsageRecord, Website, WebsiteUser
from .plans import normalize_plan, require_feature
from .providers.factory import create_provider
from .storage.base import PlatformRepository
from .storage.factory import create_repository


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "website"


class SalespersonPlatform:
    """Tenant admin service — register websites, behavior, deals, summaries."""

    def __init__(
        self,
        agent_base_url: str = "https://agent.example.com",
        repository: PlatformRepository | None = None,
        gateway: ChatGateway | None = None,
    ) -> None:
        self.agent_base_url = agent_base_url.rstrip("/")
        self._repository = repository or create_repository()
        self.gateway = gateway or ChatGateway(self._repository, create_provider())

    def create_website(
        self,
        *,
        name: str,
        domain: str,
        llm_provider: str,
        llm_model: str,
        llm_api_base: str | None = None,
        plan: str = "free",
    ) -> dict[str, Any]:
        if not name.strip():
            raise ValueError("Website name is required.")
        if not domain.strip():
            raise ValueError("Website domain is required.")
        if not llm_provider.strip() or not llm_model.strip():
            raise ValueError("LLM provider and model are required.")
        normalized_plan = normalize_plan(plan)
        if llm_api_base:
            require_feature(normalized_plan, "byok")

        website_id = self._repository.next_website_id(_slugify(name or domain))
        api_key = generate_api_key()
        widget_url = f"{self.agent_base_url}/widget.js"
        plugin = {
            "script_url": widget_url,
            "embed_code": (
                f'<script src="{widget_url}" data-api-key="{api_key}" '
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
            api_key_hash=hash_api_key(api_key),
            plan=normalized_plan,
        )
        self._repository.save_website(website)
        payload = self.get_website(website_id)
        payload["api_key"] = api_key
        return payload

    def get_website(self, website_id: str) -> dict[str, Any]:
        website = self._repository.get_website(website_id)
        return {
            "website_id": website.website_id,
            "name": website.name,
            "domain": website.domain,
            "llm": asdict(website.llm),
            "plugin": website.plugin,
            "behavior": asdict(website.behavior),
            "plan": website.plan,
        }

    def set_plan(self, website_id: str, *, plan: str) -> dict[str, Any]:
        website = self._repository.get_website(website_id)
        website.plan = normalize_plan(plan)
        self._repository.save_website(website)
        return self.get_website(website_id)

    def create_user(
        self,
        website_id: str,
        *,
        external_user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        next_number = self._repository.next_user_number(website_id)
        user = WebsiteUser(
            user_id=f"{website_id}-user-{next_number}",
            website_id=website_id,
            external_user_id=external_user_id,
            metadata=metadata or {},
        )
        self._repository.save_user(user)
        return asdict(user)

    def set_behavior(
        self,
        website_id: str,
        *,
        system_prompt: str,
        tone: str = "consultative",
        sales_goals: list[str] | None = None,
    ) -> dict[str, Any]:
        if not system_prompt.strip():
            raise ValueError("Sales behavior prompt is required.")
        website = self._repository.get_website(website_id)
        require_feature(website.plan, "custom_behavior")
        behavior = SalesBehavior(
            system_prompt=system_prompt,
            tone=tone,
            sales_goals=sales_goals or [],
        )
        return asdict(self._repository.update_behavior(website_id, behavior))

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
        self._repository.get_user(website_id, user_id)
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
        return asdict(self._repository.append_usage(usage))

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
        self._repository.get_user(website_id, user_id)
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
        return asdict(self._repository.append_deal(deal))

    def get_summary(self, website_id: str) -> dict[str, Any]:
        website = self._repository.get_website(website_id)
        usage = self._repository.list_usage(website_id)
        deals = self._repository.list_deals(website_id)
        return {
            "website": self.get_website(website_id),
            "tracked_users": self._repository.count_users(website_id),
            "usage_events": len(usage),
            "messages": sum(item.messages for item in usage),
            "tokens": sum(item.tokens for item in usage),
            "deals": len(deals),
            "deal_value": round(sum(item.value for item in deals), 2),
            "latest_behavior": asdict(website.behavior),
            "recent_usage": [asdict(item) for item in usage[-5:]],
            "recent_deals": [asdict(item) for item in deals[-5:]],
        }
