from vi_api.app.operation import AsyncOperation
from vi_api.domain.health.repository import ReadinessRepository


class CheckReadiness(AsyncOperation[bool]):
    def __init__(self, repository: ReadinessRepository):
        self.repository = repository

    async def execute(self) -> bool:
        return await self.repository.is_ready()
