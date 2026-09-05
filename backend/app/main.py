import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.database import engine, Base
from backend.app.api.auth import router as auth_router
from backend.app.api.gpus import router as gpus_router
from backend.app.api.jobs import router as jobs_router
from backend.app.api.provider import router as provider_router
from backend.app.api.ml import router as ml_router
from backend.app.api.admin import router as admin_router
from backend.app.api.websocket import router as ws_router
from backend.app.services.agent_manager import agent_manager
from backend.app.services.ml_service import ml_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Ensure SQLite columns exist for existing databases
        for col_def in [
            ("ssh_enabled", "BOOLEAN DEFAULT 1"),
            ("ssh_host", "VARCHAR(100) DEFAULT '127.0.0.1'"),
            ("ssh_port", "INTEGER DEFAULT 22"),
            ("ssh_username", "VARCHAR(100) DEFAULT 'gpuuser'"),
            ("ssh_password", "VARCHAR(100) DEFAULT 'gpupassword123'"),
            ("ssh_public_key", "TEXT"),
            ("ssh_auth_type", "VARCHAR(30) DEFAULT 'PASSWORD'"),
            ("ssh_active_sessions", "INTEGER DEFAULT 0"),
        ]:
            try:
                from sqlalchemy import text
                await conn.execute(text(f"ALTER TABLE gpus ADD COLUMN {col_def[0]} {col_def[1]}"))
            except Exception:
                pass  # Column already exists
    print("[AI-GPUShare Backend] Database tables verified/initialized.")
    
    # Reload ML models
    ml_service.load_models()

    # Start background agent watchdog
    watchdog_task = asyncio.create_task(agent_manager.start_watchdog())
    yield
    # Shutdown
    watchdog_task.cancel()
    await engine.dispose()
    print("[AI-GPUShare Backend] Shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Intelligent Distributed GPU Marketplace with Availability Prediction & Cost-Aware Scheduling",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(gpus_router, prefix=settings.API_V1_STR)
app.include_router(jobs_router, prefix=settings.API_V1_STR)
app.include_router(provider_router, prefix=settings.API_V1_STR)
app.include_router(ml_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)
app.include_router(ws_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "system": "AI-GPUShare Platform API",
        "status": "ONLINE",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health": "OK"
    }
