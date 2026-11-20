from pathlib import Path

from pydantic import TypeAdapter

from vi_api.domain.catalogue.model import FunctionTemplate


class JsonCatalogueRepository:
    """Validated public reference data; never a repository for customer records."""

    def __init__(self, path: Path):
        self.path = path

    def list_templates(self) -> list[FunctionTemplate]:
        return TypeAdapter(list[FunctionTemplate]).validate_json(self.path.read_bytes())
