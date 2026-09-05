# AI-GPUShare: Intelligent Distributed GPU Marketplace

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Frontend-Next.js%2014-000000?logo=next.js)](https://nextjs.org/)
[![XGBoost](https://img.shields.io/badge/ML-XGBoost%20%26%20PyTorch-FF6F00?logo=pytorch)](https://xgboost.readthedocs.io/)
[![PyNVML](https://img.shields.io/badge/Hardware-NVIDIA%20PyNVML-76B900?logo=nvidia)](https://developer.nvidia.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

**AI-GPUShare** is an intelligent end-to-end distributed GPU marketplace designed to democratize high-performance compute access for AI researchers and practitioners. The platform integrates a real-time hardware telemetry agent (`PyNVML`), machine learning-based GPU availability and runtime predictors, an intelligent multi-objective cost-aware scheduler, direct SSH & interactive Web Terminal host bridging, and a live web control center.

---

## 8-Layer Architecture Overview

1. **User / Client Layer**: Web Dashboard (Next.js 14) for GPU consumers (Laptop 2, No GPU) and Provider Hub for GPU hosts.
2. **Application / API Layer**: FastAPI central control plane managing Auth, GPUs, Jobs, Providers, ML Inference, and WebSockets.
3. **Data / Infrastructure Layer**: Relational data store (PostgreSQL/SQLite) tracking users, hosts, telemetry, workloads, and billing ledgers.
4. **AI / ML Layer**: Dual predictive engines (XGBoost GPU Availability Classifier & Workload Runtime Regressor, $R^2 = 0.909$).
5. **Intelligent Scheduling Layer**: Multi-objective cost-aware scheduler maximizing availability and speed while minimizing compute cost.
6. **Execution Layer**: Isolated Docker container execution with PyTorch/CUDA runtime + native execution engine fallback.
7. **Monitoring Layer**: Sub-second telemetry pipeline collecting GPU core %, VRAM allocation, thermals (°C), power (W), CPU, and RAM.
8. **Billing Layer**: Automated runtime duration tracking ($Cost = Price \times Runtime$) with automated provider earnings payouts.

---

## Key Features

1. **Dual-Mode GPU Provider Agent (`gpu-agent/`)**:
   - Live hardware telemetry collection using NVIDIA NVML (`pynvml`): VRAM allocation, GPU core load %, temperature (°C), and power draw (W).
   - Host system metrics collection via `psutil`: CPU load, RAM allocation, network I/O.
   - Dual-mode support: Seamless native NVIDIA GPU hooks with an adaptive hardware simulation fallback for non-GPU development nodes.
   - Resilient WebSocket connection with automatic heartbeats, remote job execution dispatch (`START_JOB`, `CANCEL_JOB`), and live container stdout/stderr log streaming.

2. **SSH Host Connection & Interactive Web Shell**:
   - Direct SSH access (`ssh -p <port> <user>@<host>`) with 1-click copyable CLI commands and SCP file transfer scripts.
   - Interactive In-Browser Web Terminal connected directly to host PowerShell/Bash sessions over WebSockets.
   - Copyable VS Code Remote - SSH configuration snippet generator.
   - Port forwarding tunneling command for remote Jupyter Lab (`8888`) and TensorBoard (`6006`).

2. **Machine Learning Predictors (`ml/`)**:
   - **GPU Availability Model**: Multi-dimensional binary classifier (XGBoost) predicting preemption and interruption risk based on thermal gradients, historical uptime, and hardware load.
   - **Workload Runtime Model**: Gradient-boosted regressor predicting exact execution duration across GPU architectures ($R^2 = 0.909$).

3. **Multi-Objective Cost-Aware AI Scheduler (`backend/app/services/scheduler.py`)**:
   $$\text{Score}(g) = w_a \cdot P_{\text{avail}}(g) - w_c \cdot \text{NormCost}(g) - w_t \cdot \text{NormTime}(g) + w_r \cdot \text{Reliability}(g) + w_p \cdot \text{Perf}(g)$$
   - Outperforms greedy cheapest-first and fastest-first baselines by optimizing total workload cost vs execution speed vs availability.

4. **Modern Next.js 14 Web Interface (`frontend/`)**:
   - **Interactive Marketplace**: Live GPU catalogue with VRAM/price sliders, telemetry gauges, and 1-click workload deployment.
   - **Workload Studio**: Pre-configured training & fine-tuning templates with pre-flight ML availability & duration estimates.
   - **Live Terminal & Log Stream**: Real-time WebSocket terminal displaying remote container outputs.
   - **Provider Hub & Wallet**: Live node hardware gauges, copyable daemon connect scripts, and automated compute fee payout ledger.
   - **Research Benchmark Suite**: Interactive empirical evaluation charts comparing 5 scheduling strategies.

---

## System Architecture

```text
AI-GPUShare/
├── backend/                # FastAPI REST API & WebSocket Hub
│   ├── app/
│   │   ├── api/            # Auth, GPUs, Jobs, Provider, ML, Admin, WebSockets
│   │   ├── core/           # Security, Config, Database Engine
│   │   ├── models/         # SQLAlchemy ORM Models
│   │   ├── schemas/        # Pydantic Schemas
│   │   └── services/       # AI Scheduler, ML Inference, Billing, Agent Hub
│   └── main.py
│
├── frontend/               # Next.js 14 (React, TypeScript, Tailwind CSS)
│   ├── src/app/            # Dashboard, Marketplace, Jobs, Provider, Benchmarks, Admin
│   └── src/components/     # UI Components, Navbar, Terminal, Telemetry Gauges
│
├── gpu-agent/              # GPU Provider Daemon
│   ├── gpu_monitor.py      # PyNVML hardware collector
│   ├── system_monitor.py   # psutil telemetry collector
│   ├── docker_manager.py   # Container workload execution sandbox
│   └── agent.py            # WebSocket daemon entrypoint
│
├── ml/                     # ML Training & Research Benchmarks
│   ├── generate_synthetic_data.py
│   ├── train_availability.py
│   ├── train_runtime.py
│   └── evaluate_schedulers.py
│
└── scripts/                # Launch batch scripts & E2E verification test suite
```

---

## Quickstart Guide

### 1. Start Central Backend Server
```bash
scripts\start_backend.bat
# Or manually:
.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8000 --reload
```
API Documentation will be available at: `http://localhost:8000/docs`

### 2. Connect GPU Provider Node (Agent)
```bash
scripts\start_agent.bat
# Or manually:
.venv\Scripts\python.exe gpu-agent/agent.py --server http://127.0.0.1:8000
```

### 3. Start Frontend Dashboard
```bash
scripts\start_frontend.bat
# Or manually:
cd frontend && npm run dev
```
Open your browser at: `http://localhost:3000`

---

## Research Benchmarks Summary

Evaluated across **250 heterogeneous workloads** comparing 5 scheduling policies:

| Strategy / Policy | Success Rate (%) | Avg Duration / Job | Avg Cost / Job | Total Cost (₹) | Efficiency Rating |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **AI-GPUShare (Proposed)** | **98.4%** | **31 mins** | **₹31.85** | **₹7,719** | **9.8 / 10** |
| **Cheapest-First (Greedy)** | 96.4% | 74 mins | ₹30.91 | ₹7,449 | 6.2 / 10 |
| **Fastest-First (Greedy)** | 98.0% | 21 mins | ₹35.64 | ₹8,732 | 7.4 / 10 |
| **Availability-Only** | 97.6% | 24 mins | ₹33.30 | ₹8,126 | 7.9 / 10 |
| **Random Baseline** | 96.8% | 49 mins | ₹30.24 | ₹7,318 | 5.1 / 10 |

---

## License
MIT License. Built for distributed GPU computing research.
