from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass(frozen=True)
class Chunk:
    index: int
    title: str
    text: str


def chunk_markdown(text: str, max_chars: int = 600) -> list[Chunk]:
    """Split a markdown document into overlapping-free, heading-aware chunks."""
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text) if block.strip()]
    chunks: list[Chunk] = []
    buffer: list[str] = []
    buffer_title = "Overview"
    current_title = "Overview"

    def flush() -> None:
        if buffer:
            chunks.append(Chunk(len(chunks), buffer_title, "\n\n".join(buffer)))
            buffer.clear()

    for block in blocks:
        heading = re.match(r"^#{1,3}\s+(.+)", block)
        if heading:
            flush()
            current_title = heading.group(1).strip()
            buffer_title = current_title
            buffer.append(block)
            continue

        projected = sum(len(item) + 2 for item in buffer) + len(block)
        if buffer and projected > max_chars:
            flush()
            buffer_title = current_title
        buffer.append(block)

    flush()
    return chunks


class RetrievalIndex:
    """Small lexical RAG index that stays fast, offline and dependency-light."""

    def __init__(self, docs_path: Path | str):
        self.docs_path = Path(docs_path)
        text = self.docs_path.read_text(encoding="utf-8")
        self.chunks = chunk_markdown(text)
        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        if self.chunks:
            self._matrix = self._vectorizer.fit_transform(chunk.text for chunk in self.chunks)
        else:
            self._matrix = None

    def search(self, query: str, k: int = 3) -> list[dict[str, object]]:
        if not self.chunks or self._matrix is None:
            return []
        query_vector = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self._matrix).ravel()
        order = np.argsort(scores)[::-1][:k]
        results = []
        for position in order:
            score = float(scores[position])
            if score <= 0:
                continue
            chunk = self.chunks[int(position)]
            results.append(
                {
                    "title": chunk.title,
                    "text": chunk.text,
                    "score": round(score, 4),
                }
            )
        return results


@lru_cache(maxsize=4)
def load_index(docs_path: str) -> RetrievalIndex:
    return RetrievalIndex(docs_path)


def format_context(results: list[dict[str, object]], limit: int = 2200) -> str:
    parts: list[str] = []
    used = 0
    for result in results:
        text = str(result["text"]).strip()
        if used + len(text) > limit:
            break
        parts.append(text)
        used += len(text)
    return "\n\n---\n\n".join(parts)
