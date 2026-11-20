# VI WebSync inference and training

This repository owns the private inference HTTP service, AI function interfaces,
and factory edge code. It includes the existing Ollama demo adapter. Dedicated
model training and packaging remain planned.

```bash
docker build -t vi-websync/inference:staging .
```

The backend stack runs this image on its private Docker network. It can reach
Ollama there when the vision profile is enabled. Review the contract at
packages/schemas/openapi/inference.json when changing inference endpoints.

## Local object detection pilot

1. In a private JTheta.ai workspace, create an Object Detection dataset such as
   `line-01-part-detection-v1`. Upload full industrial-camera frames. Define the
   object classes, enable AI-assisted pre-labeling where available, and review every
   bounding box before exporting in YOLO detection format.
2. Keep frames from the same capture session or production batch in the same split.
   Check that `data.yaml` points to the training and validation images and maps the
   numeric label IDs to the correct class names.
3. In a Python environment with Ultralytics installed, train a small detector and
   evaluate it on held-out camera frames.

   ```bash
   yolo detect train model=yolo11n.pt data=/absolute/path/to/data.yaml
   ```

4. Start the private inference service with the resulting `best.pt` from your own
   training run. Load checkpoints only from a trusted source. Keep them out of Git.

   ```bash
   VI_YOLO_WEIGHTS=/absolute/path/to/best.pt \
   PYTHONPATH=services/inference:packages/core \
   uv run --with ultralytics uvicorn vi_inference.main:app --port 8001
   ```

5. Start the standalone frontend with Vite. On its inspection screen, select
   **YOLO object count**, enter an exact class from `data.yaml` and the expected
   count, then upload a frame, capture a browser-visible camera, or share the
   camera vendor's viewer. Qwen remains available for text-rule inspections.

   ```bash
   curl -sS -X POST -H 'Content-Type: image/jpeg' --data-binary @frame.jpg \
     'http://127.0.0.1:8001/api/v1/demo/detect?target=cap&expected_count=6'
   ```

The detector returns normalized bounding boxes for the dashboard overlay.
A count match yields PASS, a count mismatch yields FAIL, and a missing model
or processing error yields HOLD. The threshold defaults to 0.5. Validate the
threshold on your own camera data. A count check alone cannot identify an empty
slot or verify placement.

The Vite proxy forwards inspection calls through the business backend. For local
development, run the backend with migrated PostgreSQL, a signup code or an
existing account, and `INFERENCE_URL=http://127.0.0.1:8001`. For Docker deployment,
build the `yolo` target and see the backend setup instructions. Direct
industrial-camera triggering and physical lamp integration require the camera
and controller interfaces.
