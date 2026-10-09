import asyncio
import json
import os

os.environ["COMPASS_DEMO"] = "1"

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import vision  # noqa: E402
from app.main import app  # noqa: E402

GOOD = {"reading_quality": "good", "lines": [
    {"text": "3x = 9", "box": [0.1, 0.1, 0.5, 0.1], "unclear": []},
    {"text": "x = 7", "box": [0.1, 0.3, 0.5, 0.1], "unclear": [{"pos": 4, "alternatives": ["1", "7"]}]}]}


@pytest.fixture
def groq(monkeypatch):
    monkeypatch.setattr(vision, "DEMO", False)
    monkeypatch.setattr(vision, "PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    seen = {}

    def install(status=200, content=None):
        def handler(req):
            seen["req"] = req
            body = {"choices": [{"message": {"content": content if content is not None else "```json\n" + json.dumps(GOOD) + "\n```"}}]}
            return httpx.Response(status, json=body if status == 200 else {"error": {"message": "rate limit"}})
        monkeypatch.setattr(vision, "_TRANSPORT", httpx.MockTransport(handler))
        return seen
    return install


def test_groq_request_shape_and_fenced_json(groq):
    seen = groq()
    out = asyncio.run(vision.read_lines(b"\x89PNG....", "image/png"))
    req, body = seen["req"], json.loads(seen["req"].content)
    assert str(req.url) == "https://api.groq.com/openai/v1/chat/completions"
    assert req.headers["authorization"] == "Bearer test-key"
    assert body["model"] == vision.GROQ_MODEL and body["temperature"] == 0
    assert body["max_tokens"] == 1200 and body["reasoning_effort"] == "none"
    assert body["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert [l["text"] for l in out["lines"]] == ["3x = 9", "x = 7"]
    assert out["lines"][1]["unclear"][0]["alternatives"] == ["1", "7"] and out["reading_quality"] == "good"


def test_groq_error_keeps_the_reason(groq):
    groq(status=429)
    with pytest.raises(vision.VisionError, match="429"):
        asyncio.run(vision.read_lines(b"x", "image/png"))


def test_garbage_reply_is_a_vision_error(groq):
    groq(content="I cannot read this image.")
    with pytest.raises(vision.VisionError):
        asyncio.run(vision.read_lines(b"x", "image/png"))


def test_student_sees_a_clear_error_when_reader_fails(groq):
    groq(status=401)
    c = TestClient(app)
    lesson = c.post("/api/lessons", json={}).json()
    sid = c.post("/api/join", json={"code": lesson["code"]}).json()["session"]
    r = c.post("/api/analyze", data={"code": lesson["code"], "session": sid}, files={"photo": ("w.png", b"\x89PNG" + b"0" * 20, "image/png")})
    assert r.status_code == 502 and "photo reader" in r.json()["detail"]


def test_thinking_text_is_ignored_and_truncation_is_reported(groq):
    groq(content="<think>hmm {not json}</think>\n" + json.dumps(GOOD))
    assert len(asyncio.run(vision.read_lines(b"x", "image/png"))["lines"]) == 2

    def cut(req):
        return httpx.Response(200, json={"choices": [{"finish_reason": "length", "message": {"content": ""}}]})
    vision._TRANSPORT = httpx.MockTransport(cut)
    with pytest.raises(vision.VisionError, match="token limit"):
        asyncio.run(vision.read_lines(b"x", "image/png"))


def test_rate_limit_gives_a_friendly_message_with_wait_time(groq, monkeypatch):
    groq()
    monkeypatch.setattr(vision, "_TRANSPORT", httpx.MockTransport(
        lambda req: httpx.Response(429, json={"error": {"message": "limit"}}, headers={"retry-after": "42"})))
    c = TestClient(app)
    lesson = c.post("/api/lessons", json={}).json()
    sid = c.post("/api/join", json={"code": lesson["code"]}).json()["session"]
    r = c.post("/api/analyze", data={"code": lesson["code"], "session": sid}, files={"photo": ("w.png", b"\x89PNG" + b"0" * 20, "image/png")})
    assert r.status_code == 429 and "42 seconds" in r.json()["detail"]
