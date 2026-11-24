import pytest
from fastapi.testclient import TestClient
from vi_inference import demo_inspection, object_detection
from vi_inference.main import app

URL = "/api/v1/demo/detect?target=cap&expected_count=1"
JPEG = b"\xff\xd8\xfftest\xff\xd9"
HEADERS = {"Content-Type": "image/jpeg"}


@pytest.mark.parametrize(("count", "decision"), [(0, "FAIL"), (1, "PASS"), (2, "FAIL")])
def test_detection_count_and_boxes(monkeypatch, tmp_path, count, decision):
    weights = tmp_path / "best.pt"
    weights.touch()
    monkeypatch.setenv("VI_YOLO_WEIGHTS", str(weights))
    box = object_detection.Detection(label="cap", confidence=0.9, x1=0.1, y1=0.2, x2=0.3, y2=0.4)

    def detect(model_path, image, target, confidence):
        assert (model_path, image, target, confidence) == (str(weights), JPEG, "cap", 0.5)
        return [box] * count

    monkeypatch.setattr(object_detection, "detect", detect)
    response = TestClient(app).post(URL, content=JPEG, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["decision"] == decision
    assert response.json()["detections"] == [box.model_dump()] * count


def test_missing_weights_and_invalid_jpeg_hold(monkeypatch):
    monkeypatch.delenv("VI_YOLO_WEIGHTS", raising=False)
    client = TestClient(app)
    for image in (JPEG, b"invalid"):
        response = client.post(URL, content=image, headers=HEADERS)
        assert response.status_code == 200
        assert response.json()["decision"] == "HOLD"
        assert response.json()["detections"] == []


def test_detection_model_lists_checkpoint_classes(monkeypatch, tmp_path):
    weights = tmp_path / "best.pt"
    weights.touch()
    monkeypatch.setenv("VI_YOLO_WEIGHTS", str(weights))
    monkeypatch.setattr(object_detection, "model_classes", lambda path: ["cap", "washer"])
    client = TestClient(app)
    assert client.get("/api/v1/demo/detection-model").json() == {
        "model": "best.pt",
        "classes": ["cap", "washer"],
        "status": "ready",
    }
    weights.unlink()
    assert client.get("/api/v1/demo/detection-model").json()["status"] == "missing"


def test_analyze_groups_detections_and_keeps_counts_when_qwen_is_missing(monkeypatch, tmp_path):
    weights = tmp_path / "best.pt"
    weights.touch()
    monkeypatch.setenv("VI_YOLO_WEIGHTS", str(weights))

    def detect(model_path, image, target, confidence):
        assert model_path == str(weights)
        assert target is None
        return [
            object_detection.Detection(label=label, confidence=0.9, x1=0, y1=0, x2=1, y2=1)
            for label in ("person", "car", "person")
        ]

    async def chat(endpoint, payload):
        assert payload["messages"][-1]["images"]
        return "People are next to a car."

    monkeypatch.setattr(object_detection, "detect", detect)
    monkeypatch.setattr(demo_inspection, "chat", chat)
    monkeypatch.setenv("VI_DEMO_OLLAMA_URL", "http://ollama:11434")

    client = TestClient(app)
    frame = b"\xff\xd8\xfftest\xff\xd9"
    headers = {"Content-Type": "image/jpeg"}
    result = client.post("/api/v1/demo/analyze", headers=headers, content=frame).json()
    assert result["counts"] == {"person": 2, "car": 1}
    assert len(result["detections"]) == 3
    assert result["description"]["text"] == "People are next to a car."

    monkeypatch.delenv("VI_DEMO_OLLAMA_URL")
    result = client.post("/api/v1/demo/analyze", headers=headers, content=frame).json()
    assert result["counts"] == {"person": 2, "car": 1}
    assert result["description"]["error"] == "Vision model is not configured."
