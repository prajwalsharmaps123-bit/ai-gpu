import os
import sys
import asyncio
import socket
import subprocess
from typing import Dict, Optional, Callable, Awaitable

class SSHHostManager:
    def __init__(
        self,
        ssh_host: Optional[str] = None,
        ssh_port: int = 22,
        ssh_username: Optional[str] = None,
        ssh_password: Optional[str] = "gpupassword123",
        ssh_enabled: bool = True
    ):
        self.ssh_enabled = ssh_enabled
        self.ssh_port = ssh_port
        self.ssh_password = ssh_password

        # Auto-detect username if not explicitly configured
        self.ssh_username = ssh_username or os.getenv("USERNAME") or os.getenv("USER") or "gpuuser"

        # Auto-detect local/host IP if not specified
        if ssh_host:
            self.ssh_host = ssh_host
        else:
            self.ssh_host = self._detect_host_ip()

        self.openssh_server_active = self._check_openssh_server()
        
        # session_id -> asyncio Subprocess
        self.active_shell_processes: Dict[str, asyncio.subprocess.Process] = {}
        # session_id -> asyncio Task reading output
        self.active_reader_tasks: Dict[str, asyncio.Task] = {}

    def _detect_host_ip(self) -> str:
        """Attempts to determine the routable IP of this host machine"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _check_openssh_server(self) -> bool:
        """Checks if native OpenSSH server is listening on the host"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            res = s.connect_ex(("127.0.0.1", self.ssh_port))
            s.close()
            return res == 0
        except Exception:
            return False

    def get_ssh_info(self) -> dict:
        """Returns hardware host SSH metadata payload"""
        return {
            "ssh_enabled": self.ssh_enabled,
            "ssh_host": self.ssh_host,
            "ssh_port": self.ssh_port,
            "ssh_username": self.ssh_username,
            "ssh_password": self.ssh_password,
            "ssh_auth_type": "PASSWORD",
            "ssh_native_server_active": self.openssh_server_active,
            "ssh_active_sessions": len(self.active_shell_processes)
        }

    async def start_interactive_session(
        self,
        session_id: str,
        output_callback: Callable[[str, str], Awaitable[None]]
    ) -> bool:
        """
        Spawns an interactive shell process (PowerShell on Windows, Bash on Linux)
        for real-time Web-to-Host interactive terminal bridging.
        """
        if session_id in self.active_shell_processes:
            return True

        is_windows = sys.platform.startswith("win")
        shell_cmd = "powershell.exe -NoLogo" if is_windows else os.getenv("SHELL", "/bin/bash")

        try:
            # Welcome banner
            banner = (
                f"\r\n\x1b[1;36m=========================================================\x1b[0m\r\n"
                f"\x1b[1;32m  AI-GPUShare: Connected to Host Remote Terminal\x1b[0m\r\n"
                f"\x1b[37m  Host: \x1b[1m{self.ssh_host}:{self.ssh_port}\x1b[0m\x1b[37m | User: \x1b[1m{self.ssh_username}\x1b[0m\r\n"
                f"\x1b[1;36m=========================================================\x1b[0m\r\n\r\n"
            )
            await output_callback(session_id, banner)

            process = await asyncio.create_subprocess_shell(
                shell_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            self.active_shell_processes[session_id] = process

            async def read_stream(stream):
                while True:
                    try:
                        chunk = await stream.read(512)
                        if not chunk:
                            break
                        decoded = chunk.decode("utf-8", errors="replace")
                        await output_callback(session_id, decoded)
                    except Exception:
                        break

            # Read both stdout and stderr in background task
            async def monitor_output():
                await asyncio.gather(
                    read_stream(process.stdout),
                    read_stream(process.stderr)
                )
                await output_callback(session_id, "\r\n\x1b[33m[Host Terminal Session Closed]\x1b[0m\r\n")
                if session_id in self.active_shell_processes:
                    del self.active_shell_processes[session_id]

            task = asyncio.create_task(monitor_output())
            self.active_reader_tasks[session_id] = task

            return True
        except Exception as e:
            await output_callback(session_id, f"\r\n\x1b[31m[Error starting interactive host shell: {str(e)}]\x1b[0m\r\n")
            return False

    async def write_input(self, session_id: str, data: str):
        """Sends user input keystrokes/commands into the active host shell process"""
        process = self.active_shell_processes.get(session_id)
        if process and process.stdin:
            try:
                process.stdin.write(data.encode("utf-8"))
                await process.stdin.drain()
            except Exception as e:
                print(f"[SSHManager] Stdin write error for session {session_id}: {e}")

    async def stop_session(self, session_id: str):
        """Terminates active shell process for the given session"""
        process = self.active_shell_processes.pop(session_id, None)
        if process:
            try:
                process.kill()
            except Exception:
                pass
        task = self.active_reader_tasks.pop(session_id, None)
        if task:
            task.cancel()
