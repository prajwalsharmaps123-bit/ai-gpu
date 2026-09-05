import os
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, root_mean_squared_error, r2_score, mean_absolute_percentage_error
from xgboost import XGBRegressor

def train_runtime_model(data_path="ml/datasets/workload_runtime.csv", model_dir="ml/models"):
    os.makedirs(model_dir, exist_ok=True)
    df = pd.read_csv(data_path)
    
    categorical_cols = ["workload_type", "framework"]
    numeric_cols = ["gpu_vram_gb", "model_size_mb", "batch_size", "dataset_size_mb", "epochs"]
    
    X = df[categorical_cols + numeric_cols]
    y = df["runtime_minutes"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_cols),
            ("num", "passthrough", numeric_cols)
        ]
    )
    
    regressor = XGBRegressor(
        n_estimators=150,
        max_depth=6,
        learning_rate=0.07,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42
    )
    
    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("regressor", regressor)
    ])
    
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    
    mae = mean_absolute_error(y_test, y_pred)
    rmse = root_mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    mape = mean_absolute_percentage_error(y_test, y_pred)
    
    metrics = {
        "mae_minutes": float(mae),
        "rmse_minutes": float(rmse),
        "r2_score": float(r2),
        "mape_percent": float(mape * 100)
    }
    
    print("\n--- Workload Runtime Model Evaluation ---")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")
        
    joblib.dump({"pipeline": pipeline, "metrics": metrics, "categorical_cols": categorical_cols, "numeric_cols": numeric_cols}, os.path.join(model_dir, "runtime_model.joblib"))
    print(f"[Model Saved] Saved runtime prediction model to {model_dir}/runtime_model.joblib")
    return metrics

if __name__ == "__main__":
    train_runtime_model()
