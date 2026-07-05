from __future__ import annotations

from dataclasses import asdict

from salesperson.auth.keys import resolve_website_id
from salesperson.errors import AuthError, PlatformNotFoundError
from salesperson.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    UsageRecord,
    WebsiteUser,
)
from salesperson.plans import PLAN_LABELS, allows_chat_channel, has_feature, plan_features, require_feature
from salesperson.providers.base import LLMProvider
from salesperson.storage.base import PlatformRepository

_WIDGET_VISITOR_PREFIX = "visitor-"


def _is_widget_visitor(user_id: str, channel: str) -> bool:
    return channel == "website-widget" and user_id.startswith(_WIDGET_VISITOR_PREFIX)


class ChatGateway:
    """Public API forward layer: auth → behavior → LLM → auto-meter."""

    def __init__(
        self,
        repository: PlatformRepository,
        provider: LLMProvider,
    ) -> None:
        self._repository = repository
        self._provider = provider
        self._sequence = 0

    def authenticate(self, api_key: str | None) -> str:
        if not api_key or not api_key.strip():
            raise AuthError("Missing API key.")
        website_id = resolve_website_id(self._repository.list_api_key_hashes(), api_key.strip())
        if website_id is None:
            raise AuthError("Invalid API key.")
        return website_id

    def _ensure_user(self, website_id: str, user_id: str) -> None:
        try:
            self._repository.get_user(website_id, user_id)
        except PlatformNotFoundError:
            self._repository.save_user(
                WebsiteUser(
                    user_id=user_id,
                    website_id=website_id,
                    external_user_id=user_id,
                    metadata={"source": "widget"},
                )
            )

    def forward_chat(
        self,
        *,
        api_key: str | None,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        website_id = self.authenticate(api_key)
        website = self._repository.get_website(website_id)
        if not allows_chat_channel(website.plan, request.channel):
            require_feature(website.plan, "public_chat")
        user_id = request.user_id or f"{website_id}-anonymous"
        if request.user_id:
            if _is_widget_visitor(request.user_id, request.channel):
                self._ensure_user(website_id, request.user_id)
            else:
                try:
                    self._repository.get_user(website_id, request.user_id)
                except PlatformNotFoundError as exc:
                    raise AuthError("Unknown user for this website.") from exc

        assistant_message, usage = self._provider.complete(
            llm=website.llm,
            behavior=website.behavior,
            messages=request.messages,
        )

        self._repository.append_usage(
            UsageRecord(
                website_id=website_id,
                user_id=user_id,
                channel=request.channel,
                messages=len(request.messages) + 1,
                tokens=usage.total_tokens,
                outcome="chat-completion",
            )
        )

        self._sequence += 1
        return ChatCompletionResponse(
            id=f"chatcmpl-demo-{self._sequence}",
            message=assistant_message,
            usage=usage,
            website_id=website_id,
        )

    def usage_summary(self, *, api_key: str | None) -> dict:
        website_id = self.authenticate(api_key)
        website = self._repository.get_website(website_id)
        require_feature(website.plan, "usage_api")
        return self._usage_metrics(website_id, website.domain)

    def _usage_metrics(self, website_id: str, domain: str) -> dict:
        usage = self._repository.list_usage(website_id)
        deals = self._repository.list_deals(website_id)
        return {
            "website_id": website_id,
            "domain": domain,
            "tracked_users": self._repository.count_users(website_id),
            "usage_events": len(usage),
            "messages": sum(item.messages for item in usage),
            "tokens": sum(item.tokens for item in usage),
            "deals": len(deals),
            "deal_value": round(sum(item.value for item in deals), 2),
        }

    def owner_dashboard(self, *, api_key: str | None) -> dict:
        website_id = self.authenticate(api_key)
        website = self._repository.get_website(website_id)
        usage = self._repository.list_usage(website_id)
        deals = self._repository.list_deals(website_id)
        dashboard: dict = {
            "website_id": website.website_id,
            "name": website.name,
            "domain": website.domain,
            "plan": website.plan,
            "plan_label": PLAN_LABELS[website.plan],
            "features": sorted(plan_features(website.plan)),
            "behavior": asdict(website.behavior),
            "embed": {
                "script_url": website.plugin.get("script_url"),
                "note": "API key is shown once at registration. Use your saved key below.",
            },
            "upgrade_url": "https://yanchao1999.github.io/salesperson/#plans",
        }
        if has_feature(website.plan, "usage_api"):
            dashboard["metrics"] = self._usage_metrics(website.website_id, website.domain)
            dashboard["recent_usage"] = [asdict(item) for item in usage[-5:]]
            dashboard["recent_deals"] = [asdict(item) for item in deals[-5:]]
        else:
            dashboard["metrics"] = {
                "available": False,
                "message": "Upgrade to Basic API to view usage metrics and deal totals.",
            }
            dashboard["recent_usage"] = []
            dashboard["recent_deals"] = []
        return dashboard

    @staticmethod
    def parse_messages(raw_messages: list[dict]) -> list[ChatMessage]:
        messages: list[ChatMessage] = []
        for item in raw_messages:
            role = str(item["role"])
            content = str(item["content"])
            if not content.strip():
                raise ValueError("Message content cannot be empty.")
            messages.append(ChatMessage(role=role, content=content))
        if not messages:
            raise ValueError("At least one message is required.")
        return messages

    @staticmethod
    def completion_to_dict(response: ChatCompletionResponse) -> dict:
        return {
            "id": response.id,
            "message": asdict(response.message),
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            "website_id": response.website_id,
        }
