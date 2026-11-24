from fastapi import FastAPI, Request

from vi_api.interfaces.http.controllers import training_jobs  # noqa: F401
from vi_api.interfaces.http.controllers.auth import router as auth_router
from vi_api.interfaces.http.controllers.catalogue import router as catalogue_router
from vi_api.interfaces.http.controllers.demo_examples import router as demo_examples_router
from vi_api.interfaces.http.controllers.health import router as health_router
from vi_api.interfaces.http.controllers.inspection import router as inspection_router
from vi_api.interfaces.http.controllers.training_datasets import router as training_datasets_router
from vi_api.interfaces.http.errors import register_error_handlers

app = FastAPI(title="VI WebSync API", version="0.1.0")
register_error_handlers(app)
app.include_router(health_router)
app.include_router(catalogue_router)
app.include_router(demo_examples_router)
app.include_router(auth_router)
app.include_router(inspection_router)
app.include_router(training_datasets_router)


@app.middleware("http")
async def prevent_auth_response_caching(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/api/v1/auth/"):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
    return response
