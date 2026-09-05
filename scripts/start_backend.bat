@echo off
echo ===================================================
echo   Starting AI-GPUShare Backend Server (FastAPI)
echo ===================================================
cd /d "%~dp0\.."
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
pause
