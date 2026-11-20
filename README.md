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
