"""Turn saved dashboard annotations into YOLO datasets and train queued jobs."""

import asyncio
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import asyncpg

logger = logging.getLogger(__name__)
WORKER_LOCK = 8700419


def split_photos(photos):
    """Keep a positive example in both splits and balance negatives when possible."""
    train, valid = [], []
    for positive in (True, False):
        group = sorted(
            (photo for photo in photos if bool(photo["boxes"]) == positive),
            key=lambda photo: photo["digest"],
        )
        valid_count = max(1, len(group) // 5) if len(group) >= 2 else 0
        valid.extend(group[:valid_count])
        train.extend(group[valid_count:])
    return {"train": train, "valid": valid}


def make_dataset(root, image_root, job, snapshot):
    """Export one class and YOLO's normalized center/size coordinates."""
    for split, photos in split_photos(snapshot["photos"]).items():
        images = root / split / "images"
        labels = root / split / "labels"
        images.mkdir(parents=True)
        labels.mkdir()
        for photo in photos:
            stem = photo["id"]
            suffix = "jpg" if photo["media_type"] == "image/jpeg" else "png"
            source = (
                image_root
                / snapshot["org_id"]
                / str(job["dataset_id"])
                / stem
                / f"{photo['digest']}.{suffix}"
            )
            shutil.copyfile(source, images / f"{stem}.{suffix}")
            lines = []
            for box in photo["boxes"]:
                a, b = box["start"], box["end"]
                x, y = (a["x"] + b["x"]) / 2, (a["y"] + b["y"]) / 2
                width, height = abs(a["x"] - b["x"]), abs(a["y"] - b["y"])
                lines.append(f"0 {x:.9f} {y:.9f} {width:.9f} {height:.9f}\n")
            (labels / f"{stem}.txt").write_text("".join(lines))
    manifest = root / "data.yaml"
    manifest.write_text(
        json.dumps(
            {
                "path": ".",
                "train": "train/images",
                "val": "valid/images",
                "names": [snapshot["part_name"]],
            }
        )
    )
    return manifest


async def train(job, image_root, run_root, epochs):
    snapshot = json.loads(job["snapshot"])
    output = run_root / snapshot["org_id"] / str(job["id"])
    output.mkdir(parents=True)
    weights_cache = run_root / "pretrained"
    weights_cache.mkdir(exist_ok=True)
    with TemporaryDirectory(prefix="vi-training-") as directory:
        manifest = await asyncio.to_thread(make_dataset, Path(directory), image_root, job, snapshot)
        with (output / "training.log").open("wb") as log:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "vi_inference.train_detector",
                "--data",
                str(manifest),
                "--runs",
                str(output),
                "--epochs",
                str(epochs),
                cwd=weights_cache,
                stdout=log,
                stderr=asyncio.subprocess.STDOUT,
            )
            try:
                async with asyncio.timeout(7200):
                    if await process.wait() != 0:
                        raise RuntimeError("YOLO trainer exited unsuccessfully")
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
        result = output / "object-detection"
        checkpoint = result / "weights" / "best.pt"
        if not checkpoint.is_file() or not checkpoint.stat().st_size:
            raise RuntimeError("YOLO did not produce a checkpoint")
        checkpoint.replace(output / "best.pt")


async def run():
    url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://", 1)
    image_root = Path(os.environ["VI_TRAINING_IMAGE_DIR"]).resolve()
    run_root = Path(os.environ["VI_TRAINING_RUN_DIR"]).resolve()
    epochs = int(os.getenv("VI_TRAINING_EPOCHS", "20"))
    if epochs < 1:
        raise ValueError("VI_TRAINING_EPOCHS must be positive")
    connection = await asyncpg.connect(url)
    try:
        await connection.execute("SELECT pg_advisory_lock($1::bigint)", WORKER_LOCK)
        await connection.execute("""
            UPDATE training_jobs SET status = 'failed', finished_at = now(),
                error = 'The training worker restarted. Start training again.'
            WHERE status = 'running'
        """)
        while True:
            job = await connection.fetchrow("""
                UPDATE training_jobs SET status = 'running', started_at = now()
                WHERE id = (
                    SELECT id FROM training_jobs WHERE status = 'queued'
                    ORDER BY created_at, id LIMIT 1 FOR UPDATE SKIP LOCKED
                ) RETURNING id, dataset_id, snapshot
            """)
            if not job:
                await asyncio.sleep(2)
                continue
            status, error = "succeeded", None
            try:
                await train(job, image_root, run_root, epochs)
            except Exception:
                logger.exception("Training job %s failed", job["id"])
                status = "failed"
                error = "YOLO could not train on these photos. Check the images and try again."
            await connection.execute(
                """
                UPDATE training_jobs SET status = $2, error = $3, finished_at = now()
                WHERE id = $1 AND status = 'running'
            """,
                job["id"],
                status,
                error,
            )
    finally:
        await connection.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run())
