from __future__ import annotations

import logging
import threading
import time

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class CameraStream:
    """Captura assíncrona do stream MJPEG da ESP32 ou gerador sintético em modo simulação."""

    def __init__(self, stream_url: str, mock_mode: bool = True) -> None:
        self.stream_url = stream_url
        self.mock_mode = mock_mode
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self.connected = False
        self.fps = 0.0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        target = self._mock_loop if self.mock_mode else self._esp32_loop
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self.connected = False

    def get_latest_frame(self) -> np.ndarray | None:
        with self._lock:
            return None if self._frame is None else self._frame.copy()

    def _update_frame(self, frame: np.ndarray, last_ts: float) -> float:
        now = time.monotonic()
        dt = max(1e-3, now - last_ts)
        instant_fps = 1.0 / dt
        self.fps = round(0.85 * self.fps + 0.15 * instant_fps, 1) if self.fps else round(instant_fps, 1)
        with self._lock:
            self._frame = frame
        return now

    def _mock_loop(self) -> None:
        """Gera uma pista de asfalto sintética em movimento com falhas simuladas."""
        self.connected = True
        rng = np.random.default_rng(42)
        base_noise = rng.integers(85, 115, size=(480, 640, 3), dtype=np.uint8)
        offset = 0
        last_ts = time.monotonic()

        while self._running:
            frame = base_noise.copy()
            # Faixas laterais de pavimento
            cv2.line(frame, (70, 0), (40, 480), (200, 200, 200), 3)
            cv2.line(frame, (570, 0), (600, 480), (200, 200, 200), 3)

            # Buraco sintético descendo pela pista
            pothole_y = (offset * 4) % 560 - 40
            if 20 < pothole_y < 440:
                cv2.ellipse(frame, (260, pothole_y), (42, 26), 15, 0, 360, (25, 25, 28), -1)

            # Rachadura sintética
            crack_y = (offset * 4 + 260) % 560 - 40
            if 20 < crack_y < 440:
                pts = np.array(
                    [
                        [390, crack_y],
                        [430, crack_y + 12],
                        [465, crack_y + 6],
                        [505, crack_y + 20],
                    ],
                    dtype=np.int32,
                )
                cv2.polylines(frame, [pts], False, (30, 30, 32), 4)

            cv2.putText(
                frame,
                "MODO SIMULACAO (ESP32 OFF)",
                (14, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (180, 230, 255),
                1,
                cv2.LINE_AA,
            )

            offset += 1
            last_ts = self._update_frame(frame, last_ts)
            time.sleep(1.0 / 24.0)

    def _esp32_loop(self) -> None:
        """Lê frames continuamente do endpoint MJPEG da ESP32-WROVER."""
        while self._running:
            cap = cv2.VideoCapture(self.stream_url)
            if not cap.isOpened():
                self.connected = False
                logger.warning("Aguardando stream da ESP32 em %s...", self.stream_url)
                time.sleep(1.5)
                continue

            self.connected = True
            last_ts = time.monotonic()
            logger.info("Stream conectado: %s", self.stream_url)

            try:
                while self._running:
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        self.connected = False
                        break
                    last_ts = self._update_frame(frame, last_ts)
            finally:
                cap.release()
                self.connected = False
                time.sleep(0.5)
