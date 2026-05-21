import hashlib
import structlog
from datetime import datetime, timezone

logger = structlog.get_logger()


def compute_file_hash(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def log_audit_event(
    job_id: str,
    event: str,
    details: dict | None = None,
) -> None:
    logger.info(
        event,  # primeiro arg = event no structlog; não repetir como kwarg
        job_id=job_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        **(details or {}),
    )


def log_pdf_discarded(job_id: str) -> None:
    log_audit_event(job_id, "pdf_discarded", {"pdf_descartado": True})


def log_job_created(job_id: str, tipo_declarado: str, origem: str | None) -> None:
    log_audit_event(
        job_id,
        "job_created",
        {"tipo_declarado": tipo_declarado, "origem": origem},
    )


def log_job_completed(job_id: str, modelo_ia: str, versao_conversor: str) -> None:
    log_audit_event(
        job_id,
        "job_completed",
        {"modelo_ia": modelo_ia, "versao_conversor": versao_conversor},
    )


def log_job_failed(job_id: str, error: str) -> None:
    log_audit_event(job_id, "job_failed", {"error": error})
