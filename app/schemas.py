from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


def _clean_text(value: str) -> str:
    value = " ".join(value.split())
    if not value:
        raise ValueError("text must not be empty")
    return value


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)

    @field_validator("message")
    @classmethod
    def clean(cls, value: str) -> str:
        return _clean_text(value)


class AgentRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)

    @field_validator("command")
    @classmethod
    def clean(cls, value: str) -> str:
        return _clean_text(value)


class Source(BaseModel):
    title: str
    url: str | None = None


class ChatResponse(BaseModel):
    reply: str
    intent: str
    entities: dict[str, Any] = Field(default_factory=dict)
    sources: list[Source] = Field(default_factory=list)


class AgentResponse(BaseModel):
    action: str
    entities: dict[str, Any] = Field(default_factory=dict)
    reply: str


class FeedbackRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    predicted_action: str = Field(min_length=1, max_length=60)
    correct_action: str = Field(min_length=1, max_length=60)

    @field_validator("message", "predicted_action", "correct_action")
    @classmethod
    def clean(cls, value: str) -> str:
        return _clean_text(value)


class HealthResponse(BaseModel):
    status: str
    provider: str
    documents: int
