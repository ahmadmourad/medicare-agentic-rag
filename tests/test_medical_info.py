import httpx
import pytest

from app import medical_info


def make_response(content: bytes, status: int = 200):
    request = httpx.Request("GET", medical_info.NLM_SEARCH_URL)
    return httpx.Response(status_code=status, content=content, request=request)


class FakeClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.url = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def get(self, url, params=None):
        self.url = url
        self.params = params
        if self.error:
            raise self.error
        return self.response


def install_client(monkeypatch, response=None, error=None):
    fake = FakeClient(response=response, error=error)
    monkeypatch.setattr(medical_info.httpx, "Client", lambda *args, **kwargs: fake)
    return fake


def test_lookup_disabled_returns_none(monkeypatch):
    monkeypatch.setattr(medical_info.settings, "medlineplus_enabled", False)
    install_client(monkeypatch, error=AssertionError("client should not be called"))
    assert medical_info.fetch_medlineplus("diabetes") is None


def test_lookup_parses_title_summary_and_url(monkeypatch):
    monkeypatch.setattr(medical_info.settings, "medlineplus_enabled", True)
    xml = b"""
    <root>
      <document url="https://medlineplus.gov/diabetes.html">
        <content name="title">Diabetes</content>
        <content name="FullSummary"><p>Diabetes is a &amp; condition.</p></content>
      </document>
    </root>
    """
    fake = install_client(monkeypatch, make_response(xml))

    result = medical_info.fetch_medlineplus("What is diabetes?")

    assert result == {
        "title": "Diabetes",
        "summary": "Diabetes is a & condition.",
        "url": "https://medlineplus.gov/diabetes.html",
    }
    assert fake.url == medical_info.NLM_SEARCH_URL
    assert fake.params == {"db": "healthTopics", "term": "diabetes", "retMax": "3"}


def test_lookup_uses_snippet_when_summary_missing(monkeypatch):
    monkeypatch.setattr(medical_info.settings, "medlineplus_enabled", True)
    xml = b"""
    <root>
      <document url="https://medlineplus.gov/flu.html">
        <content name="title">Flu</content>
        <content name="snippet">Flu is a respiratory illness.</content>
      </document>
    </root>
    """
    install_client(monkeypatch, make_response(xml))

    result = medical_info.fetch_medlineplus("flu")

    assert result["summary"] == "Flu is a respiratory illness."
    assert result["url"].endswith("flu.html")


def test_lookup_skips_documents_without_summary(monkeypatch):
    monkeypatch.setattr(medical_info.settings, "medlineplus_enabled", True)
    xml = b"""
    <root>
      <document url="https://example.test/empty.html">
        <content name="title">Empty</content>
      </document>
      <document url="https://example.test/useful.html">
        <content name="title">Useful</content>
        <content name="snippet">Useful summary.</content>
      </document>
    </root>
    """
    install_client(monkeypatch, make_response(xml))

    result = medical_info.fetch_medlineplus("useful")

    assert result["title"] == "Useful"
    assert result["summary"] == "Useful summary."


def test_lookup_truncates_long_summary(monkeypatch):
    monkeypatch.setattr(medical_info.settings, "medlineplus_enabled", True)
    long_summary = "word " * 400
    xml = f"""
    <root>
      <document url="https://example.test/long.html">
        <content name="title">Long</content>
        <content name="snippet">{long_summary}</content>
      </document>
    </root>
    """.encode()
    install_client(monkeypatch, make_response(xml))

    result = medical_info.fetch_medlineplus("long")

    assert result["summary"].endswith("...")
    assert len(result["summary"]) <= 1403


def test_lookup_returns_none_without_documents(monkeypatch):
    monkeypatch.setattr(medical_info.settings, "medlineplus_enabled", True)
    install_client(monkeypatch, make_response(b"<root></root>"))
    assert medical_info.fetch_medlineplus("nothing") is None


def test_lookup_handles_http_error(monkeypatch):
    monkeypatch.setattr(medical_info.settings, "medlineplus_enabled", True)
    install_client(monkeypatch, error=httpx.ConnectError("connection failed"))
    assert medical_info.fetch_medlineplus("diabetes") is None


def test_lookup_handles_malformed_xml(monkeypatch):
    monkeypatch.setattr(medical_info.settings, "medlineplus_enabled", True)
    install_client(monkeypatch, make_response(b"<root><document"))
    assert medical_info.fetch_medlineplus("diabetes") is None


def test_lookup_rejects_oversized_response(monkeypatch):
    monkeypatch.setattr(medical_info.settings, "medlineplus_enabled", True)
    monkeypatch.setattr(medical_info, "MAX_RESPONSE_BYTES", 10)
    install_client(monkeypatch, make_response(b"<root>this is too large</root>"))
    assert medical_info.fetch_medlineplus("diabetes") is None


def test_clean_query_removes_stopwords():
    assert medical_info._clean_query("What is the price of Panadol?") == "panadol"


def test_clean_query_falls_back_when_everything_is_a_stopword():
    assert medical_info._clean_query("the a an") == "the a an"
