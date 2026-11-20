import json

import httpx
import pytest
from fastapi.testclient import TestClient
from vi_inference.main import app

TEST_JPEG = b"\xff\xd8\xfftest\xff\xd9"
INSPECT = "/api/v1/demo/inspect?rule=Cap+required"
JPEG_HEADERS = {"Content-Type": "image/jpeg"}


@pytest.mark.parametrize(
    ("verdict", "visibility", "done_reason", "expected"),
    [
        ("PASS", "clear", "stop", "PASS"),
        ("FAIL", "clear", "stop", "FAIL"),
        ("HOLD", "clear", "stop", "HOLD"),
        ("unknown", "clear", "stop", "HOLD"),
        ("PASS", "clear", "length", "HOLD"),
        ("FAIL", "absent", "stop", "HOLD"),
    ],
)
def test_demo_uses_only_complete_valid_observations(
    monkeypatch, verdict, visibility, done_reason, expected
):
    monkeypatch.setenv("VI_DEMO_OLLAMA_URL", "http://ollama:11434")
    client_class = httpx.AsyncClient

    def respond(request):
        assert request.url.path == "/api/chat"
        assert b"Cap required" in request.content
        assert b'"images":[' in request.content
        return httpx.Response(
            200,
            json={
                "done": True,
                "done_reason": done_reason,
                "message": {
                    "content": json.dumps(
                        {
                            "verdict": verdict,
                            "part_visibility": visibility,
                            "reason": "Visual evidence.",
                        }
                    )
                },
            },
        )

    def client(**kwargs):
        return client_class(transport=httpx.MockTransport(respond), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client)
    result = TestClient(app).post(INSPECT, headers=JPEG_HEADERS, content=TEST_JPEG)
    assert result.json()["decision"] == expected


def test_demo_holds_when_frame_or_provider_is_missing(monkeypatch):
    monkeypatch.delenv("VI_DEMO_OLLAMA_URL", raising=False)
    client = TestClient(app)
    for image in (b"", TEST_JPEG):
        result = client.post(INSPECT, headers=JPEG_HEADERS, content=image)
        assert result.json()["decision"] == "HOLD"
