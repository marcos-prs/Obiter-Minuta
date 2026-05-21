from datetime import datetime, timezone
from sqlalchemy import String, Float, Boolean, Integer, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.engine import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class JobRecord(Base):
    """Histórico persistente de jobs — sobrevive ao TTL do Redis."""

    __tablename__ = "job_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    tipo_declarado: Mapped[str] = mapped_column(String(32), nullable=False)
    tipo_detectado: Mapped[str | None] = mapped_column(String(32), nullable=True)
    tipo_confirmado: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    numero_processo: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vara: Mapped[str | None] = mapped_column(String(128), nullable=True)
    origem: Mapped[str | None] = mapped_column(String(128), nullable=True)
    paginas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confianca_geral: Mapped[float | None] = mapped_column(Float, nullable=True)
    requer_revisao: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    modelo_ia: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hash_arquivo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLog(Base):
    """Trilha de auditoria imutável — um registro por evento do job."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
