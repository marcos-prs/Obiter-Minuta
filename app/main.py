import logging
import structlog
import sentry_sdk
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import get_settings
from app.routers import ingest, status, result, job
from app.redis_pool import disconnect_pool


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            traces_sample_rate=0.1,
            environment=settings.app_env,
        )

    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level)
        ),
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
    )

    yield

    disconnect_pool()


settings = get_settings()

app = FastAPI(
    title="ObiterJus - API de Minutas",
    version=settings.api_version,
    description="API intermediaria para processamento de pecas juridicas via IA",
    lifespan=lifespan,
)

app.include_router(ingest.router)
app.include_router(status.router)
app.include_router(result.router)
app.include_router(job.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.api_version}
