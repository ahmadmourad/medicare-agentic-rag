import pytest
from pydantic import ValidationError

from app.schemas import AgentRequest, ChatRequest, FeedbackRequest


def test_chat_request_normalizes_whitespace():
    assert ChatRequest(message="  hello   world  ").message == "hello world"


@pytest.mark.parametrize("message", ["", "   ", "x" * 501])
def test_chat_request_rejects_invalid_messages(message):
    with pytest.raises(ValidationError):
        ChatRequest(message=message)


def test_agent_request_normalizes_whitespace():
    assert AgentRequest(command="  book   now ").command == "book now"


def test_agent_request_rejects_empty_command():
    with pytest.raises(ValidationError):
        AgentRequest(command="   ")


def test_feedback_request_validates_all_fields():
    request = FeedbackRequest(
        message="  how much is panadol ",
        predicted_action="unknown",
        correct_action="price",
    )
    assert request.message == "how much is panadol"

    with pytest.raises(ValidationError):
        FeedbackRequest(message="hello", predicted_action="", correct_action="price")
