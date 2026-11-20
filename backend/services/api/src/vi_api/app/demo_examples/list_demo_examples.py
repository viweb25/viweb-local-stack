from vi_api.app.operation import AsyncOperation
from vi_api.domain.demo_examples.model import DemoExample
from vi_api.domain.demo_examples.repository import DemoExampleRepository


class ListDemoExamples(AsyncOperation[list[DemoExample]]):
    def __init__(self, repository: DemoExampleRepository):
        self.repository = repository

    async def execute(self) -> list[DemoExample]:
        return await self.repository.list()
