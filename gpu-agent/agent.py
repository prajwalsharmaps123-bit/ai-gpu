import sys
import os
import time
import json
import asyncio
import argparse
import httpx
import websockets
from typing import Optional

# Add parent directory to sys.path so it can run standalone
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gpu_monitor import GPUMonitor
from system_monitor import SystemMonitor
from docker_manager import DockerWorkloadManager
from ssh_manager import SSHHostManager

class GPUAgentDaemon:
    def __init__(
        self,
        server_url: str = "http://127.0.0.1:8000",
        gpu_id: Optional[str] = None,
        auth_key: Optional[str] = None,
        force_simulation: bool = False,
        heartbeat_interval: float = 3.0,
        ssh_host: Optional[str] = None,
        ssh_port: int = 22,
        ssh_username: Optional[str] = None,
        ssh_password: str = "gpupassword123",
        enable_ssh: bool = True
    ):
        self.server_url = server_url.rstrip("/")
        self.ws_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
        self.gpu_id = gpu_id
        self.auth_key = auth_key
        self.heartbeat_interval = heartbeat_interval
        
        self.gpu_monitor = GPUMonitor(force_simulation=force_simulation)
        self.sys_monitor = SystemMonitor()
        self.workload_mgr = DockerWorkloadManager()
        self.ssh_mgr = SSHHostManager(
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_username=ssh_username,
            ssh_password=ssh_password,
            ssh_enabled=enable_ssh
        )
        
        self.running = True
        self.active_tasks = {}

    async def register_gpu_if_needed(self, provider_email: str = "provider@gpu.io", provider_pass: str = "provider123") -> bool:
        if self.gpu_id and self.auth_key:
            return True

        print(f"[Agent] No GPU ID provided. Auto-registering hardware with server {self.server_url}...")
        hw_info = self.gpu_monitor.get_gpu_info()
        ssh_info = self.ssh_mgr.get_ssh_info()

        async with httpx.AsyncClient() as client:
            try:
                # 1. Login or Register provider account
                auth_res = await client.post(
                    f"{self.server_url}/api/v1/auth/register",
                    json={
                        "name": "Primary Provider Node",
                        "email": provider_email,
                        "password": provider_pass,
                        "role": "PROVIDER"
                    }
                )
                if auth_res.status_code == 400: # already registered, login
                    auth_res = await client.post(
                        f"{self.server_url}/api/v1/auth/login",
                        json={"email": provider_email, "password": provider_pass}
                    )
                
                if auth_res.status_code != 200:
                    print(f"[Agent Error] Provider authentication failed: {auth_res.text}")
                    return False

                token = auth_res.json()["access_token"]

                # 2. Register GPU with SSH metadata
                gpu_res = await client.post(
                    f"{self.server_url}/api/v1/gpus/register",
                    headers={"Authorization": f"Bearer {token}"},
                    json={
                        "gpu_name": hw_info["gpu_name"],
                        "vram_gb": hw_info["vram_gb"],
                        "driver_version": hw_info["driver_version"],
                        "cuda_version": hw_info["cuda_version"],
                        "price_per_hour": 18.0,
                        "is_simulated": hw_info["is_simulated"],
                        "ssh_enabled": ssh_info["ssh_enabled"],
                        "ssh_host": ssh_info["ssh_host"],
                        "ssh_port": ssh_info["ssh_port"],
                        "ssh_username": ssh_info["ssh_username"],
                        "ssh_password": ssh_info["ssh_password"],
                        "ssh_auth_type": ssh_info["ssh_auth_type"]
                    }
                )
                if gpu_res.status_code == 200:
                    data = gpu_res.json()
                    self.gpu_id = data["id"]
                    self.auth_key = data["agent_auth_key"]
                    print(f"[Agent Registered Successfully] GPU ID: {self.gpu_id}, Key: {self.auth_key}")
                    print(f"[Agent SSH Ready] Host: {ssh_info['ssh_username']}@{ssh_info['ssh_host']}:{ssh_info['ssh_port']}")
                    return True
                else:
                    print(f"[Agent Registration Error] {gpu_res.text}")
                    return False
            except Exception as e:
                print(f"[Agent Connection Error] Could not reach server: {e}")
                return False

    async def run(self):
        registered = await self.register_gpu_if_needed()
        if not registered:
            print("[Agent] Registration failed. Retrying in 5 seconds...")
            await asyncio.sleep(5)

        ws_endpoint = f"{self.ws_url}/api/v1/ws/agent/{self.gpu_id}?auth_key={self.auth_key or ''}"

        while self.running:
            try:
                print(f"[Agent] Connecting to Central Server WebSocket: {ws_endpoint}")
                async with websockets.connect(ws_endpoint) as ws:
                    print(f"[Agent] Connected & Authenticated with Central Server!")

                    async def heartbeat_loop():
                        while self.running:
                            gpu_metrics = self.gpu_monitor.get_telemetry()
                            sys_metrics = self.sys_monitor.get_system_telemetry()
                            ssh_info = self.ssh_mgr.get_ssh_info()
                            
                            payload = {
                                "type": "HEARTBEAT",
                                "data": {
                                    **gpu_metrics,
                                    **sys_metrics,
                                    "gpu_status": "AVAILABLE" if not self.active_tasks else "BUSY",
                                    "ssh_info": ssh_info
                                }
                            }
                            await ws.send(json.dumps(payload))
                            await asyncio.sleep(self.heartbeat_interval)

                    async def listener_loop():
                        while self.running:
                            msg = await ws.recv()
                            data = json.loads(msg)
                            msg_type = data.get("action") or data.get("type")

                            if msg_type == "START_JOB":
                                job_id = data.get("job_id")
                                docker_image = data.get("docker_image", "pytorch/pytorch:latest")
                                script_cmd = data.get("script_command", "python -c 'print(\"Hello GPU\")'")
                                timeout = data.get("timeout_seconds", 3600)
                                print(f"[Agent] Received START_JOB command for Job: {job_id}")

                                async def log_cb(j_id, chunk):
                                    await ws.send(json.dumps({
                                        "type": "JOB_UPDATE",
                                        "job_id": j_id,
                                        "data": {"log_chunk": chunk}
                                    }))

                                async def status_cb(j_id, status_val, code):
                                    await ws.send(json.dumps({
                                        "type": "JOB_UPDATE",
                                        "job_id": j_id,
                                        "data": {"status": status_val, "exit_code": code}
                                    }))
                                    if status_val in ["COMPLETED", "FAILED"]:
                                        if j_id in self.active_tasks:
                                            del self.active_tasks[j_id]

                                # Spawn workload execution task
                                task = asyncio.create_task(
                                    self.workload_mgr.run_workload(
                                        job_id=job_id,
                                        docker_image=docker_image,
                                        script_command=script_cmd,
                                        log_callback=log_cb,
                                        status_callback=status_cb,
                                        timeout_seconds=timeout
                                    )
                                )
                                self.active_tasks[job_id] = task

                            elif msg_type == "START_SSH_SESSION":
                                session_id = data.get("session_id")
                                print(f"[Agent] Initializing interactive SSH/PTY terminal for session {session_id}")

                                async def ssh_out_cb(s_id, chunk):
                                    try:
                                        await ws.send(json.dumps({
                                            "type": "SSH_OUTPUT",
                                            "session_id": s_id,
                                            "data": chunk
                                        }))
                                    except Exception:
                                        pass

                                await self.ssh_mgr.start_interactive_session(session_id, ssh_out_cb)

                            elif msg_type == "SSH_INPUT":
                                session_id = data.get("session_id")
                                input_data = data.get("data", "")
                                if session_id and input_data:
                                    await self.ssh_mgr.write_input(session_id, input_data)

                            elif msg_type == "STOP_SSH_SESSION":
                                session_id = data.get("session_id")
                                if session_id:
                                    print(f"[Agent] Terminating interactive SSH session {session_id}")
                                    await self.ssh_mgr.stop_session(session_id)

                    await asyncio.gather(heartbeat_loop(), listener_loop())

            except websockets.exceptions.ConnectionClosed:
                print("[Agent] WebSocket closed by server. Reconnecting in 3s...")
                await asyncio.sleep(3)
            except Exception as e:
                print(f"[Agent Exception] {e}. Reconnecting in 3s...")
                await asyncio.sleep(3)

def main():
    parser = argparse.ArgumentParser(description="AI-GPUShare Provider Agent")
    parser.add_argument("--server", default="http://127.0.0.1:8000", help="FastAPI Server URL")
    parser.add_argument("--gpu-id", default=None, help="Existing GPU ID")
    parser.add_argument("--auth-key", default=None, help="Agent Auth Key")
    parser.add_argument("--simulate", action="store_true", help="Force simulated hardware metrics")
    parser.add_argument("--interval", type=float, default=3.0, help="Heartbeat interval in seconds")
    parser.add_argument("--ssh-host", default=None, help="Custom SSH Host IP / Hostname")
    parser.add_argument("--ssh-port", type=int, default=22, help="Host SSH Port")
    parser.add_argument("--ssh-user", default=None, help="Host SSH Username")
    parser.add_argument("--ssh-pass", default="gpupassword123", help="Host SSH Password")
    parser.add_argument("--disable-ssh", action="store_true", help="Disable SSH remote access")
    args = parser.parse_args()

    agent = GPUAgentDaemon(
        server_url=args.server,
        gpu_id=args.gpu_id,
        auth_key=args.auth_key,
        force_simulation=args.simulate,
        heartbeat_interval=args.interval,
        ssh_host=args.ssh_host,
        ssh_port=args.ssh_port,
        ssh_username=args.ssh_user,
        ssh_password=args.ssh_pass,
        enable_ssh=not args.disable_ssh
    )
    asyncio.run(agent.run())

if __name__ == "__main__":
    main()
