import secrets
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.app.core.database import get_db
from backend.app.models.models import GPU, GPUMetric, GPUStatus, User, UserRole
from backend.app.schemas.schemas import GPURegister, GPUResponse, SSHConnectionInfoResponse, SSHConfigUpdateRequest
from backend.app.api.auth import get_current_user
from backend.app.services.agent_manager import agent_manager

router = APIRouter(prefix="/gpus", tags=["GPUs"])

@router.get("", response_model=List[GPUResponse])
async def list_gpus(
    status: Optional[str] = None,
    min_vram: Optional[float] = None,
    max_price: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(GPU)
    if status:
        query = query.where(GPU.status == status.upper())
    if min_vram is not None:
        query = query.where(GPU.vram_gb >= min_vram)
    if max_price is not None:
        query = query.where(GPU.price_per_hour <= max_price)
        
    result = await db.execute(query.order_by(desc(GPU.reliability_score)))
    gpus = result.scalars().all()

    response_items = []
    for g in gpus:
        # Check latest telemetry from agent memory or DB
        metric_data = agent_manager.latest_gpu_telemetry.get(g.id)
        if not metric_data:
            # Check DB
            m_res = await db.execute(select(GPUMetric).where(GPUMetric.gpu_id == g.id).order_by(desc(GPUMetric.timestamp)).limit(1))
            m = m_res.scalars().first()
            if m:
                metric_data = {
                    "gpu_utilization": m.gpu_utilization,
                    "memory_used_mb": m.memory_used_mb,
                    "memory_total_mb": m.memory_total_mb,
                    "temperature_c": m.temperature_c,
                    "power_draw_w": m.power_draw_w,
                    "cpu_utilization": m.cpu_utilization,
                    "ram_used_mb": m.ram_used_mb,
                    "ram_total_mb": m.ram_total_mb,
                }

        response_items.append(GPUResponse(
            id=g.id,
            provider_id=g.provider_id,
            gpu_name=g.gpu_name,
            vram_gb=g.vram_gb,
            driver_version=g.driver_version,
            cuda_version=g.cuda_version,
            price_per_hour=g.price_per_hour,
            status=g.status,
            reliability_score=g.reliability_score,
            total_jobs_completed=g.total_jobs_completed,
            total_uptime_hours=g.total_uptime_hours,
            last_heartbeat=g.last_heartbeat,
            agent_auth_key=None,
            is_simulated=g.is_simulated,
            ssh_enabled=g.ssh_enabled if g.ssh_enabled is not None else True,
            ssh_host=g.ssh_host or "127.0.0.1",
            ssh_port=g.ssh_port or 22,
            ssh_username=g.ssh_username or "gpuuser",
            ssh_auth_type=g.ssh_auth_type or "PASSWORD",
            ssh_active_sessions=g.ssh_active_sessions or 0,
            latest_metric=metric_data
        ))
    return response_items

@router.get("/{gpu_id}", response_model=GPUResponse)
async def get_gpu(gpu_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GPU).where(GPU.id == gpu_id))
    gpu = result.scalars().first()
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")

    metric_data = agent_manager.latest_gpu_telemetry.get(gpu.id)
    return GPUResponse(
        id=gpu.id,
        provider_id=gpu.provider_id,
        gpu_name=gpu.gpu_name,
        vram_gb=gpu.vram_gb,
        driver_version=gpu.driver_version,
        cuda_version=gpu.cuda_version,
        price_per_hour=gpu.price_per_hour,
        status=gpu.status,
        reliability_score=gpu.reliability_score,
        total_jobs_completed=gpu.total_jobs_completed,
        total_uptime_hours=gpu.total_uptime_hours,
        last_heartbeat=gpu.last_heartbeat,
        agent_auth_key=gpu.agent_auth_key,
        is_simulated=gpu.is_simulated,
        ssh_enabled=gpu.ssh_enabled if gpu.ssh_enabled is not None else True,
        ssh_host=gpu.ssh_host or "127.0.0.1",
        ssh_port=gpu.ssh_port or 22,
        ssh_username=gpu.ssh_username or "gpuuser",
        ssh_auth_type=gpu.ssh_auth_type or "PASSWORD",
        ssh_active_sessions=gpu.ssh_active_sessions or 0,
        latest_metric=metric_data
    )

@router.get("/{gpu_id}/ssh-info", response_model=SSHConnectionInfoResponse)
async def get_gpu_ssh_info(gpu_id: str, db: AsyncSession = Depends(get_db)):
    """
    Retrieve formatted SSH connection commands, VS Code configuration snippets,
    port forward helper, and interactive web terminal link for connecting to the GPU host.
    """
    result = await db.execute(select(GPU).where(GPU.id == gpu_id))
    gpu = result.scalars().first()
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU node not found")

    host = gpu.ssh_host or "127.0.0.1"
    port = gpu.ssh_port or 22
    user = gpu.ssh_username or "gpuuser"
    pwd = gpu.ssh_password or "gpupassword123"
    auth_type = gpu.ssh_auth_type or "PASSWORD"

    cli_cmd = f"ssh -p {port} {user}@{host}"
    vscode_snippet = (
        f"Host aigpushare-{gpu.id[:8]}\n"
        f"    HostName {host}\n"
        f"    Port {port}\n"
        f"    User {user}\n"
        f"    ForwardAgent yes"
    )
    jupyter_cmd = f"ssh -N -L 8888:localhost:8888 -p {port} {user}@{host}"
    scp_cmd = f"scp -P {port} model.pt {user}@{host}:~/workspace/"
    ws_url = f"/ws/ssh/terminal/{gpu.id}"

    return SSHConnectionInfoResponse(
        gpu_id=gpu.id,
        gpu_name=gpu.gpu_name,
        status=gpu.status,
        ssh_enabled=gpu.ssh_enabled if gpu.ssh_enabled is not None else True,
        ssh_host=host,
        ssh_port=port,
        ssh_username=user,
        ssh_password=pwd if auth_type == "PASSWORD" else None,
        ssh_auth_type=auth_type,
        ssh_cli_command=cli_cmd,
        vscode_config_snippet=vscode_snippet,
        jupyter_tunnel_command=jupyter_cmd,
        scp_upload_command=scp_cmd,
        interactive_ws_url=ws_url
    )

@router.put("/{gpu_id}/ssh-config", response_model=GPUResponse)
async def update_gpu_ssh_config(
    gpu_id: str,
    payload: SSHConfigUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(GPU).where(GPU.id == gpu_id))
    gpu = result.scalars().first()
    if not gpu:
        raise HTTPException(status_code=404, detail="GPU not found")

    if gpu.provider_id != current_user.id and current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Not authorized to configure this GPU node")

    if payload.ssh_enabled is not None:
        gpu.ssh_enabled = payload.ssh_enabled
    if payload.ssh_host is not None:
        gpu.ssh_host = payload.ssh_host
    if payload.ssh_port is not None:
        gpu.ssh_port = payload.ssh_port
    if payload.ssh_username is not None:
        gpu.ssh_username = payload.ssh_username
    if payload.ssh_password is not None:
        gpu.ssh_password = payload.ssh_password
    if payload.ssh_public_key is not None:
        gpu.ssh_public_key = payload.ssh_public_key
    if payload.ssh_auth_type is not None:
        gpu.ssh_auth_type = payload.ssh_auth_type

    await db.commit()
    await db.refresh(gpu)

    metric_data = agent_manager.latest_gpu_telemetry.get(gpu.id)
    return GPUResponse(
        id=gpu.id,
        provider_id=gpu.provider_id,
        gpu_name=gpu.gpu_name,
        vram_gb=gpu.vram_gb,
        driver_version=gpu.driver_version,
        cuda_version=gpu.cuda_version,
        price_per_hour=gpu.price_per_hour,
        status=gpu.status,
        reliability_score=gpu.reliability_score,
        total_jobs_completed=gpu.total_jobs_completed,
        total_uptime_hours=gpu.total_uptime_hours,
        last_heartbeat=gpu.last_heartbeat,
        agent_auth_key=gpu.agent_auth_key,
        is_simulated=gpu.is_simulated,
        ssh_enabled=gpu.ssh_enabled,
        ssh_host=gpu.ssh_host,
        ssh_port=gpu.ssh_port,
        ssh_username=gpu.ssh_username,
        ssh_auth_type=gpu.ssh_auth_type,
        ssh_active_sessions=gpu.ssh_active_sessions,
        latest_metric=metric_data
    )

@router.post("/register", response_model=GPUResponse)
async def register_gpu(
    payload: GPURegister,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    auth_key = secrets.token_hex(32)
    gpu = GPU(
        provider_id=current_user.id,
        gpu_name=payload.gpu_name,
        vram_gb=payload.vram_gb,
        driver_version=payload.driver_version,
        cuda_version=payload.cuda_version,
        price_per_hour=payload.price_per_hour,
        status=GPUStatus.AVAILABLE,
        reliability_score=0.98,
        agent_auth_key=auth_key,
        is_simulated=payload.is_simulated,
        ssh_enabled=payload.ssh_enabled,
        ssh_host=payload.ssh_host or "127.0.0.1",
        ssh_port=payload.ssh_port or 22,
        ssh_username=payload.ssh_username or "gpuuser",
        ssh_password=payload.ssh_password or "gpupassword123",
        ssh_public_key=payload.ssh_public_key,
        ssh_auth_type=payload.ssh_auth_type or "PASSWORD"
    )
    db.add(gpu)
    await db.commit()
    await db.refresh(gpu)

    return GPUResponse(
        id=gpu.id,
        provider_id=gpu.provider_id,
        gpu_name=gpu.gpu_name,
        vram_gb=gpu.vram_gb,
        driver_version=gpu.driver_version,
        cuda_version=gpu.cuda_version,
        price_per_hour=gpu.price_per_hour,
        status=gpu.status,
        reliability_score=gpu.reliability_score,
        total_jobs_completed=0,
        total_uptime_hours=0.0,
        last_heartbeat=gpu.last_heartbeat,
        agent_auth_key=gpu.agent_auth_key,
        is_simulated=gpu.is_simulated,
        ssh_enabled=gpu.ssh_enabled,
        ssh_host=gpu.ssh_host,
        ssh_port=gpu.ssh_port,
        ssh_username=gpu.ssh_username,
        ssh_auth_type=gpu.ssh_auth_type,
        ssh_active_sessions=0,
        latest_metric=None
    )
