import os
import joblib
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional

class MLService:
    def __init__(self, model_dir: str = "ml/models"):
        self.model_dir = model_dir
        self.availability_model = None
        self.runtime_pipeline = None
        self.availability_metrics = {}
        self.runtime_metrics = {}
        self.load_models()

    def load_models(self):
        avail_path = os.path.join(self.model_dir, "availability_model.joblib")
        runtime_path = os.path.join(self.model_dir, "runtime_model.joblib")

        if os.path.exists(avail_path):
            try:
                data = joblib.load(avail_path)
                self.availability_model = data["model"]
                self.availability_metrics = data.get("metrics", {})
                print("[MLService] Availability Model successfully loaded.")
            except Exception as e:
                print(f"[MLService] Error loading availability model: {e}")

        if os.path.exists(runtime_path):
            try:
                data = joblib.load(runtime_path)
                self.runtime_pipeline = data["pipeline"]
                self.runtime_metrics = data.get("metrics", {})
                print("[MLService] Runtime Model successfully loaded.")
            except Exception as e:
                print(f"[MLService] Error loading runtime model: {e}")

    def predict_availability(
        self,
        gpu_utilization: float,
        cpu_utilization: float,
        ram_usage_percent: float,
        temperature_c: float,
        power_draw_w: float = 120.0,
        requested_duration_hours: float = 1.0,
        historical_reliability: float = 0.98,
        hour_of_day: Optional[int] = None,
        day_of_week: Optional[int] = None
    ) -> float:
        now = datetime.utcnow()
        h = hour_of_day if hour_of_day is not None else now.hour
        d = day_of_week if day_of_week is not None else now.weekday()

        if self.availability_model is not None:
            features = pd.DataFrame([{
                "gpu_utilization": gpu_utilization,
                "cpu_utilization": cpu_utilization,
                "ram_usage_percent": ram_usage_percent,
                "temperature_c": temperature_c,
                "power_draw_w": power_draw_w,
                "hour_of_day": h,
                "day_of_week": d,
                "requested_duration_hours": requested_duration_hours,
                "historical_reliability": historical_reliability
            }])
            try:
                prob = float(self.availability_model.predict_proba(features)[0][1])
                return round(prob, 4)
            except Exception as e:
                print(f"[MLService] Inference fallback error: {e}")
        
        # Heuristic fallback if model not yet saved
        base = historical_reliability
        if temperature_c > 80:
            base -= (temperature_c - 80) * 0.03
        if gpu_utilization > 80:
            base -= 0.1
        return round(float(np.clip(base - requested_duration_hours * 0.02, 0.1, 0.99)), 4)

    def predict_runtime(
        self,
        gpu_vram_gb: float,
        workload_type: str = "Training",
        framework: str = "PyTorch",
        model_size_mb: float = 500.0,
        batch_size: int = 32,
        dataset_size_mb: float = 1000.0,
        epochs: int = 20
    ) -> float:
        """Returns predicted runtime in hours"""
        if self.runtime_pipeline is not None:
            df = pd.DataFrame([{
                "workload_type": workload_type,
                "framework": framework,
                "gpu_vram_gb": gpu_vram_gb,
                "model_size_mb": model_size_mb,
                "batch_size": batch_size,
                "dataset_size_mb": dataset_size_mb,
                "epochs": epochs
            }])
            try:
                mins = float(self.runtime_pipeline.predict(df)[0])
                mins = max(mins, 1.0)
                return round(mins / 60.0, 4)
            except Exception as e:
                print(f"[MLService] Runtime inference error: {e}")

        # Heuristic fallback
        raw_mins = (model_size_mb * dataset_size_mb * epochs) / (batch_size * 2000.0 * max(gpu_vram_gb, 4.0)) * 10
        return round(max(raw_mins / 60.0, 0.05), 4)

ml_service = MLService()
