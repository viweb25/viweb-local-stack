import asyncio
import logging
import os
from collections import Counter
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from vi_inference.demo_inspection import (
    InspectionResult,
    SceneDescription,
    describe_scene,
    read_jpeg,
)

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


@lru_cache(maxsize=4)
def load_model(weights: str):
    from ultralytics import YOLO

    return YOLO(weights, task="detect")


def configured_weights() -> Path | None:
    path = Path(os.getenv("VI_YOLO_WEIGHTS", ""))
    return path.resolve() if path.suffix in {".pt", ".onnx"} and path.is_file() else None


class ModelInfo(BaseModel):
    model: str | None = None
    classes: list[str] = Field(default_factory=list)
    status: Literal["ready", "missing", "unavailable"]


def model_classes(weights: str) -> list[str]:
    with model_lock:
        return list(load_model(weights).names.values())


@router.get("/detection-model", response_model=ModelInfo)
async def detection_model():
    weights = configured_weights()
    if weights is None:
        return ModelInfo(status="missing")
    try:
        classes = await run_in_threadpool(model_classes, str(weights))
    except Exception:
        logger.exception("YOLO model could not be loaded")
        return ModelInfo(status="unavailable", model=weights.name)
    return ModelInfo(status="ready", model=weights.name, classes=classes)


def detect(weights: str, image: bytes, target: str | None, confidence: float) -> list[Detection]:
    from PIL import Image

    with Image.open(BytesIO(image), formats=["JPEG"]) as source:
        if source.width * source.height > 25_000_000:
            raise ValueError("Frame exceeds the 25 megapixel limit")
        frame = source.convert("RGB")
    with model_lock:
        model = load_model(weights)
        if target is not None and target not in model.names.values():
            raise ValueError("Target class is missing from the configured model")
        class_ids = (
            None
            if target is None
            else [index for index, label in model.names.items() if label == target]
        )
        prediction = model.predict(
            frame, conf=confidence, classes=class_ids, max_det=1000, verbose=False
        )[0]
        boxes = prediction.boxes
        return [
            Detection(
                label=prediction.names[int(class_id)],
                confidence=score,
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
            )
            for (x1, y1, x2, y2), score, class_id in zip(
                boxes.xyxyn.cpu().tolist(),
                boxes.conf.cpu().tolist(),
                boxes.cls.cpu().tolist(),
                strict=True,
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

    weights = configured_weights()
    if weights is None:
        return DetectionResult(decision="HOLD", reason="Local YOLO model is not configured.")

    target = target.strip()
    try:
        detections = await run_in_threadpool(detect, str(weights), image, target, confidence)
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


class ImageAnalysis(BaseModel):
    detections: list[Detection] = Field(default_factory=list)
    counts: dict[str, int] = Field(default_factory=dict)
    model: str | None = None
    detection_error: str | None = None
    description: SceneDescription = Field(default_factory=SceneDescription)
    error: str | None = None


async def detect_scene(image: bytes, confidence: float) -> ImageAnalysis:
    weights = configured_weights()
    if weights is None:
        return ImageAnalysis(detection_error="Local YOLO model is not configured.")
    try:
        detections = await run_in_threadpool(detect, str(weights), image, None, confidence)
    except Exception:
        logger.exception("YOLO image analysis failed")
        return ImageAnalysis(
            model=weights.name, detection_error="YOLO could not process the image."
        )
    return ImageAnalysis(
        detections=detections,
        counts=dict(Counter(box.label for box in detections)),
        model=weights.name,
    )


@router.post(
    "/analyze",
    response_model=ImageAnalysis,
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def analyze_image(
    request: Request,
    confidence: Annotated[float, Query(ge=0.01, le=1)] = 0.5,
):
    try:
        image = await read_jpeg(request)
    except ValueError as exc:
        return ImageAnalysis(error=str(exc))

    result, description = await asyncio.gather(
        detect_scene(image, confidence), describe_scene(image)
    )
    result.description = description
    return result


@router.post("/trained-models/{org_id}/{job_id}/preview", response_model=list[Detection])
async def preview_trained_model(
    org_id: UUID,
    job_id: UUID,
    request: Request,
    confidence: Annotated[float, Query(ge=0.01, le=1)] = 0.5,
):
    run_dir = os.getenv("VI_TRAINING_RUN_DIR")
    if not run_dir:
        raise HTTPException(404, "Trained model unavailable")
    checkpoint = Path(run_dir) / str(org_id) / str(job_id) / "best.pt"
    if not checkpoint.is_file():
        raise HTTPException(404, "Trained model unavailable")
    try:
        image = await read_jpeg(request)
        return await run_in_threadpool(detect, str(checkpoint), image, None, confidence)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        logger.exception("Trained YOLO model preview failed")
        raise HTTPException(503, "Could not run the trained model") from exc
