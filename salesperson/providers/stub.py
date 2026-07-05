from __future__ import annotations

from salesperson.models import ChatMessage, LLMConfig, SalesBehavior, TokenUsage


class StubLLMProvider:
    """Local dev provider — echoes the last user message with sales tone."""

    def complete(
        self,
        *,
        llm: LLMConfig,
        behavior: SalesBehavior,
        messages: list[ChatMessage],
    ) -> tuple[ChatMessage, TokenUsage]:
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        prompt_tokens = sum(len(m.content.split()) for m in messages) + len(behavior.system_prompt.split())
        reply = (
            f"[{behavior.tone}/{llm.provider}:{llm.model}] "
            f"I can help with that. You asked: {last_user or '…'}"
        )
        completion_tokens = len(reply.split())
        return (
            ChatMessage(role="assistant", content=reply),
            TokenUsage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens),
        )
