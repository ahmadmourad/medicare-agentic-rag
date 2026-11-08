from __future__ import annotations

import logging
import re
import threading
from datetime import date
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
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.5-flash-lite"),
    "groq": ("https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
}

QUOTA_MARKERS = (
    "quota",
    "resource_exhausted",
    "insufficient_quota",
    "requests per day",
    "per day",
    "daily limit",
    "rpd",
)

ModelTarget = tuple[str, str, str, str]

_exhausted_lock = threading.Lock()
_exhausted_models: dict[tuple[str, str, str], date] = {}


class QuotaExceeded(Exception):
    """Raised when a provider reports that a model's daily quota is exhausted."""


class ProviderFailure(Exception):
    """Raised when a provider request fails for a reason other than daily quota."""


def reset_model_state() -> None:
    """Clear the in-memory daily quota state. Intended for tests and service restarts."""
    with _exhausted_lock:
        _exhausted_models.clear()


def _model_key(provider: str, base_url: str, model: str) -> tuple[str, str, str]:
    return provider, base_url, model


def _is_exhausted(key: tuple[str, str, str]) -> bool:
    today = date.today()
    with _exhausted_lock:
        exhausted_on = _exhausted_models.get(key)
        if exhausted_on == today:
            return True
        if exhausted_on is not None:
            _exhausted_models.pop(key, None)
        return False


def _mark_exhausted(key: tuple[str, str, str]) -> None:
    with _exhausted_lock:
        _exhausted_models[key] = date.today()


def _resolve_targets() -> list[ModelTarget]:
    provider = settings.provider
    if provider == "none":
        return []

    base_url, default_model = PROVIDER_DEFAULTS.get(provider, ("", ""))
    base_url = (settings.llm_base_url or base_url).rstrip("/")
    primary_model = settings.llm_model.strip() or default_model

    if not base_url or not primary_model:
        return []

    if provider in PROVIDER_DEFAULTS and not settings.llm_api_key.strip():
        logger.warning("%s provider selected but LLM_API_KEY is empty", provider)
        return []

    models: list[str] = []
    for model in (primary_model, settings.llm_fallback_model.strip()):
        if model and model not in models:
            models.append(model)

    return [(provider, base_url, model, settings.llm_api_key) for model in models]


def _is_daily_quota_error(response: httpx.Response) -> bool:
    if response.status_code != 429:
        return False
    try:
        body = response.text.lower()
    except Exception:
        return False
    return any(marker in body for marker in QUOTA_MARKERS)


def _request_model(target: ModelTarget, question: str, context: str, intent: str) -> str:
    provider, base_url, model, api_key = target
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
    except httpx.HTTPError as exc:
        raise ProviderFailure(str(exc)) from exc

    if _is_daily_quota_error(response):
        raise QuotaExceeded(model)

    try:
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        content = data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as exc:
        raise ProviderFailure(f"HTTP {response.status_code}") from exc
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderFailure(str(exc)) from exc

    content = str(content).strip()
    if not content:
        raise ProviderFailure("empty response")
    return content


def generate(question: str, context: str, intent: str) -> str | None:
    """Call an OpenAI-compatible chat endpoint. Returns None when no model can answer."""
    targets = _resolve_targets()
    if not targets:
        return None

    for target in targets:
        provider, base_url, model, _ = target
        key = _model_key(provider, base_url, model)

        if _is_exhausted(key):
            logger.info("%s model %s is already exhausted for today; skipping", provider, model)
            continue

        try:
            return _request_model(target, question, context, intent)
        except QuotaExceeded:
            _mark_exhausted(key)
            logger.warning(
                "%s model %s reported that its daily quota is exhausted; trying the next model",
                provider,
                model,
            )
            continue
        except ProviderFailure as exc:
            logger.warning("%s generation failed on model %s: %s", provider, model, exc)
            return None

    return None


def fallback_answer(
    question: str,
    results: list[dict[str, object]],
    medical: dict[str, str | None] | None,
    needs_disclaimer: bool,
) -> str:
    if medical and medical.get("summary"):
        answer = "\n\n".join(
            [str(medical.get("title") or question), str(medical["summary"])]
        )
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
