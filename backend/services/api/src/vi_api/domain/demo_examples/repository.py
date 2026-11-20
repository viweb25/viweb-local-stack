from pathlib import Path
from typing import Protocol
from uuid import UUID

from vi_api.domain.demo_examples.model import DemoExample, Label


class DemoExampleRepository(Protocol):
    async def create(self, part_id: str, label: Label, image: bytes) -> DemoExample: ...

    async def list(self) -> list[DemoExample]: ...

    async def get_image_path(self, example_id: UUID) -> Path | None: ...
