from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from vi_api.app.health.check_readiness import CheckReadiness
from vi_api.container import check_readiness
from vi_api.interfaces.http.schemas.errors import ErrorResponse


class Health(BaseModel):
    status: str
    service: str


class HealthController:
    def live(self):
        """Process liveness only; does not claim database or hardware readiness."""
        return Health(status="ok", service="api")

    async def ready(self, operation: Annotated[CheckReadiness, Depends(check_readiness)]):
        """Database and migration readiness, independent of model availability."""
        if not await operation.execute():
            return JSONResponse(
                status_code=503,
                content={"error": {"code": "not_ready", "message": "Database migration not ready"}},
            )
        return Health(status="ok", service="api")


router = APIRouter(tags=["health"])
controller = HealthController()
router.add_api_route("/health/live", controller.live, methods=["GET"], response_model=Health)
router.add_api_route(
    "/health/ready",
    controller.ready,
    methods=["GET"],
    response_model=Health,
    responses={503: {"model": ErrorResponse}},
)
