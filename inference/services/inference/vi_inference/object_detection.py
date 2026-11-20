import logging
import os
from functools import cache
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Annotated

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from vi_inference.demo_inspection import InspectionResult, read_jpeg

router = APIRouter(prefix="/api/v1/demo", tags=["Object detection"])
logger = logging.getLogger(__name__)
model_lock = Lock()


class Detection(BaseModel):
    label: str
    confidence: float = Field(ge=0, le=1)
    x1: float = Field(ge=0, le=1)
    y1: float = Field(ge=0, le=1)
    x2: float = Field(ge=0, le=1)
    y2: float = Field(ge=0, le=1)


class DetectionResult(InspectionResult):
    detections: list[Detection] = Field(default_factory=list)


@cache
def load_model(weights: str):
    from ultralytics import YOLO

    return YOLO(weights, task="detect")


def detect(weights: str, image: bytes, target: str, confidence: float) -> list[Detection]:
    from PIL import Image

    with Image.open(BytesIO(image), formats=["JPEG"]) as source:
        if source.width * source.height > 25_000_000:
            raise ValueError("Frame exceeds the 25 megapixel limit")
        frame = source.convert("RGB")
    with model_lock:
        model = load_model(weights)
        if target not in model.names.values():
            raise ValueError("Target class is missing from the configured model")
        class_ids = [index for index, label in model.names.items() if label == target]
        prediction = model.predict(
            frame, conf=confidence, classes=class_ids, max_det=1000, verbose=False
        )[0]
        boxes = prediction.boxes
        return [
            Detection(label=target, confidence=score, x1=x1, y1=y1, x2=x2, y2=y2)
            for (x1, y1, x2, y2), score in zip(
                boxes.xyxyn.cpu().tolist(), boxes.conf.cpu().tolist(), strict=True
            )
            if x2 > x1 and y2 > y1
        ]


@router.post(
    "/detect",
    response_model=DetectionResult,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def inspect_objects(
    request: Request,
    target: Annotated[str, Query(min_length=1, max_length=100, pattern=r"\S")],
    expected_count: Annotated[int, Query(ge=1, le=999)],
    confidence: Annotated[float, Query(ge=0.01, le=1)] = 0.5,
):
    try:
        image = await read_jpeg(request)
    except ValueError as exc:
        return DetectionResult(decision="HOLD", reason=str(exc))

    weights = Path(os.getenv("VI_YOLO_WEIGHTS", ""))
    if weights.suffix not in {".pt", ".onnx"} or not weights.is_file():
        return DetectionResult(decision="HOLD", reason="Local YOLO model is not configured.")

    target = target.strip()
    try:
        detections = await run_in_threadpool(
            detect, str(weights.resolve()), image, target, confidence
        )
    except Exception:
        logger.exception("YOLO inspection failed")
        return DetectionResult(
            decision="HOLD", reason="YOLO could not process the frame or target class."
        )

    count = len(detections)
    return DetectionResult(
        decision="PASS" if count == expected_count else "FAIL",
        reason=f"Detected {count} of {expected_count} expected objects in class {target}.",
        model=weights.name,
        detections=detections,
    )
