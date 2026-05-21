"""Operações de escrita no banco — usadas pelo worker Celery."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.models import JobRecord, AuditLog


def create_job(db: Session, job_id: str, tipo_declarado: str,
               numero_processo: str | None, vara: str | None,
               origem: str | None, hash_arquivo: str) -> None:
    record = JobRecord(
        job_id=job_id,
        status="queued",
        tipo_declarado=tipo_declarado,
        numero_processo=numero_processo,
        vara=vara,
        origem=origem,
        hash_arquivo=hash_arquivo,
    )
    db.add(record)
    db.commit()


def update_job_completed(db: Session, job_id: str, tipo_detectado: str,
                         tipo_confirmado: bool, paginas: int,
                         confianca_geral: float, requer_revisao: bool,
                         modelo_ia: str) -> None:
    record = db.query(JobRecord).filter_by(job_id=job_id).first()
    if record:
        record.status = "completed"
        record.tipo_detectado = tipo_detectado
        record.tipo_confirmado = tipo_confirmado
        record.paginas = paginas
        record.confianca_geral = confianca_geral
        record.requer_revisao = requer_revisao
        record.modelo_ia = modelo_ia
        record.completado_em = datetime.now(timezone.utc)
        db.commit()


def update_job_failed(db: Session, job_id: str, erro: str) -> None:
    record = db.query(JobRecord).filter_by(job_id=job_id).first()
    if record:
        record.status = "failed"
        record.erro = erro
        record.completado_em = datetime.now(timezone.utc)
        db.commit()


def append_audit(db: Session, job_id: str, event: str,
                 details: dict | None = None) -> None:
    log = AuditLog(job_id=job_id, event=event, details=details)
    db.add(log)
    db.commit()
