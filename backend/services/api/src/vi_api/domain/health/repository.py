from typing import Protocol


class ReadinessRepository(Protocol):
    async def is_ready(self) -> bool: ...
