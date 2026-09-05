import os
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score, f1_score
from xgboost import XGBClassifier

def train_availability_model(data_path="ml/datasets/gpu_availability.csv", model_dir="ml/models"):
    os.makedirs(model_dir, exist_ok=True)
    df = pd.read_csv(data_path)
    
    feature_cols = [
        "gpu_utilization",
        "cpu_utilization",
        "ram_usage_percent",
        "temperature_c",
        "power_draw_w",
        "hour_of_day",
        "day_of_week",
        "requested_duration_hours",
        "historical_reliability"
    ]
    
    X = df[feature_cols]
    y = df["is_available"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # Train XGBoost Classifier
    xgb_model = XGBClassifier(
        n_estimators=120,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss"
    )
    xgb_model.fit(X_train, y_train)
    
    y_pred = xgb_model.predict(X_test)
    y_prob = xgb_model.predict_proba(X_test)[:, 1]
    
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred)),
        "recall": float(recall_score(y_test, y_pred)),
        "f1": float(f1_score(y_test, y_pred)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)),
        "feature_names": feature_cols
    }
    
    print("\n--- GPU Availability Model Evaluation ---")
    for k, v in metrics.items():
        if k != "feature_names":
            print(f"  {k.upper()}: {v:.4f}")
            
    joblib.dump({"model": xgb_model, "metrics": metrics, "feature_names": feature_cols}, os.path.join(model_dir, "availability_model.joblib"))
    print(f"[Model Saved] Saved availability model to {model_dir}/availability_model.joblib")
    return metrics

if __name__ == "__main__":
    train_availability_model()
