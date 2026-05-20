import json
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import verify_token, get_redis
from app.schemas.input import StatusResponse, JOB_STATUS_KEY

router = APIRouter(prefix="/status", tags=["status"])


@router.get(
    "/{job_id}",
    response_model=StatusResponse,
    summary="Consulta estado do processamento",
)
async def get_status(
    job_id: str,
    token: dict = Depends(verify_token),
    redis=Depends(get_redis),
):
    status_raw = redis.get(JOB_STATUS_KEY.format(job_id=job_id))
    if not status_raw:
        raise HTTPException(status_code=404, detail="Job nao encontrado ou expirado")

    status_data = json.loads(status_raw)
    return StatusResponse(**status_data)
