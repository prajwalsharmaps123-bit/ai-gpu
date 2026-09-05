import random
from typing import List, Dict, Any, Optional, Tuple
from backend.app.models.models import GPU, GPUMetric, GPUStatus
from backend.app.services.ml_service import ml_service
from backend.app.core.config import settings

class AIScheduler:
    def __init__(self):
        self.w_avail = settings.SCHEDULER_W_AVAIL
        self.w_cost = settings.SCHEDULER_W_COST
        self.w_time = settings.SCHEDULER_W_TIME
        self.w_rel = settings.SCHEDULER_W_REL
        self.w_perf = settings.SCHEDULER_W_PERF

    def filter_candidates(
        self,
        gpus: List[GPU],
        min_vram_gb: float,
        preferred_gpu_id: Optional[str] = None
    ) -> List[GPU]:
        candidates = []
        for g in gpus:
            if preferred_gpu_id and g.id == preferred_gpu_id:
                return [g]
            
            # Condition 1: Must be AVAILABLE
            if g.status != GPUStatus.AVAILABLE:
                continue
            
            # Condition 2: Must satisfy minimum VRAM requirement
            if g.vram_gb < min_vram_gb:
                continue
                
            candidates.append(g)
        return candidates

    def evaluate_and_rank(
        self,
        candidates: List[GPU],
        gpu_latest_metrics: Dict[str, Optional[GPUMetric]],
        workload_spec: Dict[str, Any],
        strategy: str = "AI_SCHEDULER"
    ) -> List[Dict[str, Any]]:
        if not candidates:
            return []

        scored_candidates = []

        # Gather metrics and predict for each candidate
        for gpu in candidates:
            metric = gpu_latest_metrics.get(gpu.id)
            gpu_util = metric.gpu_utilization if metric else 10.0
            cpu_util = metric.cpu_utilization if metric else 15.0
            ram_pct = (metric.ram_used_mb / max(metric.ram_total_mb, 1.0)) * 100.0 if metric else 25.0
            temp_c = metric.temperature_c if metric else 50.0
            power_w = metric.power_draw_w if metric else 60.0

            requested_duration = workload_spec.get("expected_runtime_hours", 1.0)
            
            # 1. Predict Availability
            p_avail = ml_service.predict_availability(
                gpu_utilization=gpu_util,
                cpu_utilization=cpu_util,
                ram_usage_percent=ram_pct,
                temperature_c=temp_c,
                power_draw_w=power_w,
                requested_duration_hours=requested_duration,
                historical_reliability=gpu.reliability_score
            )

            # 2. Predict Workload Runtime
            pred_runtime_hours = ml_service.predict_runtime(
                gpu_vram_gb=gpu.vram_gb,
                workload_type=workload_spec.get("workload_type", "Training"),
                framework=workload_spec.get("framework", "PyTorch"),
                model_size_mb=workload_spec.get("model_size_mb", 500.0),
                batch_size=workload_spec.get("batch_size", 32),
                dataset_size_mb=workload_spec.get("dataset_size_mb", 1000.0),
                epochs=workload_spec.get("epochs", 20)
            )

            # 3. Calculate Total Workload Cost: (Price/hr) * (Predicted Runtime)
            est_cost = round(gpu.price_per_hour * pred_runtime_hours, 2)
            
            # 4. Performance Proxy (VRAM & relative compute)
            perf_score = min(gpu.vram_gb / 24.0, 1.0)

            scored_candidates.append({
                "gpu": gpu,
                "p_avail": p_avail,
                "pred_runtime_hours": pred_runtime_hours,
                "est_cost": est_cost,
                "reliability": gpu.reliability_score,
                "perf_score": perf_score,
                "price_per_hour": gpu.price_per_hour
            })

        # Normalization across candidate pool for multi-objective optimization
        max_cost = max([c["est_cost"] for c in scored_candidates]) or 1.0
        min_cost = min([c["est_cost"] for c in scored_candidates])
        max_time = max([c["pred_runtime_hours"] for c in scored_candidates]) or 1.0
        min_time = min([c["pred_runtime_hours"] for c in scored_candidates])

        for c in scored_candidates:
            # Normalized values [0, 1]
            norm_cost = (c["est_cost"] - min_cost) / (max_cost - min_cost + 1e-6)
            norm_time = (c["pred_runtime_hours"] - min_time) / (max_time - min_time + 1e-6)
            
            if strategy == "AI_SCHEDULER":
                # Higher score is better
                score = (
                    self.w_avail * c["p_avail"]
                    - self.w_cost * norm_cost
                    - self.w_time * norm_time
                    + self.w_rel * c["reliability"]
                    + self.w_perf * c["perf_score"]
                )
            elif strategy == "CHEAPEST":
                score = -1.0 * c["est_cost"]
            elif strategy == "FASTEST":
                score = -1.0 * c["pred_runtime_hours"]
            elif strategy == "AVAILABILITY":
                score = c["p_avail"]
            elif strategy == "RANDOM":
                score = random.random()
            else:
                score = c["p_avail"]

            c["score"] = round(float(score), 4)

        # Sort descending by score
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates

scheduler = AIScheduler()
