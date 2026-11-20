from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from vi_api.domain.demo_examples.model import Label


class DemoExampleResponse(BaseModel):
    id: UUID
    part_id: str
    label: Label
    created_at: datetime
