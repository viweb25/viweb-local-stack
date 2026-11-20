from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Membership:
    org_id: UUID
    name: str
    role: str


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    display_name: str | None
    email: str | None
    organisations: list[Membership]
