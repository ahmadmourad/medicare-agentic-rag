import atexit
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_TMP = tempfile.mkdtemp(prefix="medicare-tests-")
atexit.register(shutil.rmtree, _TMP, True)
os.environ.setdefault("MEDLINEPLUS_ENABLED", "false")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "0")
os.environ.setdefault("LLM_PROVIDER", "none")
os.environ.setdefault("FEEDBACK_PATH", os.path.join(_TMP, "feedback.jsonl"))

from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
