from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import verify_token, get_redis
from app.schemas.input import JOB_STATUS_KEY, JOB_RESULT_KEY

router = APIRouter(prefix="/job", tags=["job"])


@router.delete(
    "/{job_id}",
    summary="Descarte explicito antecipado do job",
)
async def delete_job(
    job_id: str,
    token: dict = Depends(verify_token),
    redis=Depends(get_redis),
):
    keys_deleted = 0
    keys_deleted += redis.delete(JOB_RESULT_KEY.format(job_id=job_id))
    keys_deleted += redis.delete(JOB_STATUS_KEY.format(job_id=job_id))

    if keys_deleted == 0:
        raise HTTPException(status_code=404, detail="Job nao encontrado")

    return {"job_id": job_id, "discarded": True, "keys_deleted": keys_deleted}
