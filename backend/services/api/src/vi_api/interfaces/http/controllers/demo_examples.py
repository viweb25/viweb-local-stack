from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse

from vi_api.app.demo_examples.create_demo_example import CreateDemoExample
from vi_api.app.demo_examples.get_demo_example_image import GetDemoExampleImage
from vi_api.app.demo_examples.list_demo_examples import ListDemoExamples
from vi_api.container import (
    get_create_demo_example,
    get_demo_example_image_operation,
    get_list_demo_examples,
)
from vi_api.domain.demo_examples.model import Label
from vi_api.interfaces.http.errors import ApiError, ErrorCode
from vi_api.interfaces.http.schemas.demo_examples import DemoExampleResponse
from vi_api.interfaces.http.schemas.errors import ErrorResponse
from vi_api.interfaces.http.validation import read_jpeg


class DemoExamplesController:
    async def create_example(
        self,
        request: Request,
        operation: Annotated[CreateDemoExample, Depends(get_create_demo_example)],
        part_id: Annotated[str, Query(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")],
        label: Label,
    ):
        return await operation.execute(part_id, label, await read_jpeg(request))

    async def get_examples(
        self, operation: Annotated[ListDemoExamples, Depends(get_list_demo_examples)]
    ):
        return await operation.execute()

    async def get_example_image(
        self,
        example_id: UUID,
        operation: Annotated[GetDemoExampleImage, Depends(get_demo_example_image_operation)],
    ):
        path = await operation.execute(example_id)
        if path is None:
            raise ApiError(404, ErrorCode.EXAMPLE_IMAGE_NOT_FOUND, "Example image unavailable")
        return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


router = APIRouter(
    prefix="/api/v1/demo/examples",
    tags=["Local inspection demo"],
    responses={404: {"model": ErrorResponse}},
)
controller = DemoExamplesController()
router.add_api_route(
    "",
    controller.create_example,
    methods=["POST"],
    status_code=201,
    response_model=DemoExampleResponse,
    responses={code: {"model": ErrorResponse} for code in (413, 415, 422)},
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}},
        }
    },
)
router.add_api_route(
    "", controller.get_examples, methods=["GET"], response_model=list[DemoExampleResponse]
)
router.add_api_route(
    "/{example_id}/image",
    controller.get_example_image,
    methods=["GET"],
    response_class=FileResponse,
    responses={
        200: {"content": {"image/jpeg": {"schema": {"type": "string", "format": "binary"}}}},
        422: {"model": ErrorResponse},
    },
)
