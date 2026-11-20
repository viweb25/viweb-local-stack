from pathlib import Path
from uuid import UUID

from vi_api.domain.demo_examples.repository import DemoExampleRepository


class GetDemoExampleImage:
    def __init__(self, repository: DemoExampleRepository):
        self.repository = repository

    async def execute(self, example_id: UUID) -> Path | None:
        return await self.repository.get_image_path(example_id)
