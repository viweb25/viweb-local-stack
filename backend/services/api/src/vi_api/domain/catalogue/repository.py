from typing import Protocol

from vi_api.domain.catalogue.model import FunctionTemplate


class CatalogueRepository(Protocol):
    def list_templates(self) -> list[FunctionTemplate]: ...
