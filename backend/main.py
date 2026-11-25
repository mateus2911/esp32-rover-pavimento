import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
import cv2
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from backend.camera_stream import VideoStreamManager
from backend.config import PROJECT_ROOT, settings
from backend.rover_bridge import RoverBridge

FRONTEND_DIR = settings.frontend_dir
CAPTURE_DIR = settings.resolved_capture_dir

stream_manager = VideoStreamManager(
    simulation_mode=settings.mock_mode,
    stream_url=settings.esp32_stream_url,
)
rover_bridge = RoverBridge(
    simulation_mode=settings.mock_mode,
    esp32_ws_url=settings.esp32_ws_url,
)


def _count_captured_images(capture_dir: Path) -> int:
    if not capture_dir.exists():
        return 0
    return sum(
        1 for p in capture_dir.iterdir()
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    stream_manager.start()
    try:
        yield
    finally:
        await rover_bridge.close()
        stream_manager.stop()


app = FastAPI(title="Rover Inspeção de Pavimento", lifespan=lifespan)


async def mjpeg_generator(request: Request):
    """Gerador assíncrono que empacota cada frame JPEG no padrão multipart HTTP."""
    try:
        while stream_manager.is_running:
            if await request.is_disconnected():
                break

            jpeg_bytes = stream_manager.get_jpeg_bytes()
            if jpeg_bytes is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    + f"Content-Length: {len(jpeg_bytes)}\r\n\r\n".encode("ascii")
                    + jpeg_bytes
                    + b"\r\n"
                )

            await asyncio.sleep(0.03)
    except asyncio.CancelledError:
        return


@app.get("/video_feed")
async def video_feed(request: Request):
    return StreamingResponse(
        mjpeg_generator(request),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


@app.get("/api/status")
async def get_status():
    return {
        "mock_mode": settings.mock_mode,
        "stream_url": settings.esp32_stream_url,
        "ws_url": settings.esp32_ws_url,
        "stream_running": stream_manager.is_running,
        "stream_connected": stream_manager.is_connected,
        "esp32_ws_connected": rover_bridge.is_connected,
        "total_captures": _count_captured_images(CAPTURE_DIR),
    }


@app.get("/api/captures")
async def list_captures():
    return {
        "capture_dir": str(CAPTURE_DIR.relative_to(PROJECT_ROOT)) if CAPTURE_DIR.is_relative_to(PROJECT_ROOT) else str(CAPTURE_DIR),
        "total_captures": _count_captured_images(CAPTURE_DIR),
    }


@app.post("/api/capture")
async def capture_frame():
    frame = stream_manager.get_latest_frame()
    if frame is None:
        raise HTTPException(status_code=503, detail="Nenhum frame disponível para captura.")

    CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"frame_{timestamp}.jpg"
    output_path = CAPTURE_DIR / filename

    success = await asyncio.to_thread(cv2.imwrite, str(output_path), frame)
    if not success:
        raise HTTPException(status_code=500, detail="Falha ao gravar imagem capturada em disco.")

    return {
        "status": "ok",
        "filename": filename,
        "path": str(output_path.relative_to(PROJECT_ROOT)) if output_path.is_relative_to(PROJECT_ROOT) else str(output_path),
        "total_captures": _count_captured_images(CAPTURE_DIR),
    }


@app.websocket("/ws/control")
async def websocket_control(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if not isinstance(data, dict):
                continue
            left = data.get("left", 0)
            right = data.get("right", 0)
            await rover_bridge.send_command(left, right)
    except WebSocketDisconnect:
        # Segurança: se o operador fechar a aba ou perder conexão com o servidor, pare os motores
        await rover_bridge.send_command(0, 0)


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
