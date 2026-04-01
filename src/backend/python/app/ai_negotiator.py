from typing import List

from anthropic import Anthropic

from .config import settings
from .guardrails import estimate_tokens_from_text
from .schemas import ChatMessage


SYSTEM_PROMPT = (
    "You are AntBarter AI, an automated trade negotiator. "
    "Negotiate fair item-for-item trades, identify mismatched value and propose balancing terms, "
    "and keep responses concise and professional. "
    "Do not fabricate legal guarantees. Flag safety and verification steps."
)


def _client():
    if not settings.ANTHROPIC_API_KEY:
        return None
    return Anthropic(api_key=settings.ANTHROPIC_API_KEY)


def _anthropic_messages(messages: List[ChatMessage], latest_user_message: str, max_history: int):
    # Anthropic Messages API uses "system" separately; roles are user/assistant.
    out = []
    for m in messages[-max_history:]:
        if m.role == "system":
            continue
        out.append({"role": m.role, "content": m.content})
    out.append({"role": "user", "content": latest_user_message})
    return out


def negotiate(messages: List[ChatMessage], latest_user_message: str) -> str:
    client = _client()
    if client is None:
        return (
            "ANTHROPIC_API_KEY is not configured. Set it in backend environment variables "
            "to enable Claude negotiation."
        )

    # Guardrail: limit input size before paying for tokens
    if estimate_tokens_from_text(latest_user_message) > estimate_tokens_from_text(" " * settings.AI_MAX_INPUT_CHARS):
        latest_user_message = latest_user_message[: settings.AI_MAX_INPUT_CHARS]

    msg = client.messages.create(
        model=settings.CLAUDE_MODEL,
        system=SYSTEM_PROMPT,
        messages=_anthropic_messages(messages, latest_user_message, max_history=12),
        temperature=0.4,
        max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
    )
    text_blocks = [b for b in (msg.content or []) if getattr(b, "type", None) == "text"]
    if not text_blocks:
        return "No response generated."
    return "".join([b.text for b in text_blocks]).strip() or "No response generated."


def generate_agreement(messages: List[ChatMessage], jurisdiction: str) -> str:
    client = _client()
    if client is None:
        return (
            "ANTHROPIC_API_KEY is not configured. Set it in backend environment variables "
            "to enable Claude agreement generation."
        )

    prompt = (
        "Create a concise barter agreement draft based on this chat history. "
        "Include: parties, item/service descriptions, condition, exchange logistics, "
        "timing, dispute process, and signature blocks. "
        f"Jurisdiction: {jurisdiction}. "
        "Use plain-language legal style and title it 'Barter Trade Agreement (Draft)'."
    )

    msg = client.messages.create(
        model=settings.CLAUDE_MODEL,
        system=SYSTEM_PROMPT,
        messages=_anthropic_messages(messages, prompt, max_history=20),
        temperature=0.2,
        max_tokens=settings.AI_MAX_OUTPUT_TOKENS,
    )
    text_blocks = [b for b in (msg.content or []) if getattr(b, "type", None) == "text"]
    if not text_blocks:
        return "No agreement generated."
    return "".join([b.text for b in text_blocks]).strip() or "No agreement generated."
