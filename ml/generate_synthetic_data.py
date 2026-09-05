import os
import numpy as np
import pandas as pd

def generate_availability_dataset(n_samples: int = 5000, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    
    gpu_util = np.random.uniform(5.0, 98.0, n_samples)
    cpu_util = np.random.uniform(5.0, 95.0, n_samples)
    ram_pct = np.random.uniform(15.0, 95.0, n_samples)
    temp_c = np.random.uniform(40.0, 88.0, n_samples)
    power_w = np.random.uniform(30.0, 350.0, n_samples)
    hour = np.random.randint(0, 24, n_samples)
    day = np.random.randint(0, 7, n_samples)
    requested_duration = np.random.exponential(scale=2.0, size=n_samples) + 0.2 # 0.2h to ~10h
    requested_duration = np.clip(requested_duration, 0.2, 12.0)
    reliability = np.random.beta(a=9, b=1, size=n_samples) # mostly high reliability [0.75 - 1.0]

    # Availability probability calculation based on physical laws & thermal load:
    # High temp (>82C), high load (>90%), and long duration decrease availability
    thermal_penalty = np.where(temp_c > 80, (temp_c - 80) * 0.04, 0.0)
    load_penalty = np.where((gpu_util > 85) & (cpu_util > 85), 0.20, 0.0)
    duration_penalty = requested_duration * 0.025
    
    p_avail = reliability - thermal_penalty - load_penalty - duration_penalty
    p_avail = np.clip(p_avail, 0.05, 0.99)
    
    labels = (np.random.rand(n_samples) < p_avail).astype(int)

    df = pd.DataFrame({
        "gpu_utilization": np.round(gpu_util, 2),
        "cpu_utilization": np.round(cpu_util, 2),
        "ram_usage_percent": np.round(ram_pct, 2),
        "temperature_c": np.round(temp_c, 1),
        "power_draw_w": np.round(power_w, 1),
        "hour_of_day": hour,
        "day_of_week": day,
        "requested_duration_hours": np.round(requested_duration, 2),
        "historical_reliability": np.round(reliability, 3),
        "is_available": labels
    })
    return df

def generate_runtime_dataset(n_samples: int = 5000, seed: int = 42) -> pd.DataFrame:
    np.random.seed(seed)
    
    # GPU VRAM classes: 4GB, 6GB, 8GB, 12GB, 16GB, 24GB, 40GB, 80GB
    vram_choices = [4.0, 6.0, 8.0, 10.0, 12.0, 16.0, 24.0, 48.0, 80.0]
    gpu_vram = np.random.choice(vram_choices, n_samples)
    
    # Relative compute factor (e.g. RTX 2050 ~ 1.0, RTX 3060 ~ 2.5, RTX 3090 ~ 5.5, A100 ~ 12.0)
    gpu_speed_factor = gpu_vram * np.random.uniform(0.8, 1.2, n_samples)
    
    workload_types = ["Training", "FineTuning", "Inference"]
    workloads = np.random.choice(workload_types, n_samples, p=[0.45, 0.35, 0.20])
    
    frameworks = ["PyTorch", "TensorFlow", "JAX"]
    framework_list = np.random.choice(frameworks, n_samples, p=[0.7, 0.2, 0.1])
    
    model_size_mb = np.random.uniform(50.0, 4000.0, n_samples)
    batch_size = np.random.choice([8, 16, 32, 64, 128, 256], n_samples)
    dataset_size_mb = np.random.uniform(100.0, 15000.0, n_samples)
    epochs = np.random.choice([5, 10, 20, 30, 50, 100], n_samples)

    # Base computational complexity
    workload_multiplier = np.where(workloads == "Training", 1.0, np.where(workloads == "FineTuning", 0.6, 0.15))
    
    # Approximate compute minutes
    flops_proxy = (model_size_mb * dataset_size_mb * epochs * workload_multiplier) / (batch_size * 2000.0)
    runtime_mins = (flops_proxy / (gpu_speed_factor * 0.4)) + np.random.normal(1.0, 0.3, n_samples)
    runtime_mins = np.clip(runtime_mins, 0.5, 360.0) # 30 seconds to 6 hours

    df = pd.DataFrame({
        "gpu_vram_gb": gpu_vram,
        "workload_type": workloads,
        "framework": framework_list,
        "model_size_mb": np.round(model_size_mb, 1),
        "batch_size": batch_size,
        "dataset_size_mb": np.round(dataset_size_mb, 1),
        "epochs": epochs,
        "runtime_minutes": np.round(runtime_mins, 2)
    })
    return df

if __name__ == "__main__":
    os.makedirs("ml/datasets", exist_ok=True)
    df_avail = generate_availability_dataset(8000)
    df_avail.to_csv("ml/datasets/gpu_availability.csv", index=False)
    print(f"[Synthetic Data] Generated {len(df_avail)} availability records at ml/datasets/gpu_availability.csv")

    df_runtime = generate_runtime_dataset(8000)
    df_runtime.to_csv("ml/datasets/workload_runtime.csv", index=False)
    print(f"[Synthetic Data] Generated {len(df_runtime)} runtime records at ml/datasets/workload_runtime.csv")
