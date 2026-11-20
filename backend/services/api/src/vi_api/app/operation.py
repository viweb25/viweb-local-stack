from abc import ABC, abstractmethod
from typing import Generic, TypeVar

Result = TypeVar("Result")


class Operation(ABC, Generic[Result]):
    """One request's use case. Return a result or raise an exception."""

    @abstractmethod
    def execute(self) -> Result: ...


class AsyncOperation(ABC, Generic[Result]):
    """Use-case contract for asynchronous I/O."""

    @abstractmethod
    async def execute(self) -> Result: ...
