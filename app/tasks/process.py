import base64
import json
import redis
from datetime import datetime, timezone
from celery import Celery
from app.config import get_settings
from app.schemas.input import JOB_STATUS_KEY, JOB_RESULT_KEY, JOB_PDF_KEY
from app.services.converter import convert_pdf_to_markdown, CONVERTER_VERSION
from app.services.semantic import analyze_semantic
from app.services.validator import validate_and_enrich
from app.services.packager import package_result_json
from app.utils.audit import (
    compute_file_hash,
    log_pdf_discarded,
    log_job_completed,
    log_job_failed,
)

settings = get_settings()

celery_app = Celery(
    "obiter_minuta",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
)

redis_client = redis.from_url(settings.redis_url, decode_responses=True)


@celery_app.task(bind=True, name="process_document")
def process_document(
    self,
    job_id: str,
    tipo_declarado: str,
    numero_processo: str | None = None,
    vara: str | None = None,
    origem: str | None = None,
) -> dict:
    # Lê PDF do Redis e o remove imediatamente — garante descarte controlado com TTL
    pdf_b64 = redis_client.get(JOB_PDF_KEY.format(job_id=job_id))
    if not pdf_b64:
        _set_status(job_id, "failed")
        raise ValueError(f"PDF expirado ou nao encontrado para job {job_id}")

    redis_client.delete(JOB_PDF_KEY.format(job_id=job_id))
    pdf_bytes = base64.b64decode(pdf_b64)
    file_hash = compute_file_hash(pdf_bytes)

    try:
        self.update_state(
            state="PROGRESS",
            meta={"job_id": job_id, "stage": "conversion", "progress_pct": 10},
        )
        _update_stage(job_id, "conversion", 10)

        markdown, page_count = convert_pdf_to_markdown(pdf_bytes)

        # Fix 3 — aplica limite de páginas
        if page_count > settings.max_pages:
            raise ValueError(
                f"Documento com {page_count} paginas excede o limite de {settings.max_pages}"
            )

        self.update_state(
            state="PROGRESS",
            meta={"job_id": job_id, "stage": "semantic_analysis", "progress_pct": 40},
        )
        _update_stage(job_id, "semantic_analysis", 40)

        semantic_result = analyze_semantic(
            markdown=markdown,
            tipo_declarado=tipo_declarado,
            numero_processo=numero_processo,
            vara=vara,
            origem=origem,
        )

        self.update_state(
            state="PROGRESS",
            meta={"job_id": job_id, "stage": "validation", "progress_pct": 75},
        )
        _update_stage(job_id, "validation", 75)

        minuta = validate_and_enrich(
            semantic_result=semantic_result,
            job_id=job_id,
            markdown=markdown,
            page_count=page_count,
            tipo_declarado=tipo_declarado,
            numero_processo=numero_processo,
            vara=vara,
            origem=origem,
            file_hash=file_hash,
            modelo_ia=settings.gemini_model,
        )

        self.update_state(
            state="PROGRESS",
            meta={"job_id": job_id, "stage": "packaging", "progress_pct": 90},
        )
        _update_stage(job_id, "packaging", 90)

        result_json = package_result_json(minuta)
        result_ttl = settings.result_ttl_hours * 3600
        redis_client.setex(JOB_RESULT_KEY.format(job_id=job_id), result_ttl, result_json)

        log_pdf_discarded(job_id)

        _update_stage(job_id, "done", 100)
        _set_status(job_id, "completed")

        log_job_completed(job_id, settings.gemini_model, CONVERTER_VERSION)

        return {"job_id": job_id, "status": "completed"}

    except Exception as e:
        _set_status(job_id, "failed")
        log_job_failed(job_id, str(e))
        raise


def _update_stage(job_id: str, stage: str, progress: int):
    status_raw = redis_client.get(JOB_STATUS_KEY.format(job_id=job_id))
    if status_raw:
        existing = json.loads(status_raw)
        created_at = existing.get("created_at", datetime.now(timezone.utc).isoformat())
    else:
        created_at = datetime.now(timezone.utc).isoformat()

    status_data = {
        "job_id": job_id,
        "status": "processing",
        "stage": stage,
        "progress_pct": progress,
        "created_at": created_at,
    }
    ttl = settings.job_ttl_minutes * 60
    redis_client.setex(
        JOB_STATUS_KEY.format(job_id=job_id),
        ttl,
        json.dumps(status_data),
    )


def _set_status(job_id: str, status: str):
    status_raw = redis_client.get(JOB_STATUS_KEY.format(job_id=job_id))
    if status_raw:
        existing = json.loads(status_raw)
        created_at = existing.get("created_at", datetime.now(timezone.utc).isoformat())
    else:
        created_at = datetime.now(timezone.utc).isoformat()

    status_data = {
        "job_id": job_id,
        "status": status,
        "stage": "done" if status == "completed" else None,
        "progress_pct": 100 if status == "completed" else 0,
        "created_at": created_at,
    }
    ttl = settings.job_ttl_minutes * 60
    redis_client.setex(
        JOB_STATUS_KEY.format(job_id=job_id),
        ttl,
        json.dumps(status_data),
    )
