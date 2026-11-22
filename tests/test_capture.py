import time
from fastapi.testclient import TestClient
from backend import main


def test_capture_endpoints_save_raw_frame(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "CAPTURE_DIR", tmp_path)

    with TestClient(main.app) as client:
        # Aguarda o thread de simulação produzir pelo menos 1 frame
        deadline = time.time() + 2.0
        while main.stream_manager.get_latest_frame() is None and time.time() < deadline:
            time.sleep(0.05)

        initial = client.get("/api/captures")
        assert initial.status_code == 200
        assert initial.json()["total_captures"] == 0

        resp = client.post("/api/capture")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["status"] == "ok"
        assert payload["filename"].endswith(".jpg")
        assert payload["total_captures"] == 1
        assert (tmp_path / payload["filename"]).is_file()

        after = client.get("/api/captures")
        assert after.status_code == 200
        assert after.json()["total_captures"] == 1


def test_capture_returns_503_when_no_frame(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "CAPTURE_DIR", tmp_path)

    with TestClient(main.app) as client:
        monkeypatch.setattr(main.stream_manager, "get_latest_frame", lambda: None)
        resp = client.post("/api/capture")
        assert resp.status_code == 503
