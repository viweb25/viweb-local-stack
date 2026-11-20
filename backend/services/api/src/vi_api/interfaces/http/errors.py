from enum import StrEnum

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class ErrorCode(StrEnum):
    INVALID_SIGNUP_CODE = "invalid_signup_code"
    SIGNUP_UNAVAILABLE = "signup_unavailable"
    SIGNUP_CONFLICT = "signup_conflict"
    INFERENCE_UNAVAILABLE = "inference_unavailable"
    INVALID_CREDENTIALS = "invalid_credentials"
    SIGN_IN_RATE_LIMITED = "sign_in_rate_limited"
    AUTHENTICATION_REQUIRED = "authentication_required"
    ORGANISATION_ACCESS_DENIED = "organisation_access_denied"
    SIGN_IN_UNAVAILABLE = "sign_in_unavailable"
    INVALID_REQUEST_ORIGIN = "invalid_request_origin"
    DEMO_DISABLED = "demo_disabled"
    EXAMPLE_IMAGE_NOT_FOUND = "example_image_not_found"
    UNSUPPORTED_IMAGE_TYPE = "unsupported_image_type"
    IMAGE_TOO_LARGE = "image_too_large"
    INVALID_IMAGE = "invalid_image"


class ApiError(HTTPException):
    def __init__(self, status_code: int, code: ErrorCode, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.code = code


async def http_error(request: Request, exc: HTTPException):
    code = exc.code if isinstance(exc, ApiError) else f"http_{exc.status_code}"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": str(exc.detail)}},
        headers=exc.headers,
    )


async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {"code": "validation_error", "message": "Request does not match the contract"}
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(RequestValidationError, validation_error)
