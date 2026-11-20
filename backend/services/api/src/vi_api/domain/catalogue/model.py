from dataclasses import dataclass


@dataclass(frozen=True)
class FunctionTemplate:
    id: str
    name: str
    stage: str
    config_schema: dict
