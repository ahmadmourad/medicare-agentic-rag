import json
from datetime import date

import httpx
import pytest

from app import llm
from app.config import clean_api_key


@pytest.fixture(autouse=True)
def clean_model_state():
    llm.reset_model_state()
    yield
    llm.reset_model_state()


def configure(monkeypatch, **overrides):
    values = {
        "llm_provider": "groq",
        "llm_api_key": "test-key",
        "llm_model": "primary-model",
        "llm_fallback_model": "fallback-model",
        "llm_base_url": "https://example.test/v1",
        "llm_timeout": 5.0,
        "gemini_api_key": "",
        "gemini_model": "gemini-3.5-flash-lite",
        "groq_api_key": "",
        "groq_model": "openai/gpt-oss-120b",
    }
    values.update(overrides)
    for key, value in values.items():
        monkeypatch.setattr(llm.settings, key, value)


def make_response(status=200, body="", json_data=None):
    if json_data is not None:
        body = json.dumps(json_data)
    request = httpx.Request("POST", "https://example.test/v1/chat/completions")
    return httpx.Response(status_code=status, content=body.encode(), request=request)


def success(content):
    return make_response(json_data={"choices": [{"message": {"content": content}}]})


def quota_error():
    return make_response(
        status=429,
        json_data={"error": {"message": "You exceeded your current quota."}},
    )


class FakeClient:
    def __init__(self, handler):
        self.handler = handler
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return self.handler(json)


def install_client(monkeypatch, handler):
    fake = FakeClient(handler)
    monkeypatch.setattr(llm.httpx, "Client", lambda *args, **kwargs: fake)
    return fake


def test_clean_api_key_and_provider_property(monkeypatch):
    assert clean_api_key("  PASTE_YOUR_GEMINI_KEY_HERE  ") == ""
    assert clean_api_key("  real-key  ") == "real-key"

    configure(
        monkeypatch,
        llm_provider="auto",
        gemini_api_key="gem-key",
        groq_api_key="groq-key",
    )
    assert llm.settings.provider == "gemini+groq"

    configure(monkeypatch, llm_provider="auto", gemini_api_key="gem-key", groq_api_key="")
    assert llm.settings.provider == "gemini"

    configure(monkeypatch, llm_provider="auto", gemini_api_key="", groq_api_key="groq-key")
    assert llm.settings.provider == "groq"

    configure(
        monkeypatch,
        llm_provider="auto",
        gemini_api_key="PASTE_YOUR_GEMINI_KEY_HERE",
        groq_api_key="PASTE_YOUR_GROQ_KEY_HERE",
    )
    assert llm.settings.provider == "none"
    assert llm.generate("question", "context", "price") is None


def test_gemini_then_groq_then_none_chain_on_quota(monkeypatch):
    configure(
        monkeypatch,
        llm_provider="auto",
        gemini_api_key="gem-key",
        groq_api_key="groq-key",
    )

    state = {"gemini_quota": False, "groq_quota": False}

    def handler(payload):
        model = payload["model"]
        if model == "gemini-3.5-flash-lite":
            if state["gemini_quota"]:
                return quota_error()
            return success("gemini answer")
        if state["groq_quota"]:
            return quota_error()
        return success("groq answer")

    fake = install_client(monkeypatch, handler)

    # 1. Starts with Gemini when healthy
    assert llm.generate("question", "context", "price") == "gemini answer"
    assert [c["json"]["model"] for c in fake.calls] == ["gemini-3.5-flash-lite"]

    # 2. When Gemini hits daily quota, automatically falls back to Groq and skips Gemini next time
    state["gemini_quota"] = True
    assert llm.generate("question", "context", "price") == "groq answer"
    assert [c["json"]["model"] for c in fake.calls] == [
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash-lite",
        "openai/gpt-oss-120b",
    ]

    assert llm.generate("question", "context", "price") == "groq answer"
    assert [c["json"]["model"] for c in fake.calls] == [
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash-lite",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-120b",
    ]

    # 3. When Groq also hits quota, returns None so caller uses local fallback
    state["groq_quota"] = True
    assert llm.generate("question", "context", "price") is None


def test_gemini_error_falls_back_to_groq_then_none(monkeypatch):
    configure(
        monkeypatch,
        llm_provider="auto",
        gemini_api_key="gem-key",
        groq_api_key="groq-key",
    )

    state = {"groq_fails": False}

    def handler(payload):
        if payload["model"] == "gemini-3.5-flash-lite":
            return make_response(status=500, body="gemini server error")
        if state["groq_fails"]:
            return make_response(status=503, body="groq unavailable")
        return success("groq backup answer")

    fake = install_client(monkeypatch, handler)

    assert llm.generate("question", "context", "price") == "groq backup answer"
    assert [c["json"]["model"] for c in fake.calls] == [
        "gemini-3.5-flash-lite",
        "openai/gpt-oss-120b",
    ]

    state["groq_fails"] = True
    assert llm.generate("question", "context", "price") is None


def test_generate_is_disabled_without_provider(monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_provider", "none")
    assert llm.generate("question", "context", "price") is None


def test_generate_requires_api_key_for_known_provider(monkeypatch):
    configure(monkeypatch, llm_api_key="")

    def fail(_):
        raise AssertionError("the client should not be called without an API key")

    install_client(monkeypatch, fail)
    assert llm.generate("question", "context", "price") is None


def test_generate_unknown_provider_without_base_url(monkeypatch):
    configure(monkeypatch, llm_provider="other", llm_base_url="", llm_model="model")
    assert llm.generate("question", "context", "price") is None


def test_generate_success(monkeypatch):
    configure(monkeypatch)
    fake = install_client(monkeypatch, lambda payload: success(f"answer from {payload['model']}"))

    result = llm.generate("question", "context", "price")

    assert result == "answer from primary-model"
    assert fake.calls[0]["url"] == "https://example.test/v1/chat/completions"
    assert fake.calls[0]["json"]["model"] == "primary-model"
    assert fake.calls[0]["headers"]["Authorization"] == "Bearer test-key"


def test_generate_custom_provider_without_key(monkeypatch):
    configure(
        monkeypatch,
        llm_provider="custom",
        llm_api_key="",
        llm_model="local-model",
        llm_fallback_model="",
    )
    install_client(monkeypatch, lambda payload: success("local answer"))

    assert llm.generate("question", "context", "price") == "local answer"


def test_generate_quota_falls_back_and_skips_exhausted_model(monkeypatch):
    configure(monkeypatch)

    def handler(payload):
        if payload["model"] == "primary-model":
            return quota_error()
        return success(f"answer from {payload['model']}")

    fake = install_client(monkeypatch, handler)

    assert llm.generate("question", "context", "price") == "answer from fallback-model"
    assert [call["json"]["model"] for call in fake.calls] == ["primary-model", "fallback-model"]

    assert llm.generate("question", "context", "price") == "answer from fallback-model"
    assert [call["json"]["model"] for call in fake.calls] == [
        "primary-model",
        "fallback-model",
        "fallback-model",
    ]


def test_generate_quota_without_fallback_returns_none(monkeypatch):
    configure(monkeypatch, llm_fallback_model="")
    fake = install_client(monkeypatch, lambda payload: quota_error())

    assert llm.generate("question", "context", "price") is None
    assert len(fake.calls) == 1

    assert llm.generate("question", "context", "price") is None
    assert len(fake.calls) == 1


def test_non_quota_error_does_not_try_same_provider_fallback(monkeypatch):
    configure(monkeypatch)
    fake = install_client(monkeypatch, lambda payload: make_response(status=500, body="server error"))

    assert llm.generate("question", "context", "price") is None
    assert len(fake.calls) == 1
    assert fake.calls[0]["json"]["model"] == "primary-model"


def test_per_minute_rate_limit_is_not_treated_as_daily_quota(monkeypatch):
    configure(monkeypatch, llm_fallback_model="")
    fake = install_client(
        monkeypatch,
        lambda payload: make_response(status=429, body="Rate limit exceeded, retry in one second."),
    )

    assert llm.generate("question", "context", "price") is None
    assert llm.generate("question", "context", "price") is None
    assert len(fake.calls) == 2


def test_generate_timeout_returns_none(monkeypatch):
    configure(monkeypatch)

    def timeout(_):
        raise httpx.TimeoutException("timed out")

    install_client(monkeypatch, timeout)
    assert llm.generate("question", "context", "price") is None


def test_generate_invalid_json_returns_none(monkeypatch):
    configure(monkeypatch)
    install_client(monkeypatch, lambda payload: make_response(body="not json"))
    assert llm.generate("question", "context", "price") is None


def test_generate_empty_content_returns_none(monkeypatch):
    configure(monkeypatch)
    install_client(monkeypatch, lambda payload: success("   "))
    assert llm.generate("question", "context", "price") is None


def test_model_exhaustion_resets_on_new_day(monkeypatch):
    class FakeDate:
        current = date(2026, 1, 1)

        @classmethod
        def today(cls):
            return cls.current

    monkeypatch.setattr(llm, "date", FakeDate)
    configure(monkeypatch, llm_fallback_model="")
    fake = install_client(monkeypatch, lambda payload: quota_error())

    assert llm.generate("question", "context", "price") is None
    assert len(fake.calls) == 1

    FakeDate.current = date(2026, 1, 2)
    assert llm.generate("question", "context", "price") is None
    assert len(fake.calls) == 2


def test_quota_detection_handles_unreadable_body():
    class BrokenResponse:
        status_code = 429

        @property
        def text(self):
            raise RuntimeError("body is unavailable")

    assert llm._is_daily_quota_error(BrokenResponse()) is False


def test_long_fallback_is_truncated():
    results = [{"title": "Long", "text": "## Heading\n\n" + "word " * 300, "score": 0.5}]
    answer = llm.fallback_answer("long", results, None, False)
    assert answer.endswith("...")
    assert len(answer) <= 1003


def test_medical_fallback_has_no_markdown():
    answer = llm.fallback_answer(
        "what is diabetes",
        [],
        {"title": "Diabetes", "summary": "A chronic condition.", "url": "https://example.test"},
        True,
    )
    assert answer.startswith("Diabetes")
    assert "**" not in answer
    assert llm.DISCLAIMER in answer


def test_retrieval_fallback_strips_heading():
    results = [{"title": "Price", "text": "## Panadol Extra\n\nIt costs 45 EGP.", "score": 0.5}]
    answer = llm.fallback_answer("panadol price", results, None, False)
    assert answer.startswith("Panadol Extra")
    assert "##" not in answer


def test_empty_fallback_is_helpful():
    answer = llm.fallback_answer("weather", [], None, False)
    assert "could not find" in answer.lower()
    assert "clinics" in answer.lower()


def test_medical_text_cleanup():
    from app.medical_info import _strip_html

    assert _strip_html("<p>Diabetes is a condition .</p>") == "Diabetes is a condition."
