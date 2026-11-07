import json

from app.config import settings
from app.main import RateLimiter


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["provider"] == "none"
    assert body["documents"] >= 10


def test_catalog(client):
    body = client.get("/api/catalog").json()
    assert len(body["clinics"]) == 6
    assert len(body["medicines"]) == 21
    names = {medicine["name"] for medicine in body["medicines"]}
    assert "Panadol Extra" in names
    assert "Augmentin 1g" in names


def test_static_frontend(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert client.get("/index.js").status_code == 200
    assert client.get("/images/medicines/panadol-extra.jpg").status_code == 200


def test_api_docs_allow_cdn(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "cdn.jsdelivr.net" in response.headers["content-security-policy"]


def test_security_headers(client):
    response = client.get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert "default-src 'self'" in response.headers["content-security-policy"]


def test_chat_price(client):
    response = client.post("/api/chat", json={"message": "how much is Panadol Extra?"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "price"
    assert "45 EGP" in body["reply"]


def test_chat_booking_entities(client):
    body = client.post("/api/chat", json={"message": "book a dentist for Ahmed tomorrow at 5 pm"}).json()
    assert body["intent"] == "book_appointment"
    assert body["entities"]["clinic"] == "Dental Care"
    assert body["entities"]["name"] == "Ahmed"


def test_chat_buy_entities(client):
    body = client.post("/api/chat", json={"message": "buy two packs of betadine for Ali"}).json()
    assert body["intent"] == "buy_medicine"
    assert body["entities"]["medicine"] == "Betadine"
    assert body["entities"]["quantity"] == 2
    assert body["entities"]["name"] == "Ali"


def test_agent_booking(client):
    response = client.post("/api/agent", json={"command": "book a dentist tomorrow at 5 pm"})
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "book_appointment"
    assert body["entities"]["clinic"] == "Dental Care"
    assert body["entities"]["time"] == "17:00"


def test_chat_medical_without_network(client):
    response = client.post("/api/chat", json={"message": "symptoms of flu"})
    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "medical_question"
    assert "not medical advice" in body["reply"].lower()


def test_chat_medical_with_source(client, monkeypatch):
    def fake_fetch(query: str):
        return {
            "title": "Diabetes",
            "summary": "Diabetes is a chronic condition that affects blood sugar.",
            "url": "https://medlineplus.gov/diabetes.html",
        }

    monkeypatch.setattr("app.main.fetch_medlineplus", fake_fetch)
    response = client.post("/api/chat", json={"message": "what is diabetes"})
    body = response.json()
    assert "chronic condition" in body["reply"]
    assert body["sources"][0]["url"].endswith("diabetes.html")
    assert "not medical advice" in body["reply"].lower()


def test_invalid_requests(client):
    assert client.post("/api/chat", json={"message": "   "}).status_code == 422
    assert client.post("/api/chat", json={"message": "x" * 501}).status_code == 422
    assert client.post("/api/chat", json={}).status_code == 422
    assert client.post("/api/agent", json={"command": ""}).status_code == 422


def test_feedback_writes_record(client):
    settings.feedback_path.unlink(missing_ok=True)
    response = client.post(
        "/api/feedback",
        json={
            "message": "how much is panadol",
            "predicted_action": "price",
            "correct_action": "price",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    line = settings.feedback_path.read_text(encoding="utf-8").strip()
    record = json.loads(line)
    assert record["predicted_action"] == "price"


def test_rate_limiter():
    limiter = RateLimiter(2)
    assert limiter.allow("1.2.3.4")
    assert limiter.allow("1.2.3.4")
    assert not limiter.allow("1.2.3.4")
    assert limiter.allow("5.6.7.8")


def test_rate_limiter_disabled():
    limiter = RateLimiter(0)
    for _ in range(50):
        assert limiter.allow("1.2.3.4")


def test_unknown_route(client):
    assert client.get("/api/does-not-exist").status_code == 404
    assert client.get("/api/chat").status_code in (404, 405)
