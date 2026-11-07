from app.retrieval import RetrievalIndex, format_context, load_index


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
