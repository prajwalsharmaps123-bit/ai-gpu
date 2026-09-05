import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Set, Optional, Any
from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.models import GPU, GPUMetric, GPUStatus, Job, JobStatus
from backend.app.services.billing import billing_service

class AgentConnectionManager:
    def __init__(self):
        # gpu_id -> WebSocket
        self.active_agent_connections: Dict[str, WebSocket] = {}
        # job_id -> Set[WebSocket] for UI log streaming
        self.active_ui_subscribers: Dict[str, Set[WebSocket]] = {}
        # session_id -> WebSocket (UI client connected for interactive SSH terminal)
        self.active_ssh_ui_clients: Dict[str, WebSocket] = {}
        # session_id -> gpu_id
        self.ssh_session_gpu_map: Dict[str, str] = {}
        # in-memory cache of latest telemetry per gpu_id
        self.latest_gpu_telemetry: Dict[str, Dict[str, Any]] = {}
        # in-memory cache of ssh info per gpu_id
        self.gpu_ssh_info: Dict[str, Dict[str, Any]] = {}
        # background watchdog task handle
        self._watchdog_task: Optional[asyncio.Task] = None

    async def connect_agent(self, gpu_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_agent_connections[gpu_id] = websocket
        print(f"[AgentManager] GPU Agent connected: {gpu_id}")

    def disconnect_agent(self, gpu_id: str):
        if gpu_id in self.active_agent_connections:
            del self.active_agent_connections[gpu_id]
            print(f"[AgentManager] GPU Agent disconnected: {gpu_id}")

    async def register_ssh_ui_client(self, session_id: str, gpu_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_ssh_ui_clients[session_id] = websocket
        self.ssh_session_gpu_map[session_id] = gpu_id
        print(f"[AgentManager] SSH Web Terminal client connected for session {session_id} on GPU {gpu_id}")

    def unregister_ssh_ui_client(self, session_id: str):
        if session_id in self.active_ssh_ui_clients:
            del self.active_ssh_ui_clients[session_id]
        if session_id in self.ssh_session_gpu_map:
            gpu_id = self.ssh_session_gpu_map.pop(session_id)
            # Notify agent to close interactive pty/shell session
            asyncio.create_task(self.send_command_to_agent(gpu_id, {
                "action": "STOP_SSH_SESSION",
                "session_id": session_id
            }))
        print(f"[AgentManager] SSH Web Terminal client disconnected for session {session_id}")

    async def forward_ssh_output_to_ui(self, session_id: str, output_data: str):
        ws = self.active_ssh_ui_clients.get(session_id)
        if ws:
            try:
                await ws.send_json({
                    "type": "SSH_OUTPUT",
                    "session_id": session_id,
                    "data": output_data
                })
            except Exception:
                self.unregister_ssh_ui_client(session_id)

    async def forward_ssh_input_to_agent(self, session_id: str, input_data: str):
        gpu_id = self.ssh_session_gpu_map.get(session_id)
        if gpu_id:
            await self.send_command_to_agent(gpu_id, {
                "action": "SSH_INPUT",
                "session_id": session_id,
                "data": input_data
            })

    async def subscribe_ui_job(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.active_ui_subscribers:
            self.active_ui_subscribers[job_id] = set()
        self.active_ui_subscribers[job_id].add(websocket)

    def unsubscribe_ui_job(self, job_id: str, websocket: WebSocket):
        if job_id in self.active_ui_subscribers:
            self.active_ui_subscribers[job_id].discard(websocket)

    async def broadcast_job_log(self, job_id: str, log_chunk: str):
        if job_id in self.active_ui_subscribers:
            dead_sockets = set()
            for ws in self.active_ui_subscribers[job_id]:
                try:
                    await ws.send_json({
                        "type": "JOB_LOG",
                        "job_id": job_id,
                        "data": log_chunk
                    })
                except Exception:
                    dead_sockets.add(ws)
            for ws in dead_sockets:
                self.active_ui_subscribers[job_id].discard(ws)

    async def send_command_to_agent(self, gpu_id: str, command_payload: dict) -> bool:
        ws = self.active_agent_connections.get(gpu_id)
        if not ws:
            print(f"[AgentManager] No active agent WebSocket for GPU: {gpu_id}")
            return False
        try:
            await ws.send_json(command_payload)
            return True
        except Exception as e:
            print(f"[AgentManager] Failed to send command to GPU {gpu_id}: {e}")
            self.disconnect_agent(gpu_id)
            return False

    async def process_heartbeat(self, gpu_id: str, data: dict, db: AsyncSession):
        now = datetime.utcnow()
        self.latest_gpu_telemetry[gpu_id] = data

        ssh_data = data.get("ssh_info")
        if ssh_data:
            self.gpu_ssh_info[gpu_id] = ssh_data

        # Record metric in DB
        metric = GPUMetric(
            gpu_id=gpu_id,
            gpu_utilization=data.get("gpu_utilization", 0.0),
            memory_used_mb=data.get("memory_used_mb", 0.0),
            memory_total_mb=data.get("memory_total_mb", 0.0),
            temperature_c=data.get("temperature_c", 0.0),
            power_draw_w=data.get("power_draw_w", 0.0),
            cpu_utilization=data.get("cpu_utilization", 0.0),
            ram_used_mb=data.get("ram_used_mb", 0.0),
            ram_total_mb=data.get("ram_total_mb", 0.0),
            timestamp=now
        )
        db.add(metric)

        # Update GPU last heartbeat, status, and SSH configuration if available
        gpu_res = await db.execute(select(GPU).where(GPU.id == gpu_id))
        gpu = gpu_res.scalars().first()
        if gpu:
            gpu.last_heartbeat = now
            reported_status = data.get("gpu_status", GPUStatus.AVAILABLE)
            # Do not overwrite BUSY or RESERVED if a job is actively running
            if gpu.status not in [GPUStatus.BUSY, GPUStatus.RESERVED] or reported_status == GPUStatus.AVAILABLE:
                gpu.status = reported_status
            
            if ssh_data:
                if "ssh_host" in ssh_data and ssh_data["ssh_host"]:
                    gpu.ssh_host = ssh_data["ssh_host"]
                if "ssh_port" in ssh_data and ssh_data["ssh_port"]:
                    gpu.ssh_port = ssh_data["ssh_port"]
                if "ssh_username" in ssh_data and ssh_data["ssh_username"]:
                    gpu.ssh_username = ssh_data["ssh_username"]
                if "ssh_enabled" in ssh_data:
                    gpu.ssh_enabled = ssh_data["ssh_enabled"]
                if "ssh_active_sessions" in ssh_data:
                    gpu.ssh_active_sessions = ssh_data["ssh_active_sessions"]

        await db.commit()

    async def process_job_update(self, job_id: str, data: dict, db: AsyncSession):
        """Processes execution updates from the GPU agent"""
        job_res = await db.execute(select(Job).where(Job.id == job_id))
        job = job_res.scalars().first()
        if not job:
            return

        status = data.get("status")
        log_chunk = data.get("log_chunk", "")
        exit_code = data.get("exit_code")

        if log_chunk:
            job.logs = (job.logs or "") + log_chunk
            await self.broadcast_job_log(job_id, log_chunk)

        gpu = None
        if job.gpu_id:
            g_res = await db.execute(select(GPU).where(GPU.id == job.gpu_id))
            gpu = g_res.scalars().first()

        if status == "RUNNING" and job.status != JobStatus.RUNNING:
            job.status = JobStatus.RUNNING
            job.actual_start_time = datetime.utcnow()
            if gpu:
                gpu.status = GPUStatus.BUSY

        elif status in ["COMPLETED", "FAILED"]:
            job.status = JobStatus.COMPLETED if status == "COMPLETED" else JobStatus.FAILED
            job.actual_end_time = datetime.utcnow()
            job.exit_code = exit_code if exit_code is not None else (0 if status == "COMPLETED" else 1)
            
            if gpu:
                gpu.status = GPUStatus.AVAILABLE
                if status == "COMPLETED":
                    gpu.total_jobs_completed += 1
            
            # Settle billing
            await billing_service.settle_job(job, db)

        await db.commit()

    async def start_watchdog(self):
        """Monitors stale heartbeats and marks inactive GPUs as OFFLINE"""
        while True:
            try:
                await asyncio.sleep(5)
                async with AsyncSessionLocal() as db:
                    now = datetime.utcnow()
                    cutoff = now - timedelta(seconds=15)
                    
                    stmt = select(GPU).where(GPU.last_heartbeat < cutoff, GPU.status != GPUStatus.OFFLINE)
                    res = await db.execute(stmt)
                    stale_gpus = res.scalars().all()
                    
                    for gpu in stale_gpus:
                        print(f"[Watchdog] GPU {gpu.id} ({gpu.gpu_name}) heartbeat expired. Marking OFFLINE.")
                        gpu.status = GPUStatus.OFFLINE
                        if gpu.id in self.active_agent_connections:
                            del self.active_agent_connections[gpu.id]
                    if stale_gpus:
                        await db.commit()
            except Exception as e:
                print(f"[Watchdog Error] {e}")

agent_manager = AgentConnectionManager()
