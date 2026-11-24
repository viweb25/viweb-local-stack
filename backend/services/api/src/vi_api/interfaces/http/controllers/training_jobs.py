import json
import os
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

import httpx
from fastapi import HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import text

from vi_api.infrastructure.database.session import Session
from vi_api.interfaces.http.controllers.auth import BrowserOrigin
from vi_api.interfaces.http.controllers.training_datasets import OrgMember, require_editor, router
from vi_api.interfaces.http.dependencies.identity import SettingsDependency
from vi_api.interfaces.http.validation import read_jpeg


class StartTraining(BaseModel):
    revision: int = Field(gt=0)


class TrainingJob(BaseModel):
    id: UUID
    dataset_revision: int
    status: Literal["queued", "running", "succeeded", "failed"]
    error: str | None
    created_at: datetime
    finished_at: datetime | None


@router.post("/{dataset_id}/jobs", status_code=202)
async def start_training(
    dataset_id: UUID,
    data: StartTraining,
    member: OrgMember,
    _: BrowserOrigin,
) -> TrainingJob:
    require_editor(member)
    ids = {"id": dataset_id, "org": member.org_id}
    async with Session.begin() as session:
        result = await session.execute(
            text("""
                SELECT part_name, revision FROM training_datasets
                WHERE id = :id AND org_id = :org FOR UPDATE
            """),
            ids,
        )
        dataset = result.mappings().one_or_none()
        if dataset is None:
            raise HTTPException(404, "Dataset not found")
        if dataset["revision"] != data.revision:
            raise HTTPException(409, "Open the latest saved version before training.")
        active = await session.execute(
            text("""
                SELECT id, dataset_revision, status, error, created_at, finished_at
                FROM training_jobs WHERE dataset_id = :id AND status IN ('queued', 'running')
            """),
            ids,
        )
        job = active.mappings().one_or_none()
        if job is not None:
            if job["dataset_revision"] != data.revision:
                raise HTTPException(409, "An earlier revision is still training.")
            return TrainingJob.model_validate(dict(job))
        result = await session.execute(
            text("""
                SELECT id, digest, media_type, reviewed, boxes FROM training_photos
                WHERE dataset_id = :id ORDER BY position
            """),
            ids,
        )
        photos = [dict(photo) for photo in result.mappings()]
        if not all(photo["reviewed"] for photo in photos):
            raise HTTPException(422, "Review all photos before starting training.")
        unique = {}
        for photo in photos:
            previous = unique.setdefault(photo["digest"], photo)
            if previous["boxes"] != photo["boxes"]:
                raise HTTPException(422, "Identical photos have different labels. Check the boxes.")
        if len(unique) < 4 or sum(bool(photo["boxes"]) for photo in unique.values()) < 2:
            raise HTTPException(422, "Add at least four different photos, with the part in two.")
        snapshot = {
            "org_id": str(member.org_id),
            "part_name": dataset["part_name"],
            "photos": list(unique.values()),
        }
        job = await session.execute(
            text("""
                INSERT INTO training_jobs (dataset_id, dataset_revision, snapshot)
                VALUES (:id, :revision, CAST(:snapshot AS jsonb))
                RETURNING id, dataset_revision, status, error, created_at, finished_at
            """),
            {
                "id": dataset_id,
                "revision": data.revision,
                "snapshot": json.dumps(snapshot, default=str),
            },
        )
        return TrainingJob.model_validate(dict(job.mappings().one()))


@router.get("/{dataset_id}/jobs/latest")
async def latest_job(dataset_id: UUID, member: OrgMember, response: Response) -> TrainingJob | None:
    response.headers["Cache-Control"] = "no-store"
    async with Session() as session:
        result = await session.execute(
            text("""
                SELECT j.id, j.dataset_revision, j.status, j.error, j.created_at, j.finished_at
                FROM training_jobs j JOIN training_datasets d ON d.id = j.dataset_id
                WHERE d.id = :id AND d.org_id = :org
                ORDER BY j.created_at DESC, j.id DESC LIMIT 1
            """),
            {"id": dataset_id, "org": member.org_id},
        )
        row = result.mappings().one_or_none()
    return TrainingJob.model_validate(dict(row)) if row else None


async def completed_checkpoint(dataset_id: UUID, job_id: UUID, member: OrgMember) -> Path:
    async with Session() as session:
        exists = await session.scalar(
            text("""
                SELECT 1 FROM training_jobs j JOIN training_datasets d ON d.id = j.dataset_id
                WHERE j.id = :job AND d.id = :id AND d.org_id = :org AND j.status = 'succeeded'
            """),
            {"job": job_id, "id": dataset_id, "org": member.org_id},
        )
    directory = os.getenv("VI_TRAINING_RUN_DIR")
    if not exists or not directory:
        raise HTTPException(404, "Trained checkpoint unavailable")
    checkpoint = Path(directory) / str(member.org_id) / str(job_id) / "best.pt"
    if not checkpoint.is_file():
        raise HTTPException(404, "Trained checkpoint unavailable")
    return checkpoint


@router.get("/{dataset_id}/jobs", response_model=list[TrainingJob])
async def completed_jobs(dataset_id: UUID, member: OrgMember, response: Response):
    response.headers["Cache-Control"] = "no-store"
    async with Session() as session:
        result = await session.execute(
            text("""
                SELECT j.id, j.dataset_revision, j.status, j.error, j.created_at, j.finished_at
                FROM training_jobs j JOIN training_datasets d ON d.id = j.dataset_id
                WHERE d.id = :id AND d.org_id = :org AND j.status = 'succeeded'
                ORDER BY j.created_at DESC, j.id DESC
            """),
            {"id": dataset_id, "org": member.org_id},
        )
        return [dict(row) for row in result.mappings()]


@router.get("/{dataset_id}/jobs/{job_id}/checkpoint", response_class=FileResponse)
async def download_checkpoint(dataset_id: UUID, job_id: UUID, member: OrgMember):
    checkpoint = await completed_checkpoint(dataset_id, job_id, member)
    return FileResponse(
        checkpoint,
        filename="best.pt",
        media_type="application/octet-stream",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/{dataset_id}/jobs/{job_id}/preview")
async def test_trained_model(
    dataset_id: UUID,
    job_id: UUID,
    request: Request,
    member: OrgMember,
    settings: SettingsDependency,
    _: BrowserOrigin,
    confidence: Annotated[float, Query(ge=0.01, le=1)] = 0.5,
):
    await completed_checkpoint(dataset_id, job_id, member)
    image = await read_jpeg(request)
    try:
        async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
            result = await client.post(
                f"{settings.inference_url.rstrip('/')}/api/v1/demo/trained-models/"
                f"{member.org_id}/{job_id}/preview",
                params={"confidence": confidence},
                content=image,
                headers={"Content-Type": "image/jpeg"},
            )
            result.raise_for_status()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 422:
            raise HTTPException(422, "The model could not read this photo") from exc
        raise HTTPException(503, "Trained model preview unavailable") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Trained model preview unavailable") from exc
    return Response(
        result.content,
        media_type="application/json",
        headers={"Cache-Control": "no-store"},
    )
