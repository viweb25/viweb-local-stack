import os
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.concurrency import run_in_threadpool

from vi_api.domain.demo_examples.model import DemoExample, Label


class PostgresDemoExampleRepository:
    def __init__(self, sessions: async_sessionmaker, directory: Path):
        self.sessions = sessions
        self.directory = directory

    async def create(self, part_id: str, label: Label, image: bytes) -> DemoExample:
        example_id = uuid4()
        await run_in_threadpool(self._write_image, example_id, image)
        async with self.sessions.begin() as session:
            result = await session.execute(
                text("""
                    INSERT INTO demo_examples (id, part_id, label)
                    VALUES (:id, :part_id, :label)
                    RETURNING id, part_id, label, created_at
                """),
                {"id": example_id, "part_id": part_id, "label": label},
            )
            return DemoExample(**result.mappings().one())

    async def list(self) -> list[DemoExample]:
        async with self.sessions() as session:
            result = await session.execute(
                text(
                    "SELECT id, part_id, label, created_at FROM demo_examples "
                    "ORDER BY created_at DESC, id DESC"
                )
            )
            return [DemoExample(**row) for row in result.mappings()]

    async def get_image_path(self, example_id: UUID) -> Path | None:
        async with self.sessions() as session:
            exists = await session.scalar(
                text("SELECT 1 FROM demo_examples WHERE id = :id"), {"id": example_id}
            )
        path = self.directory / f"{example_id}.jpg"
        return path if exists and await run_in_threadpool(path.is_file) else None

    def _write_image(self, example_id: UUID, image: bytes) -> None:
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self.directory / f"{example_id}.jpg"
        with path.open("xb") as stream:
            stream.write(image)
            stream.flush()
            os.fsync(stream.fileno())
