import os
import tempfile

import pytest
from fastapi.testclient import TestClient

_TMP = tempfile.mkdtemp(prefix="medicare-tests-")
os.environ.setdefault("MEDLINEPLUS_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "0")
os.environ.setdefault("LLM_PROVIDER", "none")
os.environ.setdefault("FEEDBACK_PATH", os.path.join(_TMP, "feedback.jsonl"))

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
