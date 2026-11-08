from app.retrieval import RetrievalIndex, chunk_markdown, format_context, load_index


def test_index_loads_chunks():
    index = load_index()
    assert len(index.chunks) >= 10


def test_price_search():
    index = load_index()
    results = index.search("How much is Panadol Extra?", k=3)
    assert results
    assert any("45" in str(result["text"]) for result in results)


def test_clinic_search():
    index = load_index()
    results = index.search("dentist", k=3)
    assert results
    assert "Dental Care" in " ".join(str(result["text"]) for result in results)


def test_no_result_for_gibberish():
    index = load_index()
    results = index.search("zzzz qqqq", k=3)
    assert results == []


def test_format_context():
    index = load_index()
    results = index.search("opening hours", k=2)
    context = format_context(results)
    assert "9:00-21:00" in context
    assert context


def test_empty_index_search(tmp_path):
    path = tmp_path / "empty.md"
    path.write_text("", encoding="utf-8")
    index = RetrievalIndex(path)
    assert index.search("panadol") == []


def test_chunking_starts_new_chunk_at_each_heading():
    chunks = chunk_markdown("# First\n\nOne.\n\n## Second\n\nTwo.")
    assert [chunk.title for chunk in chunks] == ["First", "Second"]
    assert chunks[0].text.startswith("# First")
    assert chunks[1].text.startswith("## Second")


def test_long_single_block_is_kept_intact():
    chunks = chunk_markdown("word " * 300, max_chars=100)
    assert len(chunks) == 1
    assert len(chunks[0].text) > 100


def test_search_honours_k_and_sorts_scores():
    index = load_index()
    results = index.search("panadol price", k=2)
    assert len(results) <= 2
    scores = [float(result["score"]) for result in results]
    assert scores == sorted(scores, reverse=True)


def test_format_context_respects_limit():
    results = [
        {"title": "One", "text": "a" * 100, "score": 0.9},
        {"title": "Two", "text": "b" * 100, "score": 0.8},
    ]
    assert format_context(results, limit=150) == "a" * 100
    assert format_context([], limit=150) == ""
