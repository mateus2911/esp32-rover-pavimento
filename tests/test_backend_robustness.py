import asyncio
from pathlib import Path
from types import SimpleNamespace
import cv2
import numpy as np
from fastapi.testclient import TestClient
from backend import camera_stream, main, rover_bridge as rb_module
from backend.config import PROJECT_ROOT, Settings


def test_settings_load_from_env_vars(monkeypatch, tmp_path):
    monkeypatch.setenv("ROVER_MOCK_MODE", "false")
    monkeypatch.setenv("ROVER_ESP32_STREAM_URL", "http://10.0.0.5:81/stream")
    monkeypatch.setenv("ROVER_ESP32_WS_URL", "ws://10.0.0.5:82")
    monkeypatch.setenv("ROVER_MODEL_PATH", "ai/models/custom.onnx")
    monkeypatch.setenv("ROVER_CONFIDENCE_THRESHOLD", "0.62")
    monkeypatch.setenv("ROVER_CAPTURE_DIR", str(tmp_path))

    cfg = Settings(_env_file=None)
    assert cfg.mock_mode is False
    assert cfg.esp32_stream_url == "http://10.0.0.5:81/stream"
    assert cfg.esp32_ws_url == "ws://10.0.0.5:82"
    assert cfg.resolved_model_path == PROJECT_ROOT / "ai/models/custom.onnx"
    assert cfg.confidence_threshold == 0.62
    assert cfg.resolved_capture_dir == tmp_path


def test_settings_load_local_dotenv():
    env_file = PROJECT_ROOT / ".env"
    assert env_file.is_file()
    cfg = Settings(_env_file=env_file)
    assert cfg.esp32_stream_url == "http://192.168.4.1:81/stream"
    assert cfg.esp32_ws_url == "ws://192.168.4.1:82"
    assert cfg.resolved_capture_dir == PROJECT_ROOT / "ai/dataset/raw"


def test_video_stream_reconnects_and_sets_buffersize(monkeypatch):
    created_caps = []
    sample_frame = np.zeros((240, 320, 3), dtype=np.uint8)

    class FakeCapture:
        def __init__(self, url: str):
            self.url = url
            self.index = len(created_caps)
            self.props = {}
            self.released = False
            self.reads = 0
            created_caps.append(self)

        def isOpened(self) -> bool:
            # Primeira tentativa falha ao abrir; segunda abre com sucesso
            return self.index >= 1

        def set(self, prop, value):
            self.props[prop] = value
            return True

        def read(self):
            self.reads += 1
            if self.index == 1 and self.reads <= 2:
                # Simula queda após abrir na segunda instância
                return False, None
            return True, sample_frame

        def release(self):
            self.released = True

    monkeypatch.setattr(camera_stream.cv2, "VideoCapture", FakeCapture)

    manager = camera_stream.VideoStreamManager(
        simulation_mode=False,
        stream_url="http://192.168.4.1:81/stream",
        reconnect_delay=0.02,
        max_failures_before_reconnect=2,
    )
    manager.start()
    try:
        import time

        deadline = time.time() + 2.0
        while manager.get_latest_frame() is None and time.time() < deadline:
            time.sleep(0.02)

        assert manager.get_latest_frame() is not None
        assert len(created_caps) >= 3
        assert created_caps[0].released is True
        assert created_caps[1].released is True
        assert created_caps[-1].props.get(cv2.CAP_PROP_BUFFERSIZE) == 1
    finally:
        manager.stop()

    assert created_caps[-1].released is True


def test_rover_bridge_reuses_persistent_ws_and_reconnects(monkeypatch):
    connections = []

    class FakeWS:
        def __init__(self, fail_on_second_send: bool = False):
            self.open = True
            self.sent = []
            self.closed = False
            self.fail_on_second_send = fail_on_second_send

        async def send(self, msg: str):
            if self.fail_on_second_send and len(self.sent) >= 1:
                self.open = False
                raise RuntimeError("Conexão perdida")
            self.sent.append(msg)

        async def close(self):
            self.open = False
            self.closed = True

    async def fake_connect(url, **kwargs):
        idx = len(connections)
        ws = FakeWS(fail_on_second_send=(idx == 0))
        connections.append(ws)
        return ws

    monkeypatch.setattr(rb_module.websockets, "connect", fake_connect)

    async def run():
        bridge = rb_module.RoverBridge(simulation_mode=False, esp32_ws_url="ws://192.168.4.1:82")
        await bridge.send_command(120, 120)
        await bridge.send_command(200, -200)
        await bridge.send_command(0, 0)
        await bridge.close()

    asyncio.run(run())

    # Primeira conexão falhou no 2º envio e reconectou; 3º envio reutilizou a 2ª conexão
    assert len(connections) == 2
    assert connections[0].closed is True
    assert len(connections[0].sent) == 1
    assert len(connections[1].sent) == 2
    assert connections[1].closed is True


def test_mjpeg_generator_stops_on_disconnect_and_streams_content_length():
    class FakeRequest:
        def __init__(self):
            self.calls = 0

        async def is_disconnected(self) -> bool:
            self.calls += 1
            return self.calls > 1

    async def run():
        req = FakeRequest()
        main.stream_manager.start()
        try:
            # Garante ao menos 1 frame pronto
            while main.stream_manager.get_latest_frame() is None:
                await asyncio.sleep(0.02)

            chunks = []
            async for chunk in main.mjpeg_generator(req):
                chunks.append(chunk)
            return chunks
        finally:
            main.stream_manager.stop()

    chunks = asyncio.run(run())
    assert len(chunks) == 1
    assert b"Content-Length:" in chunks[0]

    with TestClient(main.app) as client:
        with client.stream("GET", "/video_feed") as resp:
            assert resp.status_code == 200
            first_bytes = next(resp.iter_bytes())
            assert b"Content-Length:" in first_bytes
