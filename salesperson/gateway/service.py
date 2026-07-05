from __future__ import annotations

from dataclasses import asdict

from salesperson.auth.keys import resolve_website_id
from salesperson.errors import AuthError, PlatformNotFoundError
from salesperson.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    UsageRecord,
)
from salesperson.providers.base import LLMProvider
from salesperson.storage.base import PlatformRepository


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

    def forward_chat(
        self,
        *,
        api_key: str | None,
        request: ChatCompletionRequest,
    ) -> ChatCompletionResponse:
        website_id = self.authenticate(api_key)
        website = self._repository.get_website(website_id)
        user_id = request.user_id or f"{website_id}-anonymous"

        if request.user_id:
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
            id=f"chatcmpl-stub-{self._sequence}",
            message=assistant_message,
            usage=usage,
            website_id=website_id,
        )

    def usage_summary(self, *, api_key: str | None) -> dict:
        website_id = self.authenticate(api_key)
        usage = self._repository.list_usage(website_id)
        deals = self._repository.list_deals(website_id)
        website = self._repository.get_website(website_id)
        return {
            "website_id": website_id,
            "domain": website.domain,
            "tracked_users": self._repository.count_users(website_id),
            "usage_events": len(usage),
            "messages": sum(item.messages for item in usage),
            "tokens": sum(item.tokens for item in usage),
            "deals": len(deals),
            "deal_value": round(sum(item.value for item in deals), 2),
        }

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
