from fastapi import FastAPI
from pydantic import BaseModel

from vi_inference.demo_inspection import router as demo_inspection_router
from vi_inference.object_detection import router as object_detection_router

app = FastAPI(title="VI WebSync Inference", version="0.1.0")
app.include_router(demo_inspection_router)
app.include_router(object_detection_router)


class Health(BaseModel):
    status: str
    service: str
    loaded_packages: int


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


@app.get("/health/live", response_model=Health)
def live():
    return Health(status="ok", service="inference", loaded_packages=0)


@app.post("/api/v1/predict", status_code=503, response_model=ErrorResponse)
def predict():
    """No approved model is loaded. Never fabricate a successful inspection."""
    return ErrorResponse(
        error=ErrorDetail(code="model_not_loaded", message="No approved function package loaded")
    )
