from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from backend.app.core.database import get_db
from backend.app.models.models import GPU, Job, Wallet, WalletTransaction, User
from backend.app.schemas.schemas import GPUResponse, WalletTransactionResponse
from backend.app.api.auth import get_current_user
from backend.app.services.agent_manager import agent_manager

router = APIRouter(prefix="/provider", tags=["Provider"])

@router.get("/dashboard")
async def get_provider_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Retrieve provider GPUs
    g_res = await db.execute(select(GPU).where(GPU.provider_id == current_user.id))
    gpus = g_res.scalars().all()

    # Retrieve wallet
    w_res = await db.execute(select(Wallet).where(Wallet.user_id == current_user.id))
    wallet = w_res.scalars().first()
    balance = wallet.balance if wallet else 0.0

    total_jobs = sum(g.total_jobs_completed for g in gpus)
    total_gpus = len(gpus)
    online_gpus = sum(1 for g in gpus if g.status in ["AVAILABLE", "BUSY", "RESERVED"])

    # Recent transactions
    tx_items = []
    if wallet:
        t_res = await db.execute(
            select(WalletTransaction)
            .where(WalletTransaction.wallet_id == wallet.id)
            .order_by(desc(WalletTransaction.timestamp))
            .limit(10)
        )
        tx_items = t_res.scalars().all()

    gpu_list = []
    for g in gpus:
        metric = agent_manager.latest_gpu_telemetry.get(g.id)
        gpu_list.append({
            "id": g.id,
            "gpu_name": g.gpu_name,
            "vram_gb": g.vram_gb,
            "status": g.status,
            "price_per_hour": g.price_per_hour,
            "reliability_score": g.reliability_score,
            "agent_auth_key": g.agent_auth_key,
            "latest_metric": metric
        })

    return {
        "provider_id": current_user.id,
        "provider_name": current_user.name,
        "total_gpus": total_gpus,
        "online_gpus": online_gpus,
        "total_jobs_completed": total_jobs,
        "wallet_balance": balance,
        "gpus": gpu_list,
        "recent_earnings": [
            {
                "id": t.id,
                "amount": t.amount,
                "type": t.transaction_type,
                "description": t.description,
                "timestamp": t.timestamp
            } for t in tx_items
        ]
    }
