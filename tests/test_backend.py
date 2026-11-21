from pathlib import Path
import time

import numpy as np
from fastapi.testclient import TestClient

from backend.ai_detector import PavementDetector
from backend.config import settings
from backend.main import app


def test_health_and_status() -> None:
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}

        # Aguarda um ciclo curto do gerador mock
        time.sleep(0.15)
        status = client.get("/api/status")
        assert status.status_code == 200
        payload = status.json()
        assert payload["mock_mode"] is True
        assert payload["stream_connected"] is True


def test_websocket_control_and_emergency_stop() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws/control") as ws:
            ws.send_json({"left": 180, "right": 180})
            ack = ws.receive_json()
            assert ack["ack"] is True
            assert ack["left"] == 180
            assert ack["right"] == 180

        stop_res = client.post("/api/emergency_stop")
        assert stop_res.status_code == 200
        assert stop_res.json() == {"status": "stopped"}

        status = client.get("/api/status").json()
        assert status["last_command"] == {"left": 0, "right": 0}


def test_snapshot_saves_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "capture_dir", tmp_path)
    with TestClient(app) as client:
        time.sleep(0.15)
        res = client.post("/api/snapshot")
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True
        assert Path(body["path"]).exists()


def test_detector_preview_on_synthetic_pothole() -> None:
    detector = PavementDetector(Path("nao_existe.onnx"), confidence_threshold=0.45)
    frame = np.full((240, 320, 3), 120, dtype=np.uint8)
    frame[80:140, 110:190] = 20  # região escura simulando buraco
    annotated, detections = detector.detect(frame)
    assert annotated.shape == frame.shape
    assert len(detections) >= 1
