from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

Label = Literal["PASS", "FAIL"]


@dataclass(frozen=True)
class DemoExample:
    id: UUID
    part_id: str
    label: Label
    created_at: datetime
