# VI WebSync local stack

This repository contains the business API and worker, PostgreSQL migrations,
and inference service in `backend/`, `database/`, and `inference/`.
The React dashboard remains in the separate `viweb-frontend` repository.

## Start the stack

From this folder, run one command.

```bash
docker compose up -d --build --wait
```

Compose builds the local source, waits for PostgreSQL, applies the schema, and
starts Redis, the API, the worker, and inference. The only published port is API
port 8000 on loopback. The migration job exits after applying the schema. The
database and saved images persist across restarts.

In the separate frontend repository, use Node 22 and run `npm ci` on the first
run, then `npm run dev`. Open **http://127.0.0.1:3000**. Choose **Create an
account** and enter a workspace name, email, and password to open Inspection. Use
this exact frontend address because the API checks the browser origin.

## Turn on YOLO or Qwen

The default startup runs the inference API so you can use signup, camera
preview, and capture without downloading model dependencies. Inspection
returns HOLD until its model is available.

For YOLO, copy your trained checkpoint to `models/best.pt` and run:

```bash
INFERENCE_TARGET=yolo docker compose up -d --build --wait
```

For repeat YOLO starts, put `INFERENCE_TARGET=yolo` in this repository's
local `.env`. For Qwen, start the vision profile and download the model once:

```bash
docker compose --profile vision up -d --build --wait
docker compose exec ollama ollama pull qwen2.5vl:3b
```

## Stop or check status

```bash
docker compose ps -a
docker compose logs api migrate inference
docker compose down
```

This is a loopback-only development stack. The copied source trees are
independent of the original repositories. Make local-stack changes in this
repository or port shared changes back to the applicable upstream explicitly.

## Prepare a dataset and train

1. Capture full frames from the line and create a private Object Detection
   dataset in JTheta.ai. Add the classes you want to detect. Review the
   automatic bounding boxes and export the annotations in YOLO detection format.
2. Extract the export under `datasets/`. Keep the image and label directories
   from the export, and place `data.yaml` at `datasets/data.yaml`. Set
   `path: .` in that file and use relative image directories for `train`,
   `val`, and the optional `test` split. Keep related production frames in
   the same split. A typical export uses `train/images`, `valid/images`,
   and `test/images` with a sibling `labels` directory for each split.
3. From this repository, run:

   ```bash
   docker compose --profile training run --build --rm trainer
   ```

   The CPU trainer fine-tunes a pretrained YOLO11n detector using Ultralytics
   and PyTorch. It mounts the dataset read-only and writes checkpoints and
   metrics to `runs/`. The first run downloads model dependencies and the
   pretrained checkpoint. Use `--epochs 1` at the end of the command for a
   quick pipeline check. If given a test split, training also evaluates the
   selected checkpoint on that split.
4. Review the printed run directory, especially `results.csv`, validation
   charts, and held-out results if present. Once the checkpoint is approved,
   replace `runs/object-detection` with that actual run directory below:

   ```bash
   cp runs/object-detection/weights/best.pt models/best.pt
   INFERENCE_TARGET=yolo docker compose up -d --build --wait
   docker compose restart inference
   ```

5. Open the dashboard's **Dataset & models** guide or go directly to
   **Inspection**. Click **Refresh model** after deploying weights. Choose
   a trained class, expected count, and a confidence threshold validated on
   your own frames. Start the camera or share its vendor viewer, then
   select **Capture & detect**. Check the decision, green boxes, and part
   crops. Use **Overview** for recent results from the current session.

## Work in separate repositories

Docker Compose can use either the copies committed here or independent
checkouts. Open the backend, database, inference, and frontend folders in
separate VS Code windows if preferred. Keep this repository as the Compose
entry point and add the following to its local `.env` (absolute paths also
work):

```dotenv
BACKEND_CONTEXT=../viweb-ai
DATABASE_CONTEXT=../viweb-db
INFERENCE_CONTEXT=../viweb-inference
```

Use the `inspection-onboarding` branch in `viweb-ai` and the matching
revisions of the other repositories. With current checkouts, startup is
still `docker compose up -d --build --wait` here and `npm run dev` in
`viweb-frontend`. Frontend installation uses `npm ci` once per checkout.

## First camera test from separate GitHub repositories

Install Git, Docker with Compose, and Node.js 22. Run on the computer connected
to the camera. Clone the repositories side by side:

```bash
mkdir viweb-workspace
cd viweb-workspace
git clone https://github.com/viweb25/viweb-local-stack.git
git clone --branch inspection-onboarding https://github.com/viweb25/viweb-ai.git
git clone https://github.com/viweb25/viweb-db.git
git clone https://github.com/viweb25/viweb-inference.git
git clone https://github.com/viweb25/viweb-frontend.git
```

From `viweb-local-stack`, start everything except the frontend with one command:

```bash
docker compose -f compose.yaml -f compose.separate.yaml up -d --build --wait
```

The override uses the sibling backend, database, and inference repositories.
On first run it builds the CPU YOLO image, downloads a starter detector, and
keeps it in a Docker volume. It uses `models/best.pt` when that file is present.

In a second terminal, open `viweb-frontend` and run:

```bash
npm ci && npm run dev
```

Open **http://127.0.0.1:3000**, create an account, and choose **Sample inspection**.
Select and start the camera if the browser lists it. Otherwise open the
manufacturer's camera viewer, start live video, and choose **Share camera window**
in VI WebSync. Choose **Count parts**, then click **Use person demo** to select `person` and
an expected count of `1`. Put one person in view and click **Capture & check**. Green boxes show
detections. The photo border is green when the count matches and red when it
differs. A saved JPEG works with **Upload image** and **Check this photo**.

For a factory part, copy your reviewed, trusted checkpoint to `models/best.pt`
and switch inference to it:

```bash
docker compose -f compose.yaml -f compose.separate.yaml restart inference
```

Click **Refresh model** in the dashboard and select a class from that checkpoint.
Industrial cameras that only work through their vendor software use the window
sharing path for this workflow. Exact SDK integration depends on the camera model.

## Train your own detector

Start with fine-tuning to learn factory-specific classes from your own camera
images. The trainer starts from Ultralytics' COCO-trained YOLO11n weights and
learns the classes from your bounding-box labels. Example photos saved as
PASS or FAIL in the dashboard have image-level labels. The detector needs a
class and a bounding box for each visible part.

For example, if the export has `train/images`, `valid/images`, and
`test/images` folders, its `datasets/data.yaml` for one part class can look
like this:

```yaml
path: .
train: train/images
val: valid/images
test: test/images
names:
  0: cap
```

Keep the sibling `labels` directory for each split and use the class IDs from
your export. Omit `test` if your export has only training and validation splits.

For the sibling repositories, run the trainer from `viweb-local-stack`:

```bash
docker compose -f compose.yaml -f compose.separate.yaml --profile training run --build --rm trainer
```

Add `--epochs 1` to verify the pipeline or `--from-scratch` to start with
randomly initialized weights. Both modes use the YOLO11n architecture and
produce a deployable `weights/best.pt`. Training from scratch typically needs
more labeled data and compute. Compare both approaches on the same held-out
production batches before choosing a model. Measure missed parts, extra
detections, incorrect pass/fail decisions, and inference time at the station.

A proprietary architecture would be a separate development effort. Use the
fine-tuned detector as a baseline, then use its measured failure cases and
latency to define what a new design should improve.

## Analyze a photo with YOLO and Qwen

From `viweb-local-stack`, with the sibling repositories available:

```bash
docker compose -f compose.yaml -f compose.separate.yaml --profile vision up -d --build --wait
docker compose -f compose.yaml -f compose.separate.yaml --profile vision exec ollama ollama pull qwen2.5vl:3b
```

In **Check parts**, set **Check type** to **Analyze image**. Upload a photo
to analyze it, or start a camera and click **Capture & analyze**. YOLO draws boxes and groups counts by class. Qwen provides a scene
description. This mode reports observations without applying a pass/fail rule.

The starter YOLO checkpoint recognizes its COCO classes, including people and
cars. To return a factory class such as `cap`, load a checkpoint trained with
that class. A custom checkpoint lists the classes it was trained to detect.

[Hugging Face hosts the Qwen model card and original weights](https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct).
The local stack runs Qwen through Ollama and sends photos only to the local
services.

## Saved training datasets

In the dashboard, open **Models → Train a model**, name one part, and add JPEG or PNG
photos in one or more batches. Use the gallery to draw boxes around the part
or confirm that a photo has none. Click **Save draft** at any point and
reopen the dataset to continue. Each dataset supports up to 200 photos of
5 MiB each.

Migration `0006` adds organisation-owned `training_datasets` and their
`training_photos`. PostgreSQL stores photo metadata, normalized box coordinates,
review status, and the dataset revision. The API stores photo files in the
private volume at `VI_TRAINING_IMAGE_DIR` and checks organisation membership
before delivering them. Keep that directory on durable storage. Uploaded files
from abandoned saves may remain in the directory. Cloud object storage is
a separate deployment step.

### Train from the dashboard

Start the updated API and training worker from this directory:

```bash
docker compose -f compose.yaml -f compose.separate.yaml --profile vision up -d --build --wait api training-worker
```

Save at least four different reviewed photos, including two with the target
part, then choose **Save and train** to submit the whole set. Four photos
enable a pipeline check. Use a
broader set of production examples to evaluate model quality. The worker
snapshots the saved revision, holds some photos back for validation, converts
the drawn boxes into YOLO detection labels, and fine-tunes pretrained YOLO11n.
It runs 20 CPU epochs by default. Set `VI_TRAINING_EPOCHS` for local testing.

The dashboard shows queued, training, completed, or failed. A completed job
appears in **Models → Test a model** for the selected photo set. Select a
completed run, add a fresh photo, and click **Run test** to see its
detections. You can also download the selected `best.pt`. The training
runs volume stores the checkpoint and trainer output. Production activation
is a subsequent step.
