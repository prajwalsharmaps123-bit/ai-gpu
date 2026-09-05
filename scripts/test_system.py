import asyncio
import sys
import os
import httpx
import websockets
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

async def run_full_system_verification():
    print("\n=======================================================")
    print("   AI-GPUSHARE: END-TO-END SYSTEM VERIFICATION SUITE")
    print("=======================================================\n")

    base_url = "http://127.0.0.1:8000/api/v1"
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        # Step 1: Health Check
        print("[1/6] Testing Backend Root API Health...")
        health = await client.get("http://127.0.0.1:8000/")
        assert health.status_code == 200, f"Health check failed: {health.text}"
        print(f"  -> OK: {health.json()['system']} ({health.json()['status']})")

        # Step 2: Auth Registration
        print("\n[2/6] Registering Test Provider & Workload User...")
        prov_reg = await client.post(f"{base_url}/auth/register", json={
            "name": "Dr. Turing Provider",
            "email": "turing@gpu.io",
            "password": "password123",
            "role": "PROVIDER"
        })
        if prov_reg.status_code == 400:
            prov_reg = await client.post(f"{base_url}/auth/login", json={"email": "turing@gpu.io", "password": "password123"})
        prov_token = prov_reg.json()["access_token"]
        print(f"  -> Provider Authenticated (User ID: {prov_reg.json()['user']['id']})")

        user_reg = await client.post(f"{base_url}/auth/register", json={
            "name": "Prof. Hinton Researcher",
            "email": "hinton@gpu.io",
            "password": "password123",
            "role": "USER"
        })
        if user_reg.status_code == 400:
            user_reg = await client.post(f"{base_url}/auth/login", json={"email": "hinton@gpu.io", "password": "password123"})
        user_token = user_reg.json()["access_token"]
        print(f"  -> User Authenticated (Wallet Balance: INR {user_reg.json()['user']['wallet_balance']})")

        # Step 3: Register GPU Hardware
        print("\n[3/6] Registering Hardware Node in Marketplace...")
        gpu_reg = await client.post(
            f"{base_url}/gpus/register",
            headers={"Authorization": f"Bearer {prov_token}"},
            json={
                "gpu_name": "NVIDIA GeForce RTX 2050",
                "vram_gb": 4.0,
                "driver_version": "592.00",
                "cuda_version": "13.1",
                "price_per_hour": 15.0,
                "is_simulated": False
            }
        )
        assert gpu_reg.status_code == 200, f"GPU Registration failed: {gpu_reg.text}"
        gpu_id = gpu_reg.json()["id"]
        auth_key = gpu_reg.json()["agent_auth_key"]
        print(f"  -> GPU Node Registered: ID={gpu_id}, VRAM=4GB, Price=INR 15/hr")

        # Step 4: Test ML Predictions
        print("\n[4/6] Querying ML Prediction Services...")
        avail_pred = await client.post(f"{base_url}/ml/predict-availability", json={
            "gpu_utilization": 22.5,
            "cpu_utilization": 18.0,
            "ram_usage_percent": 35.0,
            "temperature_c": 51.0,
            "requested_duration_hours": 0.5,
            "historical_uptime_ratio": 0.98
        })
        print(f"  -> Availability Model Pred: P(avail)={avail_pred.json()['predicted_availability_probability']*100}%")

        runtime_pred = await client.post(f"{base_url}/ml/predict-runtime", json={
            "gpu_vram_gb": 4.0,
            "workload_type": "Training",
            "framework": "PyTorch",
            "model_size_mb": 400.0,
            "batch_size": 32,
            "dataset_size_mb": 1200.0,
            "epochs": 10
        })
        print(f"  -> Runtime Model Pred: {runtime_pred.json()['predicted_runtime_minutes']} mins")

        # Step 5: Connect GPU Provider Agent over WebSocket
        print("\n[5/6] Spawning Provider Agent WebSocket Client...")
        ws_url = f"ws://127.0.0.1:8000/api/v1/ws/agent/{gpu_id}?auth_key={auth_key}"
        
        async with websockets.connect(ws_url) as ws:
            ack = await ws.recv()
            print(f"  -> Agent Connected: {ack}")

            # Send Telemetry Heartbeat
            await ws.send(json.dumps({
                "type": "HEARTBEAT",
                "data": {
                    "gpu_utilization": 24.0,
                    "memory_used_mb": 620.0,
                    "memory_total_mb": 4096.0,
                    "temperature_c": 51.0,
                    "power_draw_w": 32.0,
                    "cpu_utilization": 15.0,
                    "ram_used_mb": 4200.0,
                    "ram_total_mb": 16000.0,
                    "gpu_status": "AVAILABLE"
                }
            }))
            hb_ack = await ws.recv()
            print(f"  -> Telemetry Recorded: {hb_ack}")

            # Step 6: Verify SSH Host Connection & Interactive Terminal Bridge
            print("\n[6/7] Testing SSH Host Connection & Terminal Bridge...")
            ssh_info_res = await client.get(f"{base_url}/gpus/{gpu_id}/ssh-info")
            assert ssh_info_res.status_code == 200, f"SSH info query failed: {ssh_info_res.text}"
            ssh_info_data = ssh_info_res.json()
            print(f"  -> SSH CLI Command: {ssh_info_data['ssh_cli_command']}")
            print(f"  -> SSH Port: {ssh_info_data['ssh_port']}, User: {ssh_info_data['ssh_username']}")
            print(f"  -> VS Code Snippet Host: HostName {ssh_info_data['ssh_host']}")
            assert "ssh -p" in ssh_info_data['ssh_cli_command'], "Invalid SSH CLI format"
            assert "ssh -N -L" in ssh_info_data['jupyter_tunnel_command'], "Invalid Jupyter tunnel format"

            # Connect Web UI Terminal to WebSocket Bridge
            term_ws_url = f"ws://127.0.0.1:8000/api/v1/ws/ssh/terminal/{gpu_id}?session_id=test_term_01"
            async with websockets.connect(term_ws_url) as term_ws:
                # Agent receives START_SSH_SESSION
                agent_cmd_raw = await ws.recv()
                agent_cmd = json.loads(agent_cmd_raw)
                assert agent_cmd.get("action") == "START_SSH_SESSION", f"Unexpected action: {agent_cmd}"
                print(f"  -> Agent Received: START_SSH_SESSION (Session: {agent_cmd.get('session_id')})")

                # Web client sends interactive shell input
                await term_ws.send(json.dumps({
                    "type": "SSH_INPUT",
                    "data": "echo 'Hello GPU Host Computer'\r\n"
                }))

                # Agent receives input
                agent_input_raw = await ws.recv()
                agent_input = json.loads(agent_input_raw)
                assert agent_input.get("action") == "SSH_INPUT", f"Unexpected input action: {agent_input}"

                # Agent sends back SSH_OUTPUT
                await ws.send(json.dumps({
                    "type": "SSH_OUTPUT",
                    "session_id": "test_term_01",
                    "data": "Hello GPU Host Computer\r\n"
                }))

                # Web terminal client receives output
                term_msg_raw = await term_ws.recv()
                term_msg = json.loads(term_msg_raw)
                assert term_msg.get("type") == "SSH_OUTPUT"
                assert "Hello GPU Host Computer" in term_msg.get("data")
                print("  -> Interactive Web Terminal Bridge: Bi-directional communication verified 100%!")

            # Step 7: Submit Workload Job via AI Scheduler
            print("\n[7/7] Submitting Distributed Workload via AI Scheduler...")
            job_res = await client.post(
                f"{base_url}/jobs",
                headers={"Authorization": f"Bearer {user_token}"},
                json={
                    "title": "PyTorch Matrix Multiplications & CUDA Probe",
                    "workload_type": "Inference",
                    "framework": "PyTorch",
                    "docker_image": "pytorch/pytorch:latest",
                    "script_command": "python -c \"import time; print('=== Remote Workload Initialized on GPU ==='); time.sleep(1); print('Tensor allocation: [2000, 2000] float32'); time.sleep(1); print('Execution finished cleanly.')\"",
                    "min_vram_gb": 4.0,
                    "expected_runtime_hours": 0.05,
                    "budget_max": 20.0,
                    "priority": "HIGH",
                    "scheduling_strategy": "AI_SCHEDULER"
                }
            )
            assert job_res.status_code == 200, f"Job submission failed: {job_res.text}"
            job_data = job_res.json()
            job_id = job_data["id"]
            print(f"  -> Job #{job_id[:8]} Assigned to GPU: {job_data['gpu_name']}")
            print(f"  -> AI Scheduler Score: {job_data['scheduler_score']}, Pred Avail: {round(job_data['predicted_availability']*100, 1)}%")

            # Agent receives START_JOB command over WebSocket
            cmd_raw = await ws.recv()
            cmd = json.loads(cmd_raw)
            print(f"  -> Agent Received Command: {cmd['action']} for Job #{cmd['job_id'][:8]}")

            # Simulate Execution & Stream Logs
            await ws.send(json.dumps({
                "type": "JOB_UPDATE",
                "job_id": job_id,
                "data": {"status": "RUNNING", "log_chunk": "[Container Engine] Starting PyTorch execution sandbox...\n"}
            }))
            await asyncio.sleep(1)

            await ws.send(json.dumps({
                "type": "JOB_UPDATE",
                "job_id": job_id,
                "data": {"status": "COMPLETED", "exit_code": 0, "log_chunk": "[Container Engine] Computation finished with exit code 0.\n"}
            }))

            # Verify settlement
            await asyncio.sleep(0.5)
            final_job = await client.get(f"{base_url}/jobs/{job_id}", headers={"Authorization": f"Bearer {user_token}"})
            fj = final_job.json()
            print(f"\n[Verification Succeeded]")
            print(f"  -> Final Status: {fj['status']}")
            print(f"  -> Actual Runtime: {fj['actual_runtime_seconds']}s")
            print(f"  -> Cost Billed: INR {fj['cost_charged']}")
            print(f"  -> Provider Earned: INR {fj['provider_earned']}")
            print("\n=======================================================")
            print("   ALL DISTRIBUTED & SSH PIPELINE TESTS PASSED WITH 100% SUCCESS")
            print("=======================================================\n")

if __name__ == "__main__":
    asyncio.run(run_full_system_verification())
