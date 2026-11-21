from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import time

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from backend.ai_detector import PavementDetector
from backend.camera_stream import CameraStream
from backend.config import settings
from backend.esp32_client import Esp32ControlClient
from backend.models import Detection, DriveCommand, RoverStatus

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


class AppState:
    def __init__(self) -> None:
        self.camera = CameraStream(settings.esp32_stream_url, mock_mode=settings.mock_mode)
        self.detector = PavementDetector(
            settings.model_path,
            confidence_threshold=settings.confidence_threshold,
        )
        self.esp32 = Esp32ControlClient(settings.esp32_ws_url, mock_mode=settings.mock_mode)
        self.ai_enabled = True
        self.latest_detections: list[Detection] = []


state = AppState()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.capture_dir.mkdir(parents=True, exist_ok=True)
    state.camera.start()
    try:
        yield
    finally:
        await state.esp32.emergency_stop()
        await state.esp32.close()
        state.camera.stop()


app = FastAPI(title="Rover de Inspeção de Pavimento", lifespan=lifespan)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/status", response_model=RoverStatus)
async def get_status() -> RoverStatus:
    return RoverStatus(
        mock_mode=settings.mock_mode,
        ai_enabled=state.ai_enabled,
        detector_backend=state.detector.backend_name,
        stream_connected=state.camera.connected,
        esp32_connected=state.esp32.connected,
        fps=state.camera.fps,
        last_command=state.esp32.last_command,
        detections=state.latest_detections,
    )


@app.post("/api/ai/toggle")
async def toggle_ai(enabled: bool | None = None) -> dict[str, bool]:
    state.ai_enabled = (not state.ai_enabled) if enabled is None else enabled
    if not state.ai_enabled:
        state.latest_detections = []
    return {"ai_enabled": state.ai_enabled}


@app.post("/api/snapshot")
async def save_snapshot() -> JSONResponse:
    """Salva o frame bruto atual (sem anotações) para compor o dataset de treino."""
    frame = state.camera.get_latest_frame()
    if frame is None:
        return JSONResponse({"ok": False, "error": "Nenhum frame disponível"}, status_code=503)

    settings.capture_dir.mkdir(parents=True, exist_ok=True)
    filename = f"frame_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    out_path = settings.capture_dir / filename
    cv2.imwrite(str(out_path), frame)
    return JSONResponse({"ok": True, "path": str(out_path)})


@app.post("/api/emergency_stop")
async def emergency_stop() -> dict[str, str]:
    await state.esp32.emergency_stop()
    return {"status": "stopped"}


def _mjpeg_generator():
    while True:
        frame = state.camera.get_latest_frame()
        if frame is None:
            time.sleep(0.05)
            continue

        if state.ai_enabled:
            output_frame, detections = state.detector.detect(frame)
            state.latest_detections = detections
        else:
            output_frame = frame

        ok, encoded = cv2.imencode(".jpg", output_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            continue

        jpg_bytes = encoded.tobytes()
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpg_bytes + b"\r\n"
        )
        time.sleep(0.03)


@app.get("/video_feed")
async def video_feed() -> StreamingResponse:
    return StreamingResponse(
        _mjpeg_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.websocket("/ws/control")
async def control_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = await websocket.receive_json()
            cmd = DriveCommand(**payload)
            await state.esp32.send_command(cmd)
            await websocket.send_json(
                {
                    "ack": True,
                    "left": cmd.left,
                    "right": cmd.right,
                    "esp32_connected": state.esp32.connected,
                }
            )
            await asyncio.sleep(0)
    except WebSocketDisconnect:
        await state.esp32.emergency_stop()
