import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.core.database import AsyncSessionLocal
from backend.app.models.models import GPU
from backend.app.services.agent_manager import agent_manager

router = APIRouter(prefix="/ws", tags=["WebSockets"])

@router.websocket("/agent/{gpu_id}")
async def agent_websocket_endpoint(websocket: WebSocket, gpu_id: str, auth_key: str = Query(None)):
    """
    Persistent bi-directional WebSocket connection with GPU Provider Agent
    """
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(GPU).where(GPU.id == gpu_id))
        gpu = res.scalars().first()
        if not gpu:
            await websocket.close(code=4004, reason="GPU not found")
            return
        if auth_key and gpu.agent_auth_key and auth_key != gpu.agent_auth_key:
            await websocket.close(code=4003, reason="Unauthorized Agent Key")
            return

    await agent_manager.connect_agent(gpu_id, websocket)

    try:
        # Acknowledge connection
        await websocket.send_json({"type": "CONNECTION_ESTABLISHED", "gpu_id": gpu_id})

        while True:
            raw_data = await websocket.receive_text()
            try:
                payload = json.loads(raw_data)
                msg_type = payload.get("type")

                async with AsyncSessionLocal() as db:
                    if msg_type == "HEARTBEAT" or msg_type == "TELEMETRY":
                        await agent_manager.process_heartbeat(gpu_id, payload.get("data", {}), db)
                        await websocket.send_json({"type": "HEARTBEAT_ACK", "status": "OK"})

                    elif msg_type == "JOB_UPDATE":
                        job_id = payload.get("job_id")
                        await agent_manager.process_job_update(job_id, payload.get("data", {}), db)

                    elif msg_type == "SSH_OUTPUT":
                        session_id = payload.get("session_id")
                        output_chunk = payload.get("data", "")
                        if session_id and output_chunk:
                            await agent_manager.forward_ssh_output_to_ui(session_id, output_chunk)

            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        agent_manager.disconnect_agent(gpu_id)
    except Exception as e:
        print(f"[WebSocket Agent Error] {e}")
        agent_manager.disconnect_agent(gpu_id)


@router.websocket("/jobs/{job_id}/logs")
async def job_logs_websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    Web UI live streaming endpoint for real-time stdout/stderr from executing container
    """
    await agent_manager.subscribe_ui_job(job_id, websocket)
    try:
        while True:
            # Keep-alive receive
            _ = await websocket.receive_text()
    except WebSocketDisconnect:
        agent_manager.unsubscribe_ui_job(job_id, websocket)
    except Exception:
        agent_manager.unsubscribe_ui_job(job_id, websocket)


@router.websocket("/ssh/terminal/{gpu_id}")
async def ssh_terminal_websocket_endpoint(
    websocket: WebSocket,
    gpu_id: str,
    session_id: str = Query(...)
):
    """
    Interactive Web Terminal bridge for real-time SSH / PTY interaction with GPU host
    """
    # 1. Register Web client
    await agent_manager.register_ssh_ui_client(session_id, gpu_id, websocket)

    # 2. Instruct Agent to spawn/initialize interactive PTY/shell session
    agent_connected = await agent_manager.send_command_to_agent(gpu_id, {
        "action": "START_SSH_SESSION",
        "session_id": session_id,
        "gpu_id": gpu_id
    })

    if not agent_connected:
        try:
            await websocket.send_json({
                "type": "SSH_OUTPUT",
                "session_id": session_id,
                "data": "\r\n\x1b[31m[AI-GPUShare Error] GPU Agent is currently offline or disconnected.\x1b[0m\r\n"
            })
        except Exception:
            pass

    try:
        while True:
            msg_raw = await websocket.receive_text()
            try:
                msg = json.loads(msg_raw)
                msg_type = msg.get("type")
                if msg_type == "SSH_INPUT":
                    input_data = msg.get("data", "")
                    await agent_manager.forward_ssh_input_to_agent(session_id, input_data)
                elif msg_type == "SSH_RESIZE":
                    rows = msg.get("rows", 24)
                    cols = msg.get("cols", 80)
                    await agent_manager.send_command_to_agent(gpu_id, {
                        "action": "SSH_RESIZE",
                        "session_id": session_id,
                        "rows": rows,
                        "cols": cols
                    })
                elif msg_type == "PING":
                    await websocket.send_json({"type": "PONG"})
            except json.JSONDecodeError:
                # Raw text input fallback
                await agent_manager.forward_ssh_input_to_agent(session_id, msg_raw)
    except WebSocketDisconnect:
        agent_manager.unregister_ssh_ui_client(session_id)
    except Exception as e:
        print(f"[SSH Terminal Error] {e}")
        agent_manager.unregister_ssh_ui_client(session_id)
