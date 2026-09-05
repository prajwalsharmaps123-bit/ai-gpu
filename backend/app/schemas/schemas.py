from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# --- Auth Schemas ---
class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: str = "USER"  # USER, PROVIDER, ADMIN

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: datetime
    wallet_balance: Optional[float] = 0.0

    class Config:
        from_attributes = True

# --- GPU Schemas ---
class GPURegister(BaseModel):
    gpu_name: str
    vram_gb: float
    driver_version: Optional[str] = None
    cuda_version: Optional[str] = None
    price_per_hour: float = 15.0
    is_simulated: bool = False
    ssh_enabled: bool = True
    ssh_host: Optional[str] = "127.0.0.1"
    ssh_port: Optional[int] = 22
    ssh_username: Optional[str] = "gpuuser"
    ssh_password: Optional[str] = "gpupassword123"
    ssh_public_key: Optional[str] = None
    ssh_auth_type: Optional[str] = "PASSWORD"

class GPUMetricPayload(BaseModel):
    gpu_id: str
    gpu_utilization: float
    memory_used_mb: float
    memory_total_mb: float
    temperature_c: float
    power_draw_w: float
    cpu_utilization: float
    ram_used_mb: float
    ram_total_mb: float
    timestamp: Optional[datetime] = None

class GPUResponse(BaseModel):
    id: str
    provider_id: str
    gpu_name: str
    vram_gb: float
    driver_version: Optional[str]
    cuda_version: Optional[str]
    price_per_hour: float
    status: str
    reliability_score: float
    total_jobs_completed: int
    total_uptime_hours: float
    last_heartbeat: Optional[datetime]
    agent_auth_key: Optional[str] = None
    is_simulated: bool
    ssh_enabled: bool = True
    ssh_host: Optional[str] = "127.0.0.1"
    ssh_port: Optional[int] = 22
    ssh_username: Optional[str] = "gpuuser"
    ssh_auth_type: Optional[str] = "PASSWORD"
    ssh_active_sessions: Optional[int] = 0
    latest_metric: Optional[dict] = None

    class Config:
        from_attributes = True

# --- SSH Specific Schemas ---
class SSHConnectionInfoResponse(BaseModel):
    gpu_id: str
    gpu_name: str
    status: str
    ssh_enabled: bool
    ssh_host: str
    ssh_port: int
    ssh_username: str
    ssh_password: Optional[str] = None
    ssh_auth_type: str
    ssh_cli_command: str
    vscode_config_snippet: str
    jupyter_tunnel_command: str
    scp_upload_command: str
    interactive_ws_url: str

class SSHConfigUpdateRequest(BaseModel):
    ssh_enabled: Optional[bool] = None
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    ssh_username: Optional[str] = None
    ssh_password: Optional[str] = None
    ssh_public_key: Optional[str] = None
    ssh_auth_type: Optional[str] = None

# --- Job Schemas ---
class JobCreate(BaseModel):
    title: str = "PyTorch Model Training"
    workload_type: str = "Training" # Training, Inference, FineTuning, Interactive
    framework: str = "PyTorch"       # PyTorch, TensorFlow, Custom
    docker_image: str = "pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime"
    script_command: str = "python -c 'import torch; print(f\"CUDA available: {torch.cuda.is_available()}\")'"
    min_vram_gb: float = 4.0
    expected_runtime_hours: float = 0.5
    budget_max: float = 50.0
    priority: str = "NORMAL"
    scheduling_strategy: str = "AI_SCHEDULER" # RANDOM, CHEAPEST, FASTEST, AVAILABILITY, AI_SCHEDULER
    preferred_gpu_id: Optional[str] = None
    enable_ssh: bool = True

class JobResponse(BaseModel):
    id: str
    user_id: str
    gpu_id: Optional[str]
    title: str
    workload_type: str
    framework: str
    docker_image: str
    script_command: str
    min_vram_gb: float
    expected_runtime_hours: float
    budget_max: float
    priority: str
    scheduling_strategy: str
    predicted_availability: Optional[float]
    predicted_runtime_hours: Optional[float]
    predicted_cost: Optional[float]
    scheduler_score: Optional[float]
    status: str
    actual_start_time: Optional[datetime]
    actual_end_time: Optional[datetime]
    actual_runtime_seconds: float
    cost_charged: float
    provider_earned: float
    logs: Optional[str]
    exit_code: Optional[int]
    created_at: datetime
    gpu_name: Optional[str] = None
    ssh_command: Optional[str] = None

    class Config:
        from_attributes = True

# --- ML Prediction Request Schemas ---
class AvailabilityPredictionRequest(BaseModel):
    gpu_utilization: float
    cpu_utilization: float
    ram_usage_percent: float
    temperature_c: float
    requested_duration_hours: float
    historical_uptime_ratio: float = 0.98

class RuntimePredictionRequest(BaseModel):
    gpu_vram_gb: float
    workload_type: str
    framework: str
    model_size_mb: float = 500.0
    batch_size: int = 32
    dataset_size_mb: float = 1000.0
    epochs: int = 20

# --- Wallet Schemas ---
class WalletDeposit(BaseModel):
    amount: float = Field(..., gt=0)

class WalletTransactionResponse(BaseModel):
    id: str
    job_id: Optional[str]
    amount: float
    transaction_type: str
    description: str
    timestamp: datetime

    class Config:
        from_attributes = True
