from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.models.models import Job, GPU, Wallet, WalletTransaction, JobStatus

PLATFORM_FEE_PERCENTAGE = 0.10 # 10% platform fee

class BillingService:
    @staticmethod
    async def settle_job(job: Job, db: AsyncSession) -> dict:
        """
        Calculates final cost based on actual runtime seconds,
        deducts from user's wallet, credits provider's wallet,
        and logs transactions.
        """
        if not job.actual_start_time or not job.actual_end_time:
            return {"status": "skipped", "reason": "Missing execution start/end timestamps"}

        runtime_seconds = (job.actual_end_time - job.actual_start_time).total_seconds()
        job.actual_runtime_seconds = max(runtime_seconds, 1.0)
        runtime_hours = job.actual_runtime_seconds / 3600.0

        # Retrieve GPU directly via query to avoid lazy load issues in async SQLAlchemy
        gpu = None
        if job.gpu_id:
            gpu_res = await db.execute(select(GPU).where(GPU.id == job.gpu_id))
            gpu = gpu_res.scalars().first()

        price_per_hour = gpu.price_per_hour if gpu else 15.0
        
        # Calculate cost
        total_cost = round(max(runtime_hours * price_per_hour, 0.5), 2)
        platform_fee = round(total_cost * PLATFORM_FEE_PERCENTAGE, 2)
        provider_earning = round(total_cost - platform_fee, 2)

        job.cost_charged = total_cost
        job.provider_earned = provider_earning

        # 1. Deduct from User Wallet
        user_wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == job.user_id))
        user_wallet = user_wallet_res.scalars().first()
        if user_wallet:
            user_wallet.balance -= total_cost
            user_wallet.updated_at = datetime.utcnow()
            
            user_tx = WalletTransaction(
                wallet_id=user_wallet.id,
                job_id=job.id,
                amount=-total_cost,
                transaction_type="CHARGE",
                description=f"Workload compute cost for Job #{job.id[:8]} ({round(runtime_seconds, 1)}s runtime)"
            )
            db.add(user_tx)

        # 2. Credit Provider Wallet (if provider exists)
        if gpu and gpu.provider_id:
            provider_wallet_res = await db.execute(select(Wallet).where(Wallet.user_id == gpu.provider_id))
            provider_wallet = provider_wallet_res.scalars().first()
            if not provider_wallet:
                provider_wallet = Wallet(user_id=gpu.provider_id, balance=0.0)
                db.add(provider_wallet)
                await db.flush()

            provider_wallet.balance += provider_earning
            provider_wallet.updated_at = datetime.utcnow()

            provider_tx = WalletTransaction(
                wallet_id=provider_wallet.id,
                job_id=job.id,
                amount=provider_earning,
                transaction_type="EARNING",
                description=f"Provider compute earnings for Job #{job.id[:8]} on {gpu.gpu_name}"
            )
            db.add(provider_tx)

        await db.commit()
        return {
            "total_cost": total_cost,
            "provider_earning": provider_earning,
            "platform_fee": platform_fee,
            "runtime_seconds": job.actual_runtime_seconds
        }

billing_service = BillingService()
