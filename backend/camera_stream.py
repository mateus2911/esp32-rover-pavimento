import threading
import cv2
import numpy as np


class VideoStreamManager:
    def __init__(
        self,
        simulation_mode: bool = True,
        stream_url: str = "http://192.168.4.1:81/stream",
        reconnect_delay: float = 1.0,
        max_failures_before_reconnect: int = 5,
    ):
        self.simulation_mode = simulation_mode
        self.stream_url = stream_url
        self.reconnect_delay = reconnect_delay
        self.max_failures_before_reconnect = max_failures_before_reconnect
        self._latest_frame: np.ndarray | None = None
        self._lock = threading.Lock()
        self._running = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Inicia a thread em background para captura ou simulação contínua."""
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _generate_simulated_frame(self, frame_count: int) -> np.ndarray:
        """
        Gera um frame falso (QVGA 320x240 ou VGA 640x480) para testar o pipeline sem hardware.
        """
        img = np.zeros((240, 320, 3), dtype=np.uint8)
        pt1 = (0, 0)
        pt2 = (319, 239)
        color = (255, 255, 255)
        thickness = 1

        cv2.rectangle(img, pt1, pt2, color, thickness)
        cv2.putText(
            img,
            f"SIMULACAO | Frame: {frame_count}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            thickness,
        )

        return img

    def _open_capture(self) -> cv2.VideoCapture | None:
        """Abre o stream MJPEG da ESP32 com buffer mínimo para reduzir latência."""
        cap = cv2.VideoCapture(self.stream_url)
        if not cap.isOpened():
            cap.release()
            return None
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _update_loop(self) -> None:
        """Loop executado em thread separada para manter apenas o frame mais recente."""
        frame_count = 0
        consecutive_failures = 0
        cap: cv2.VideoCapture | None = None

        try:
            while self._running:
                if self.simulation_mode:
                    frame = self._generate_simulated_frame(frame_count)
                    frame_count += 1
                    with self._lock:
                        self._latest_frame = frame.copy()
                    self._stop_event.wait(timeout=1 / 30)  # Simula ~30 FPS
                    continue

                if cap is None or not cap.isOpened():
                    if cap is not None:
                        cap.release()
                    cap = self._open_capture()
                    if cap is None:
                        self._stop_event.wait(timeout=self.reconnect_delay)
                        continue
                    consecutive_failures = 0

                ret, frame = cap.read()
                if not ret or frame is None:
                    consecutive_failures += 1
                    if consecutive_failures >= self.max_failures_before_reconnect:
                        cap.release()
                        cap = None
                        consecutive_failures = 0
                        self._stop_event.wait(timeout=self.reconnect_delay)
                    else:
                        self._stop_event.wait(timeout=0.05)
                    continue

                consecutive_failures = 0
                with self._lock:
                    self._latest_frame = frame.copy()
        finally:
            if cap is not None:
                cap.release()

    def get_latest_frame(self) -> np.ndarray | None:
        """Retorna uma cópia do último frame bruto capturado."""
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def get_jpeg_bytes(self) -> bytes | None:
        """Retorna o último frame codificado em JPEG para transmissão MJPEG."""
        frame = self.get_latest_frame()
        if frame is None:
            return None

        success, buffer = cv2.imencode(".jpg", frame)

        if success is True:
            return buffer.tobytes()
        return None
