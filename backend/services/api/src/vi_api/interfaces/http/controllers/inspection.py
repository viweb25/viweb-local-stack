from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, Request, Response

from vi_api.domain.identity.models import CurrentUser
from vi_api.interfaces.http.controllers.auth import BrowserOrigin
from vi_api.interfaces.http.dependencies.identity import SettingsDependency, get_current_user
from vi_api.interfaces.http.errors import ApiError, ErrorCode

router = APIRouter(prefix="/api/v1/demo", tags=["Inspection"])
MAX_FRAME_BYTES = 5 * 1024 * 1024


@router.post(
    "/{engine}",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
async def inspect(
    engine: Literal["inspect", "detect"],
    request: Request,
    settings: SettingsDependency,
    origin: BrowserOrigin,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Response:
    if not user.organisations:
        raise ApiError(403, ErrorCode.ORGANISATION_ACCESS_DENIED, "Workspace access is required")
    if request.headers.get("content-type") != "image/jpeg":
        raise ApiError(415, ErrorCode.UNSUPPORTED_IMAGE_TYPE, "A JPEG frame is required")
    image = bytearray()
    async for chunk in request.stream():
        if len(image) + len(chunk) > MAX_FRAME_BYTES:
            raise ApiError(413, ErrorCode.IMAGE_TOO_LARGE, "Image exceeds 5 MiB")
        image.extend(chunk)
    try:
        async with httpx.AsyncClient(timeout=95, trust_env=False) as client:
            result = await client.post(
                f"{settings.inference_url.rstrip('/')}/api/v1/demo/{engine}",
                params=request.query_params.multi_items(),
                content=bytes(image),
                headers={"Content-Type": "image/jpeg"},
            )
    except httpx.HTTPError as exc:
        raise ApiError(
            503, ErrorCode.INFERENCE_UNAVAILABLE, "Inspection service unavailable"
        ) from exc
    if result.status_code not in (200, 422):
        raise ApiError(503, ErrorCode.INFERENCE_UNAVAILABLE, "Inspection service unavailable")
    return Response(
        result.content,
        status_code=result.status_code,
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )
