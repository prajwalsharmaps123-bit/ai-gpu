@echo off
echo ===================================================
echo   Starting AI-GPUShare GPU Provider Agent Daemon
echo ===================================================
cd /d "%~dp0\.."
.venv\Scripts\python.exe gpu-agent/agent.py --server http://127.0.0.1:8000
pause
