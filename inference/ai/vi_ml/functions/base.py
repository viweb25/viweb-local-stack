from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class FunctionAI(ABC):
    """One implementation per function type. Return the shared result envelope.

    Predictions describe observations; the edge rule engine makes the final decision.
    Training/export are separate pipelines and may require optional GPU dependencies.
    """

    @abstractmethod
    def load(self, package_path: Path, licence: dict[str, Any]) -> None: ...

    @abstractmethod
    def predict(self, frame: bytes, config: dict[str, Any]) -> dict[str, Any]: ...

    @abstractmethod
    def health(self) -> dict[str, Any]: ...
