from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from vi_api.infrastructure.database.models.base import Base


class DemoExampleRow(Base):
    __tablename__ = "demo_examples"
    __table_args__ = (CheckConstraint("label IN ('PASS', 'FAIL')", name="ck_demo_example_label"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    part_id: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
