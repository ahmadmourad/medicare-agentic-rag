from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from .config import settings

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "This is general health information, not medical advice. "
    "Please consult a doctor or pharmacist before making any decision."
)

SYSTEM_PROMPT = (
    "You are the MediCare assistant for a clinic and pharmacy website. "
    "Answer only from the provided context. Be concise and friendly. "
    "Never diagnose, prescribe, or give personalised treatment advice. "
    "If the context does not contain the answer, say so and suggest asking a healthcare professional. "
    "For emergencies, tell the user to call local emergency services immediately. "
    "When you use a source, mention it in plain text."
)

PROVIDER_DEFAULTS: dict[str, tuple[str, str]] = {
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash"),
    "groq": ("https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
    "ollama": ("http://localhost:11434/v1", "llama3.2"),
}


def _resolve_provider() -> tuple[str, str, str, str] | None:
    provider = settings.provider
    if provider == "none":
        return None
    base_url, default_model = PROVIDER_DEFAULTS.get(provider, ("", ""))
    base_url = settings.llm_base_url or base_url
    model = settings.llm_model or default_model
    if not base_url or not model:
        return None
    return provider, base_url.rstrip("/"), model, settings.llm_api_key


def generate(question: str, context: str, intent: str) -> str | None:
    """Call an OpenAI-compatible chat endpoint. Returns None on any failure."""
    resolved = _resolve_provider()
    if resolved is None:
        return None

    provider, base_url, model, api_key = resolved
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Context:\n{context or 'No relevant context found.'}\n\n"
                    f"Question: {question}\n\n"
                    f"Detected intent: {intent}"
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 400,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        with httpx.Client(timeout=settings.llm_timeout) as client:
            response = client.post(f"{base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        content = data["choices"][0]["message"]["content"]
        content = str(content).strip()
        return content or None
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
        logger.warning("%s generation failed: %s", provider, exc)
        return None


def fallback_answer(
    question: str,
    results: list[dict[str, object]],
    medical: dict[str, str | None] | None,
    needs_disclaimer: bool,
) -> str:
    if medical and medical.get("summary"):
        parts = [f"**{medical.get('title') or question}**", str(medical["summary"])]
        if medical.get("url"):
            parts.append(f"Source: {medical['url']}")
        answer = "\n\n".join(parts)
    elif results:
        text = str(results[0]["text"]).strip()
        text = re.sub(r"^#{1,3}\s*", "", text)
        if len(text) > 1000:
            text = text[:1000].rsplit(" ", 1)[0] + "..."
        answer = text
    else:
        answer = (
            "I could not find a reliable answer for that. "
            "You can ask about our clinics, opening hours, medicine prices, "
            "or a general health topic, and I will do my best to help."
        )

    if needs_disclaimer:
        answer = f"{answer}\n\n{DISCLAIMER}"
    return answer
