from enum import Enum
from pydantic import BaseModel, Field


class TipoPeca(str, Enum):
    inicial = "inicial"
    contestacao = "contestacao"
    tutela = "tutela"
    replica = "replica"
    recurso = "recurso"
    outro = "outro"


class IngestRequest(BaseModel):
    tipo_declarado: TipoPeca
    numero_processo: str | None = None
    vara: str | None = None
    origem: str | None = None


class IngestResponse(BaseModel):
    job_id: str
    status: str
    estimated_seconds: int = 30


class StatusResponse(BaseModel):
    job_id: str
    status: str
    stage: str | None = None
    progress_pct: int = 0
    created_at: str


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class JobStage(str, Enum):
    conversion = "conversion"
    semantic_analysis = "semantic_analysis"
    validation = "validation"
    packaging = "packaging"
    done = "done"


JOB_STATUS_KEY = "job:{job_id}:status"
JOB_RESULT_KEY = "job:{job_id}:result"
JOB_PDF_KEY = "job:{job_id}:pdf"
