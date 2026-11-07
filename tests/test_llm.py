from app import llm


def test_generate_is_disabled_without_provider(monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_provider", "none")
    assert llm.generate("question", "context", "price") is None


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
