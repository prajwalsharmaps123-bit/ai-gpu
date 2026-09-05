import os
import sys
import random
import numpy as np
import pandas as pd
from typing import List, Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.models.models import GPU, GPUMetric, GPUStatus
from backend.app.services.scheduler import scheduler
from backend.app.services.ml_service import ml_service

def simulate_cluster_benchmark(num_jobs: int = 200, seed: int = 42) -> Dict[str, Any]:
    random.seed(seed)
    np.random.seed(seed)

    # 1. Define Heterogeneous GPU Cluster
    cluster_specs = [
        {"name": "NVIDIA RTX 2050", "vram": 4.0, "price": 10.0, "reliability": 0.94, "speed": 1.0},
        {"name": "NVIDIA RTX 3060", "vram": 12.0, "price": 18.0, "reliability": 0.97, "speed": 2.4},
        {"name": "NVIDIA RTX 3080", "vram": 10.0, "price": 28.0, "reliability": 0.96, "speed": 3.8},
        {"name": "NVIDIA RTX 3090", "vram": 24.0, "price": 40.0, "reliability": 0.98, "speed": 5.2},
        {"name": "NVIDIA RTX 4090", "vram": 24.0, "price": 55.0, "reliability": 0.99, "speed": 7.5},
        {"name": "NVIDIA A100 SXM", "vram": 80.0, "price": 120.0, "reliability": 0.995, "speed": 12.0}
    ]

    gpus = []
    for i, spec in enumerate(cluster_specs):
        g = GPU(
            id=f"gpu-{i+1}",
            provider_id=f"prov-{(i%2)+1}",
            gpu_name=spec["name"],
            vram_gb=spec["vram"],
            price_per_hour=spec["price"],
            status=GPUStatus.AVAILABLE,
            reliability_score=spec["reliability"]
        )
        gpus.append((g, spec["speed"]))

    # 2. Generate Workload Batches
    workloads = []
    for j in range(num_jobs):
        vram_req = random.choice([4.0, 8.0, 12.0, 16.0, 24.0])
        w_type = random.choice(["Training", "FineTuning", "Inference"])
        model_sz = random.uniform(200, 3000)
        data_sz = random.uniform(500, 8000)
        epochs = random.choice([10, 20, 50])
        batch_sz = random.choice([16, 32, 64])

        workloads.append({
            "job_id": f"job-{j+1}",
            "min_vram_gb": vram_req,
            "workload_type": w_type,
            "framework": "PyTorch",
            "model_size_mb": model_sz,
            "dataset_size_mb": data_sz,
            "epochs": epochs,
            "batch_size": batch_sz,
            "expected_runtime_hours": random.uniform(0.5, 3.0)
        })

    strategies = ["RANDOM", "CHEAPEST", "FASTEST", "AVAILABILITY", "AI_SCHEDULER"]
    results_summary = {}

    for strat in strategies:
        total_cost = 0.0
        total_runtime_hrs = 0.0
        failures = 0
        successes = 0
        total_score = 0.0

        for w in workloads:
            # Filter candidates by VRAM
            eligible = [g for g, spd in gpus if g.vram_gb >= w["min_vram_gb"]]
            if not eligible:
                continue

            # Mock latest metrics with thermal and load variance
            metrics_map = {}
            for g, spd in gpus:
                metrics_map[g.id] = GPUMetric(
                    gpu_id=g.id,
                    gpu_utilization=random.uniform(10, 85),
                    cpu_utilization=random.uniform(15, 75),
                    ram_used_mb=4000,
                    ram_total_mb=16000,
                    temperature_c=random.uniform(45, 82),
                    power_draw_w=120
                )

            # Evaluate with scheduler
            ranked = scheduler.evaluate_and_rank(
                candidates=eligible,
                gpu_latest_metrics=metrics_map,
                workload_spec=w,
                strategy=strat
            )

            chosen = ranked[0]
            chosen_gpu: GPU = chosen["gpu"]
            
            # Ground truth simulation: Actual runtime depends on GPU speed
            # Base complexity
            base_hours = w["expected_runtime_hours"]
            # Find speed factor
            speed = next(spd for g, spd in gpus if g.id == chosen_gpu.id)
            actual_runtime = max(base_hours / (speed / 2.0), 0.1)
            actual_cost = actual_runtime * chosen_gpu.price_per_hour

            # Actual failure probability (based on temperature and reliability)
            temp = metrics_map[chosen_gpu.id].temperature_c
            failure_prob = (1.0 - chosen_gpu.reliability_score) + (0.15 if temp > 80 else 0.0)
            is_failed = random.random() < failure_prob

            if is_failed:
                failures += 1
            else:
                successes += 1
                total_cost += actual_cost
                total_runtime_hrs += actual_runtime

        total_evaluated = successes + failures
        results_summary[strat] = {
            "strategy": strat,
            "total_jobs": total_evaluated,
            "success_rate_percent": round((successes / total_evaluated) * 100, 2) if total_evaluated else 0.0,
            "failure_rate_percent": round((failures / total_evaluated) * 100, 2) if total_evaluated else 0.0,
            "avg_cost_per_job": round(total_cost / max(successes, 1), 2),
            "avg_runtime_hours_per_job": round(total_runtime_hrs / max(successes, 1), 2),
            "total_cost": round(total_cost, 2),
            "total_runtime_hours": round(total_runtime_hrs, 2)
        }

    return results_summary

if __name__ == "__main__":
    os.makedirs("ml/datasets", exist_ok=True)
    res = simulate_cluster_benchmark(250)
    print("\n==================== RESEARCH BENCHMARK RESULTS ====================")
    df_res = pd.DataFrame(list(res.values()))
    print(df_res.to_string(index=False))
    df_res.to_csv("ml/datasets/benchmark_results.csv", index=False)
    print("====================================================================")
