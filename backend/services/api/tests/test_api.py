from fastapi.testclient import TestClient
from vi_api.bootstrap import app

client = TestClient(app)


def test_liveness_and_catalogue():
    assert client.get("/health/live").json() == {"status": "ok", "service": "api"}
    response = client.get("/api/v1/function-templates")
    assert response.status_code == 200
    assert len(response.json()) == 8
    assert all(item["stage"].startswith("planned:") for item in response.json())


def test_unknown_route_uses_error_envelope():
    response = client.get("/api/v1/projects")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_404"


def test_inspection_requires_a_session():
    response = client.post(
        "/api/v1/demo/detect?target=cap&expected_count=6",
        headers={"Origin": "http://127.0.0.1:3000", "Content-Type": "image/jpeg"},
        content=b"frame",
    )
    assert response.status_code == 401


def test_inspection_forwards_frame_and_query(monkeypatch):
    from uuid import uuid4

    import httpx
    from vi_api.domain.identity.models import CurrentUser, Membership
    from vi_api.interfaces.http.controllers import inspection
    from vi_api.interfaces.http.dependencies.identity import get_current_user

    user = CurrentUser(uuid4(), "Operator", None, [Membership(uuid4(), "Factory", "operator")])
    monkeypatch.setitem(app.dependency_overrides, get_current_user, lambda: user)

    async def post(self, url, **kwargs):
        assert url == "http://127.0.0.1:8001/api/v1/demo/detect"
        assert kwargs["params"] == [("target", "cap"), ("expected_count", "6")]
        assert kwargs["content"] == b"frame"
        return httpx.Response(200, json={"decision": "PASS"})

    monkeypatch.setattr(inspection.httpx.AsyncClient, "post", post)
    response = client.post(
        "/api/v1/demo/detect?target=cap&expected_count=6",
        headers={"Origin": "http://127.0.0.1:3000", "Content-Type": "image/jpeg"},
        content=b"frame",
    )
    assert response.status_code == 200
    assert response.json() == {"decision": "PASS"}
