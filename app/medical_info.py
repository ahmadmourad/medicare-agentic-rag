from __future__ import annotations

import html
import logging
import re
import xml.etree.ElementTree as ET

import httpx

from .config import settings

logger = logging.getLogger(__name__)

NLM_SEARCH_URL = "https://wsearch.nlm.nih.gov/ws/query"
MAX_RESPONSE_BYTES = 2_000_000

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "what", "which", "who",
    "how", "why", "when", "where", "do", "does", "did", "can", "could",
    "i", "you", "me", "my", "we", "our", "please", "tell", "about", "of",
    "in", "on", "for", "to", "and", "or", "with", "much", "many", "cost",
    "price", "buy", "book", "want", "need", "give", "show",
}


def _clean_query(query: str) -> str:
    lowered = re.sub(r"[^\w\s]", " ", query.lower())
    words = [word for word in lowered.split() if len(word) > 1 and word not in STOPWORDS]
    return " ".join(words) or query.strip()


def _strip_html(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def fetch_medlineplus(query: str, timeout: float | None = None) -> dict[str, str | None] | None:
    """Return a short patient-friendly summary, or None when unavailable."""
    if not settings.medlineplus_enabled:
        return None

    params = {"db": "healthTopics", "term": _clean_query(query), "retMax": "3"}
    try:
        with httpx.Client(
            timeout=timeout or settings.medlineplus_timeout,
            follow_redirects=True,
            headers={"User-Agent": "MediCareAssistant/1.0"},
        ) as client:
            response = client.get(NLM_SEARCH_URL, params=params)
            response.raise_for_status()
            if len(response.content) > MAX_RESPONSE_BYTES:
                return None
            root = ET.fromstring(response.content)
    except (httpx.HTTPError, ET.ParseError, ValueError) as exc:
        logger.info("MedlinePlus lookup failed: %s", exc)
        return None

    for document in root.iter("document"):
        title: str | None = None
        summary: str | None = None
        for content in document.findall("content"):
            name = content.get("name")
            raw = content.text or ""
            if name == "title" and not title:
                title = _strip_html(raw)
            elif name in {"FullSummary", "snippet"} and not summary:
                summary = _strip_html(raw)

        if not summary:
            continue
        if len(summary) > 1400:
            summary = summary[:1400].rsplit(" ", 1)[0] + "..."
        return {
            "title": title or _clean_query(query).title(),
            "summary": summary,
            "url": document.get("url"),
        }

    return None
