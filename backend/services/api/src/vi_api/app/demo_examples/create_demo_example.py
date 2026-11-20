from vi_api.domain.demo_examples.model import DemoExample, Label
from vi_api.domain.demo_examples.repository import DemoExampleRepository


class CreateDemoExample:
    def __init__(self, repository: DemoExampleRepository):
        self.repository = repository

    async def execute(self, part_id: str, label: Label, image: bytes) -> DemoExample:
        return await self.repository.create(part_id, label, image)
