# AI inference backend

Owner: Akash. Compose service: `ai-api`; host command: `make inference`.
`GET /health/live` reports the process and zero loaded packages.
`POST /api/v1/predict` returns 503 `model_not_loaded`. No trained model is bundled.

The AI runtime is independent of business API access/approval logic. See
`docs/guides/AI_LIFECYCLE.md` for plugin contracts, training/evaluation, packaging and
integration. Keep future GPU dependencies in a separate AI image. Model unavailability
must never become a successful inspection or permit PASS.
