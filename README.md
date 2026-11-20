# VI WebSync local stack

This repository contains the business API and worker, PostgreSQL migrations,
and inference service in `backend/`, `database/`, and `inference/`.
The React dashboard remains in the separate `viweb-frontend` repository.

## Start the stack

From this folder, run one command.

```bash
docker compose up -d --build --wait
```

Compose builds the local source, waits for PostgreSQL, applies the schema,
creates a private signup code, and starts Redis, the API, the worker, and
inference. The only published port is the API at `127.0.0.1:8000`. The
`migrate` and `signup-code` containers exit successfully once their jobs
finish. The database, signup code, and saved images persist across restarts.

Get the signup code for your first account.

```bash
docker compose exec -T api cat /run/viweb-signup/code
```

In the separate frontend repository, use Node 22 and run `npm ci` on the
first run, then `npm run dev`. Open **http://127.0.0.1:3000**. The frontend
already proxies requests to port 8000. Select **Create an account**, use the
signup code, then sign in and open the camera station. Use this exact frontend
address because the API checks the browser origin.

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
