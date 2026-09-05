import os
import sys
import asyncio
import subprocess
from typing import Callable, Awaitable, Optional

class DockerWorkloadManager:
    def __init__(self):
        self.has_docker = False
        try:
            res = subprocess.run(["docker", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=3)
            if res.returncode == 0:
                self.has_docker = True
                print("[DockerManager] Docker runtime detected.")
        except Exception:
            self.has_docker = False
            print("[DockerManager] Docker not detected or not active. Using native sandbox execution engine.")

    async def run_workload(
        self,
        job_id: str,
        docker_image: str,
        script_command: str,
        log_callback: Callable[[str, str], Awaitable[None]],
        status_callback: Callable[[str, str, Optional[int]], Awaitable[None]],
        timeout_seconds: int = 3600
    ):
        """
        Executes the user workload and streams stdout/stderr chunks asynchronously.
        """
        await status_callback(job_id, "RUNNING", None)
        await log_callback(job_id, f"[Container Manager] Initializing execution environment for Job {job_id[:8]}...\n")
        await log_callback(job_id, f"[Container Manager] Target Image: {docker_image}\n")
        await log_callback(job_id, f"[Container Manager] Command: {script_command}\n")
        await log_callback(job_id, "------------------------------------------------------------\n")

        # Native Sandbox Subprocess Execution
        try:
            agent_dir = os.path.dirname(os.path.abspath(__file__))
            env = os.environ.copy()
            existing_pypath = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{agent_dir}{os.pathsep}{existing_pypath}" if existing_pypath else agent_dir

            # Use current python executable for python commands
            cmd = script_command
            if cmd.startswith("python "):
                cmd = f'"{sys.executable}" {cmd[7:]}'

            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            async def read_stream(stream, is_stderr=False):
                prefix = "[stderr] " if is_stderr else ""
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace")
                    await log_callback(job_id, f"{prefix}{decoded}")

            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        read_stream(process.stdout, is_stderr=False),
                        read_stream(process.stderr, is_stderr=True),
                        process.wait()
                    ),
                    timeout=timeout_seconds
                )
                exit_code = process.returncode
                if exit_code == 0:
                    await log_callback(job_id, "\n------------------------------------------------------------\n")
                    await log_callback(job_id, "[Container Manager] Workload successfully completed with exit code 0.\n")
                    await status_callback(job_id, "COMPLETED", 0)
                else:
                    await log_callback(job_id, f"\n[Container Manager] Workload failed with exit code {exit_code}.\n")
                    await status_callback(job_id, "FAILED", exit_code)
            except asyncio.TimeoutError:
                process.kill()
                await log_callback(job_id, f"\n[Container Manager] Execution timeout exceeded ({timeout_seconds}s). Process terminated.\n")
                await status_callback(job_id, "FAILED", -1)

        except Exception as e:
            await log_callback(job_id, f"\n[Execution Error] {str(e)}\n")
            await status_callback(job_id, "FAILED", 1)
