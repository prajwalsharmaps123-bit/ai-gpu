import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
from backend.app.core.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class UserRole(str):
    USER = "USER"
    PROVIDER = "PROVIDER"
    ADMIN = "ADMIN"

class GPUStatus(str):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"
    MAINTENANCE = "MAINTENANCE"

class JobStatus(str):
    CREATED = "CREATED"
    QUEUED = "QUEUED"
    SCHEDULING = "SCHEDULING"
    RESERVED = "RESERVED"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.USER, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    gpus = relationship("GPU", back_populates="owner", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")


class GPU(Base):
    __tablename__ = "gpus"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    provider_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    gpu_name = Column(String(100), nullable=False)
    vram_gb = Column(Float, nullable=False)
    driver_version = Column(String(50), nullable=True)
    cuda_version = Column(String(50), nullable=True)
    price_per_hour = Column(Float, nullable=False, default=15.0)  # INR or USD
    status = Column(String(30), default=GPUStatus.AVAILABLE, index=True)
    reliability_score = Column(Float, default=0.98)
    total_jobs_completed = Column(Integer, default=0)
    total_uptime_hours = Column(Float, default=0.0)
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    agent_auth_key = Column(String(64), unique=True, index=True, nullable=True)
    is_simulated = Column(Boolean, default=False)
    
    # SSH & Remote Host Connectivity
    ssh_enabled = Column(Boolean, default=True)
    ssh_host = Column(String(100), default="127.0.0.1")
    ssh_port = Column(Integer, default=22)
    ssh_username = Column(String(100), default="gpuuser")
    ssh_password = Column(String(100), default="gpupassword123")
    ssh_public_key = Column(Text, nullable=True)
    ssh_auth_type = Column(String(30), default="PASSWORD") # PASSWORD or PUBLIC_KEY
    ssh_active_sessions = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="gpus")
    metrics = relationship("GPUMetric", back_populates="gpu", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="gpu")


class GPUMetric(Base):
    __tablename__ = "gpu_metrics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    gpu_id = Column(String(36), ForeignKey("gpus.id"), nullable=False, index=True)
    gpu_utilization = Column(Float, default=0.0)
    memory_used_mb = Column(Float, default=0.0)
    memory_total_mb = Column(Float, default=0.0)
    temperature_c = Column(Float, default=0.0)
    power_draw_w = Column(Float, default=0.0)
    cpu_utilization = Column(Float, default=0.0)
    ram_used_mb = Column(Float, default=0.0)
    ram_total_mb = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    gpu = relationship("GPU", back_populates="metrics")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    gpu_id = Column(String(36), ForeignKey("gpus.id"), nullable=True, index=True)
    
    # Workload spec
    title = Column(String(150), default="PyTorch Training Workload")
    workload_type = Column(String(50), default="Training") # Training, Inference, FineTuning
    framework = Column(String(50), default="PyTorch")       # PyTorch, TensorFlow, JAX
    docker_image = Column(String(150), default="pytorch/pytorch:latest")
    script_command = Column(Text, default="python train.py")
    
    # Requirements & constraints
    min_vram_gb = Column(Float, default=4.0)
    expected_runtime_hours = Column(Float, default=1.0)
    budget_max = Column(Float, default=50.0)
    priority = Column(String(20), default="NORMAL")
    scheduling_strategy = Column(String(30), default="AI_SCHEDULER") # RANDOM, CHEAPEST, FASTEST, AVAILABILITY, AI_SCHEDULER
    
    # Predictions
    predicted_availability = Column(Float, nullable=True)
    predicted_runtime_hours = Column(Float, nullable=True)
    predicted_cost = Column(Float, nullable=True)
    scheduler_score = Column(Float, nullable=True)

    # State & Execution Lifecycle
    status = Column(String(30), default=JobStatus.CREATED, index=True)
    actual_start_time = Column(DateTime, nullable=True)
    actual_end_time = Column(DateTime, nullable=True)
    actual_runtime_seconds = Column(Float, default=0.0)
    cost_charged = Column(Float, default=0.0)
    provider_earned = Column(Float, default=0.0)
    
    # Output logs & exit
    logs = Column(Text, default="")
    exit_code = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="jobs")
    gpu = relationship("GPU", back_populates="jobs")


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), unique=True, nullable=False)
    balance = Column(Float, default=500.0) # default initial free credits
    currency = Column(String(10), default="INR")
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="wallet")
    transactions = relationship("WalletTransaction", back_populates="wallet", cascade="all, delete-orphan")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    wallet_id = Column(String(36), ForeignKey("wallets.id"), nullable=False, index=True)
    job_id = Column(String(36), nullable=True)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String(30), nullable=False) # DEPOSIT, CHARGE, EARNING, REFUND
    description = Column(String(255), default="")
    timestamp = Column(DateTime, default=datetime.utcnow)

    wallet = relationship("Wallet", back_populates="transactions")
