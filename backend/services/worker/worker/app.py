from celery import Celery
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    redis_url: str = "redis://127.0.0.1:16379/0"


app = Celery("vi_websync", broker=Settings().redis_url)
app.conf.update(
    task_default_queue="platform",
    task_routes={"vi.health.ping": {"queue": "platform"}},
    broker_connection_retry_on_startup=True,
    broker_transport_options={"visibility_timeout": 3600},
    task_soft_time_limit=30,
    task_time_limit=60,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_ignore_result=True,
    worker_prefetch_multiplier=1,
)


@app.task(name="vi.health.ping")
def ping():
    """Infrastructure smoke task only; no training or customer data access."""
    return {"status": "ok", "service": "worker"}
