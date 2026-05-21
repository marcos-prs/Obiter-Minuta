import base64
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from app.dependencies import verify_token, get_redis
from app.schemas.input import TipoPeca, IngestResponse, JOB_STATUS_KEY, JOB_PDF_KEY
from app.tasks.process import process_document
from app.utils.audit import log_job_created
from app.config import get_settings, Settings

router = APIRouter(prefix="/ingest", tags=["ingest"])


@router.post(
    "",
    response_model=IngestResponse,
    status_code=202,
    summary="Ingestao de peca juridica",
)
async def ingest_document(
    file: UploadFile = File(...),
    tipo_declarado: TipoPeca = Form(...),
    numero_processo: str | None = Form(None),
    vara: str | None = Form(None),
    origem: str | None = Form(None),
    token: dict = Depends(verify_token),
    redis=Depends(get_redis),
    settings: Settings = Depends(get_settings),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF sao aceitos")

    content = await file.read()
    max_bytes = settings.max_pdf_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo excede o limite de {settings.max_pdf_size_mb}MB",
        )

    job_id = f"j_{uuid.uuid4().hex[:12]}"

    ttl = settings.job_ttl_minutes * 60

    # PDF salvo no Redis como base64 com TTL controlado — nunca vai para args do Celery
    pdf_b64 = base64.b64encode(content).decode()
    redis.setex(JOB_PDF_KEY.format(job_id=job_id), ttl, pdf_b64)

    status_data = {
        "job_id": job_id,
        "status": "queued",
        "stage": None,
        "progress_pct": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    redis.setex(JOB_STATUS_KEY.format(job_id=job_id), ttl, json.dumps(status_data))

    process_document.apply_async(
        args=[job_id, tipo_declarado.value, numero_processo, vara, origem],
        task_id=job_id,
        expires=ttl,  # expira a task se o worker não pegar dentro do TTL do PDF
    )

    log_job_created(job_id, tipo_declarado.value, origem)

    return IngestResponse(
        job_id=job_id,
        status="queued",
        estimated_seconds=30,
    )
