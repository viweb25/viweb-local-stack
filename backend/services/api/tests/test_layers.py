from fastapi.testclient import TestClient
from vi_api.app.catalogue.get_function_templates import GetFunctionTemplates
from vi_api.bootstrap import app
from vi_api.container import get_function_templates
from vi_api.domain.catalogue.model import FunctionTemplate


class FakeRepository:
    def list_templates(self):
        return [
            FunctionTemplate(id="test", name="Example", stage="planned: test", config_schema={})
        ]


def test_controller_uses_injected_service_and_repository():
    app.dependency_overrides[get_function_templates] = lambda: GetFunctionTemplates(
        FakeRepository()
    )
    try:
        response = TestClient(app).get("/api/v1/function-templates")
        assert response.status_code == 200
        assert response.json()[0]["id"] == "test"
    finally:
        app.dependency_overrides.clear()


def test_readiness_fails_closed_when_database_is_unavailable(monkeypatch):
    class UnavailableEngine:
        def connect(self):
            raise ConnectionError("private connection detail")

    monkeypatch.setattr("vi_api.container.engine", UnavailableEngine())
    response = TestClient(app).get("/health/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "not_ready"
    assert "private" not in response.text


def test_demo_controller_uses_repository_binding_and_validates_upload():
    from datetime import UTC, datetime
    from uuid import uuid4

    from vi_api.container import get_demo_example_repository
    from vi_api.domain.demo_examples.model import DemoExample

    image = b"\xff\xd8\xfftest\xff\xd9"
    example = DemoExample(uuid4(), "part-1", "PASS", datetime.now(UTC))

    class FakeDemoRepository:
        async def create(self, part_id, label, payload):
            assert (part_id, label, payload) == ("part-1", "PASS", image)
            return example

    client = TestClient(app)
    app.dependency_overrides[get_demo_example_repository] = FakeDemoRepository
    try:
        url = "/api/v1/demo/examples?part_id=part-1&label=PASS"
        result = client.post(url, content=image, headers={"Content-Type": "image/jpeg"})
        assert result.status_code == 201
        assert result.json()["id"] == str(example.id)

        result = client.post(url, content=b"bad", headers={"Content-Type": "image/jpeg"})
        assert result.status_code == 422
        assert result.json()["error"]["code"] == "invalid_image"
    finally:
        app.dependency_overrides.pop(get_demo_example_repository, None)
