from typing import Annotated

from fastapi import APIRouter, Depends

from vi_api.app.catalogue.get_function_templates import GetFunctionTemplates
from vi_api.container import get_function_templates
from vi_api.interfaces.http.schemas.catalogue import FunctionTemplate


class CatalogueController:
    def templates(
        self, operation: Annotated[GetFunctionTemplates, Depends(get_function_templates)]
    ):
        """Public static catalogue. A template does not imply a trained model exists."""
        return operation.execute()


router = APIRouter(prefix="/api/v1", tags=["catalogue"])
router.add_api_route(
    "/function-templates",
    CatalogueController().templates,
    methods=["GET"],
    response_model=list[FunctionTemplate],
)
