from fastapi import Request

from vi_api.interfaces.http.errors import ApiError, ErrorCode

MAX_IMAGE_BYTES = 5 * 1024 * 1024


async def read_jpeg(request: Request) -> bytes:
    if request.headers.get("content-type") != "image/jpeg":
        raise ApiError(415, ErrorCode.UNSUPPORTED_IMAGE_TYPE, "Send a JPEG image")
    image = bytearray()
    async for chunk in request.stream():
        if len(image) + len(chunk) > MAX_IMAGE_BYTES:
            raise ApiError(413, ErrorCode.IMAGE_TOO_LARGE, "Image exceeds 5 MiB")
        image.extend(chunk)
    if not image.startswith(b"\xff\xd8\xff") or not image.endswith(b"\xff\xd9"):
        raise ApiError(422, ErrorCode.INVALID_IMAGE, "Invalid JPEG framing")
    return bytes(image)
