from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.app.core.database import get_db
from backend.app.models.models import Job, GPU, GPUMetric, User, Wallet, JobStatus, GPUStatus
from backend.app.schemas.schemas import JobCreate, JobResponse
from backend.app.api.auth import get_current_user
from backend.app.services.scheduler import scheduler
from backend.app.services.agent_manager import agent_manager
from backend.app.services.ml_service import ml_service

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.post("", response_model=JobResponse)
async def submit_job(
    payload: JobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Check user wallet balance
    w_res = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = w_res.scalars().first()
    if not wallet or wallet.balance < 5.0:
        raise HTTPException(status_code=400, detail="Insufficient wallet balance. Please add funds.")

    # 2. Query available candidate GPUs
    g_res = await db.execute(select(GPU))
    all_gpus = g_res.scalars().all()

    candidates = scheduler.filter_candidates(
        gpus=all_gpus,
        min_vram_gb=payload.min_vram_gb,
        preferred_gpu_id=payload.preferred_gpu_id
    )

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail=f"No available GPUs match your minimum requirement ({payload.min_vram_gb} GB VRAM). Please try again shortly."
        )

    # 3. Retrieve latest metrics for candidates
    gpu_metrics_map = {}
    for g in candidates:
        m_data = agent_manager.latest_gpu_telemetry.get(g.id)
        if m_data:
            gpu_metrics_map[g.id] = GPUMetric(
                gpu_id=g.id,
                gpu_utilization=m_data.get("gpu_utilization", 0.0),
                cpu_utilization=m_data.get("cpu_utilization", 0.0),
                ram_used_mb=m_data.get("ram_used_mb", 0.0),
                ram_total_mb=m_data.get("ram_total_mb", 1.0),
                temperature_c=m_data.get("temperature_c", 50.0),
                power_draw_w=m_data.get("power_draw_w", 60.0),
            )
        else:
            m_res = await db.execute(select(GPUMetric).where(GPUMetric.gpu_id == g.id).order_by(desc(GPUMetric.timestamp)).limit(1))
            gpu_metrics_map[g.id] = m_res.scalars().first()

    # 4. Score and rank candidates using selected scheduling strategy
    ranked_candidates = scheduler.evaluate_and_rank(
        candidates=candidates,
        gpu_latest_metrics=gpu_metrics_map,
        workload_spec={
            "expected_runtime_hours": payload.expected_runtime_hours,
            "workload_type": payload.workload_type,
            "framework": payload.framework,
        },
        strategy=payload.scheduling_strategy
    )

    if not ranked_candidates:
        raise HTTPException(status_code=400, detail="Scheduler could not rank candidates.")

    best_match = ranked_candidates[0]
    selected_gpu: GPU = best_match["gpu"]

    # 5. Create Job Record
    job = Job(
        user_id=current_user.id,
        gpu_id=selected_gpu.id,
        title=payload.title,
        workload_type=payload.workload_type,
        framework=payload.framework,
        docker_image=payload.docker_image,
        script_command=payload.script_command,
        min_vram_gb=payload.min_vram_gb,
        expected_runtime_hours=payload.expected_runtime_hours,
        budget_max=payload.budget_max,
        priority=payload.priority,
        scheduling_strategy=payload.scheduling_strategy,
        predicted_availability=best_match["p_avail"],
        predicted_runtime_hours=best_match["pred_runtime_hours"],
        predicted_cost=best_match["est_cost"],
        scheduler_score=best_match["score"],
        status=JobStatus.RESERVED,
        logs=f"[AI-Scheduler] Workload assigned to {selected_gpu.gpu_name} (Score: {best_match['score']}, Pred Avail: {round(best_match['p_avail']*100, 1)}%, Pred Cost: INR {best_match['est_cost']})\n"
    )
    
    # Mark GPU reserved
    selected_gpu.status = GPUStatus.RESERVED
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # 6. Dispatch START_JOB command to Agent if connected via WebSocket
    command_payload = {
        "action": "START_JOB",
        "job_id": job.id,
        "gpu_id": selected_gpu.id,
        "docker_image": job.docker_image,
        "script_command": job.script_command,
        "workload_type": job.workload_type,
        "timeout_seconds": int(payload.expected_runtime_hours * 3600 + 300)
    }

    dispatched = await agent_manager.send_command_to_agent(selected_gpu.id, command_payload)
    if not dispatched:
        job.logs += f"[System Warning] Agent not directly reachable via WebSocket. Queued for agent polling.\n"
        job.status = JobStatus.QUEUED
        await db.commit()

    return JobResponse(
        id=job.id,
        user_id=job.user_id,
        gpu_id=job.gpu_id,
        title=job.title,
        workload_type=job.workload_type,
        framework=job.framework,
        docker_image=job.docker_image,
        script_command=job.script_command,
        min_vram_gb=job.min_vram_gb,
        expected_runtime_hours=job.expected_runtime_hours,
        budget_max=job.budget_max,
        priority=job.priority,
        scheduling_strategy=job.scheduling_strategy,
        predicted_availability=job.predicted_availability,
        predicted_runtime_hours=job.predicted_runtime_hours,
        predicted_cost=job.predicted_cost,
        scheduler_score=job.scheduler_score,
        status=job.status,
        actual_start_time=job.actual_start_time,
        actual_end_time=job.actual_end_time,
        actual_runtime_seconds=job.actual_runtime_seconds,
        cost_charged=job.cost_charged,
        provider_earned=job.provider_earned,
        logs=job.logs,
        exit_code=job.exit_code,
        created_at=job.created_at,
        gpu_name=selected_gpu.gpu_name
    )

@router.get("", response_model=List[JobResponse])
async def list_user_jobs(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(Job, GPU.gpu_name).outerjoin(GPU, Job.gpu_id == GPU.id).where(Job.user_id == current_user.id)
    if status:
        query = query.where(Job.status == status.upper())
    result = await db.execute(query.order_by(desc(Job.created_at)))
    rows = result.all()

    resp = []
    for job, gpu_name in rows:
        resp.append(JobResponse(
            id=job.id,
            user_id=job.user_id,
            gpu_id=job.gpu_id,
            title=job.title,
            workload_type=job.workload_type,
            framework=job.framework,
            docker_image=job.docker_image,
            script_command=job.script_command,
            min_vram_gb=job.min_vram_gb,
            expected_runtime_hours=job.expected_runtime_hours,
            budget_max=job.budget_max,
            priority=job.priority,
            scheduling_strategy=job.scheduling_strategy,
            predicted_availability=job.predicted_availability,
            predicted_runtime_hours=job.predicted_runtime_hours,
            predicted_cost=job.predicted_cost,
            scheduler_score=job.scheduler_score,
            status=job.status,
            actual_start_time=job.actual_start_time,
            actual_end_time=job.actual_end_time,
            actual_runtime_seconds=job.actual_runtime_seconds,
            cost_charged=job.cost_charged,
            provider_earned=job.provider_earned,
            logs=job.logs,
            exit_code=job.exit_code,
            created_at=job.created_at,
            gpu_name=gpu_name or "Unassigned"
        ))
    return resp

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Job, GPU.gpu_name).outerjoin(GPU, Job.gpu_id == GPU.id).where(Job.id == job_id))
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Job not found")

    job, gpu_name = row
    return JobResponse(
        id=job.id,
        user_id=job.user_id,
        gpu_id=job.gpu_id,
        title=job.title,
        workload_type=job.workload_type,
        framework=job.framework,
        docker_image=job.docker_image,
        script_command=job.script_command,
        min_vram_gb=job.min_vram_gb,
        expected_runtime_hours=job.expected_runtime_hours,
        budget_max=job.budget_max,
        priority=job.priority,
        scheduling_strategy=job.scheduling_strategy,
        predicted_availability=job.predicted_availability,
        predicted_runtime_hours=job.predicted_runtime_hours,
        predicted_cost=job.predicted_cost,
        scheduler_score=job.scheduler_score,
        status=job.status,
        actual_start_time=job.actual_start_time,
        actual_end_time=job.actual_end_time,
        actual_runtime_seconds=job.actual_runtime_seconds,
        cost_charged=job.cost_charged,
        provider_earned=job.provider_earned,
        logs=job.logs,
        exit_code=job.exit_code,
        created_at=job.created_at,
        gpu_name=gpu_name or "Unassigned"
    )

@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Job).where(Job.id == job_id, Job.user_id == current_user.id))
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
        return {"status": "already_terminated", "job_status": job.status}

    job.status = JobStatus.CANCELLED
    job.actual_end_time = datetime.utcnow()
    
    if job.gpu_id:
        g_res = await db.execute(select(GPU).where(GPU.id == job.gpu_id))
        gpu = g_res.scalars().first()
        if gpu:
            gpu.status = GPUStatus.AVAILABLE
            await agent_manager.send_command_to_agent(gpu.id, {"action": "CANCEL_JOB", "job_id": job.id})

    await db.commit()
    return {"message": "Job cancelled successfully", "job_id": job_id}
