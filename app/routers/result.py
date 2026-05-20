import json
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import verify_token, get_redis
from app.schemas.input import JOB_RESULT_KEY
from app.schemas.output import MinutaPackage

router = APIRouter(prefix="/result", tags=["result"])


@router.get(
    "/{job_id}",
    response_model=MinutaPackage,
    summary="Retorna pacote estruturado",
)
async def get_result(
    job_id: str,
    token: dict = Depends(verify_token),
    redis=Depends(get_redis),
):
    result_raw = redis.get(JOB_RESULT_KEY.format(job_id=job_id))
    if not result_raw:
        raise HTTPException(
            status_code=404,
            detail="Resultado nao encontrado. Job expirado ou ainda em processamento.",
        )

    redis.delete(JOB_RESULT_KEY.format(job_id=job_id))
    result_data = json.loads(result_raw)
    return MinutaPackage(**result_data)
