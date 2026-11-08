from __future__ import annotations

import json
import logging
import os
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import agent, llm
from .catalog import CLINICS, MEDICINES
from .config import settings
from .medical_info import fetch_medlineplus
from .retrieval import RetrievalIndex, format_context, load_index
from .schemas import (
    AgentRequest,
    AgentResponse,
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    HealthResponse,
    Source,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DOCUMENTS = 0


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float = 60.0):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        if self.limit <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            if len(self._hits) > 4096:
                stale = [
                    item
                    for item, records in self._hits.items()
                    if not records or now - records[-1] > self.window
                ]
                for item in stale:
                    del self._hits[item]
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            return True


RATE_LIMITED_PATHS = frozenset({"/api/chat", "/api/agent", "/api/feedback"})
limiter = RateLimiter(settings.rate_limit_per_minute)
feedback_lock = threading.Lock()


@asynccontextmanager
async def lifespan(_: FastAPI):
    global DOCUMENTS
    index = load_index(str(settings.docs_path))
    DOCUMENTS = len(index.chunks)
    logger.info("Loaded %d knowledge chunks", DOCUMENTS)
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)


def get_index() -> RetrievalIndex:
    global DOCUMENTS
    index = load_index(str(settings.docs_path))
    DOCUMENTS = len(index.chunks)
    return index


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.url.path in RATE_LIMITED_PATHS:
        forwarded = request.headers.get("x-forwarded-for", "")
        key = forwarded.split(",")[0].strip() or (request.client.host if request.client else "anonymous")
        if not limiter.allow(key):
            return JSONResponse({"detail": "Too many requests. Please wait a minute."}, status_code=429)

    response = await call_next(request)
    if not request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    in_hf_space = bool(os.environ.get("HF_SPACE") or os.environ.get("SPACE_ID"))
    frame_ancestors = "'self' https://huggingface.co https://*.hf.space" if in_hf_space else "'none'"
    response.headers["X-Content-Type-Options"] = "nosniff"
    if not in_hf_space:
        response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

    if request.url.path in {"/docs", "/docs/", "/redoc", "/redoc/"}:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data: https://fastapi.tiangolo.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            f"connect-src 'self'; frame-ancestors {frame_ancestors}; base-uri 'self'; form-action 'self'"
        )
    else:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; script-src 'self'; "
            f"connect-src 'self'; frame-ancestors {frame_ancestors}; base-uri 'self'; form-action 'self'"
        )
    return response


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", provider=settings.provider, documents=DOCUMENTS or len(get_index().chunks))


@app.get("/api/catalog")
def catalog() -> dict[str, Any]:
    return {
        "clinics": [
            {"name": clinic.name, "description": clinic.description} for clinic in CLINICS
        ],
        "medicines": [
            {
                "name": medicine.name,
                "price": medicine.price,
                "dosage": medicine.dosage,
                "description": medicine.description,
                "prescription": medicine.prescription,
            }
            for medicine in MEDICINES
        ],
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    result = agent.handle(payload.message)

    if result.action in agent.COMMAND_ACTIONS:
        return ChatResponse(reply=result.reply, intent=result.action, entities=result.entities)

    index = get_index()
    results = index.search(payload.message, k=3)
    needs_disclaimer = result.action == "medical_question"

    medical = None
    if needs_disclaimer or (result.action == "unknown" and not results):
        medical = fetch_medlineplus(payload.message)

    needs_disclaimer = result.action == "medical_question" or medical is not None

    context = format_context(results)
    if medical and medical.get("summary"):
        context = f"{context}\n\nMedlinePlus summary:\n{medical['summary']}".strip()

    reply = llm.generate(payload.message, context, result.action)
    if not reply:
        fallback_results = [] if result.action == "medical_question" and not medical else results
        reply = llm.fallback_answer(payload.message, fallback_results, medical, needs_disclaimer)
    elif needs_disclaimer and llm.DISCLAIMER not in reply:
        reply = f"{reply}\n\n{llm.DISCLAIMER}"

    sources: list[Source] = []
    if medical and medical.get("url"):
        sources.append(Source(title=str(medical.get("title") or "MedlinePlus"), url=str(medical["url"])))

    return ChatResponse(reply=reply, intent=result.action, entities=result.entities, sources=sources)


@app.post("/api/agent", response_model=AgentResponse)
def run_agent(payload: AgentRequest) -> AgentResponse:
    return agent.handle(payload.command)


@app.post("/api/feedback")
def feedback(payload: FeedbackRequest) -> dict[str, str]:
    record = {
        "timestamp": time.time(),
        "message": payload.message,
        "predicted_action": payload.predicted_action,
        "correct_action": payload.correct_action,
    }
    try:
        settings.feedback_path.parent.mkdir(parents=True, exist_ok=True)
        with feedback_lock:
            with settings.feedback_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")
    except OSError as exc:
        logger.warning("Could not write feedback: %s", exc)
        return {"status": "error"}
    return {"status": "ok"}


def mount_frontend(application: FastAPI) -> None:
    if settings.frontend_dir.is_dir():
        application.mount(
            "/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend"
        )
    else:
        logger.warning("Frontend directory not found: %s", settings.frontend_dir)


mount_frontend(app)
