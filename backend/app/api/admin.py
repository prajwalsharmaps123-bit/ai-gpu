from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from backend.app.core.database import get_db
from backend.app.models.models import User, GPU, Job, Wallet, GPUStatus, JobStatus
from backend.app.api.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/stats")
async def get_cluster_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Total counts
    user_count = await db.scalar(select(func.count(User.id)))
    gpu_count = await db.scalar(select(func.count(GPU.id)))
    online_gpus = await db.scalar(select(func.count(GPU.id)).where(GPU.status.in_([GPUStatus.AVAILABLE, GPUStatus.BUSY, GPUStatus.RESERVED])))
    job_count = await db.scalar(select(func.count(Job.id)))
    running_jobs = await db.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.RUNNING))
    completed_jobs = await db.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.COMPLETED))
    failed_jobs = await db.scalar(select(func.count(Job.id)).where(Job.status == JobStatus.FAILED))
    total_revenue = await db.scalar(select(func.sum(Job.cost_charged))) or 0.0

    return {
        "total_users": user_count,
        "total_gpus": gpu_count,
        "online_gpus": online_gpus,
        "total_jobs": job_count,
        "running_jobs": running_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "total_revenue": round(total_revenue, 2),
    }

@router.post("/gpus/{gpu_id}/reset")
async def force_reset_gpu(
    gpu_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(GPU).where(GPU.id == gpu_id))
    gpu = res.scalars().first()
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")

    gpu.status = GPUStatus.AVAILABLE
    await db.commit()
    return {"message": f"GPU {gpu.gpu_name} reset to AVAILABLE status"}
