from vi_api.app.operation import Operation
from vi_api.domain.catalogue.model import FunctionTemplate
from vi_api.domain.catalogue.repository import CatalogueRepository


class GetFunctionTemplates(Operation[list[FunctionTemplate]]):
    def __init__(self, repository: CatalogueRepository):
        self.repository = repository

    def execute(self) -> list[FunctionTemplate]:
        return self.repository.list_templates()
