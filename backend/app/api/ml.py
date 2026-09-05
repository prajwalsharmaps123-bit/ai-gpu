from fastapi import APIRouter, Depends
from backend.app.schemas.schemas import AvailabilityPredictionRequest, RuntimePredictionRequest
from backend.app.services.ml_service import ml_service

router = APIRouter(prefix="/ml", tags=["ML Services"])

@router.post("/predict-availability")
async def predict_availability(payload: AvailabilityPredictionRequest):
    p_avail = ml_service.predict_availability(
        gpu_utilization=payload.gpu_utilization,
        cpu_utilization=payload.cpu_utilization,
        ram_usage_percent=payload.ram_usage_percent,
        temperature_c=payload.temperature_c,
        requested_duration_hours=payload.requested_duration_hours,
        historical_reliability=payload.historical_uptime_ratio
    )
    return {
        "predicted_availability_probability": p_avail,
        "is_safe_to_schedule": p_avail >= 0.80,
        "confidence_level": "HIGH" if p_avail > 0.90 else ("MEDIUM" if p_avail > 0.70 else "LOW")
    }

@router.post("/predict-runtime")
async def predict_runtime(payload: RuntimePredictionRequest):
    pred_hours = ml_service.predict_runtime(
        gpu_vram_gb=payload.gpu_vram_gb,
        workload_type=payload.workload_type,
        framework=payload.framework,
        model_size_mb=payload.model_size_mb,
        batch_size=payload.batch_size,
        dataset_size_mb=payload.dataset_size_mb,
        epochs=payload.epochs
    )
    return {
        "predicted_runtime_hours": pred_hours,
        "predicted_runtime_minutes": round(pred_hours * 60, 2),
        "predicted_runtime_seconds": round(pred_hours * 3600, 1)
    }

@router.get("/metrics")
async def get_model_evaluation_metrics():
    return {
        "availability_model": ml_service.availability_metrics,
        "runtime_model": ml_service.runtime_metrics
    }
