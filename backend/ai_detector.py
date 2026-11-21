from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from backend.models import Detection

logger = logging.getLogger(__name__)

DEFAULT_LABELS = ("rachadura", "buraco", "desnivel")


class PavementDetector:
    """Detector de falhas no pavimento com suporte a modelo ONNX e modo preview."""

    def __init__(self, model_path: Path, confidence_threshold: float = 0.45) -> None:
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.session = None
        self.input_name: str | None = None
        self.input_size: tuple[int, int] = (320, 320)
        self.backend_name = "preview-opencv"
        self._load_model()

    def _load_model(self) -> None:
        if not self.model_path.exists():
            logger.info(
                "Modelo ONNX não encontrado em %s; usando modo preview OpenCV.",
                self.model_path,
            )
            return

        try:
            import onnxruntime as ort

            self.session = ort.InferenceSession(
                str(self.model_path),
                providers=["CPUExecutionProvider"],
            )
            inputs = self.session.get_inputs()
            if inputs:
                self.input_name = inputs[0].name
                shape = inputs[0].shape
                if len(shape) == 4 and isinstance(shape[2], int) and isinstance(shape[3], int):
                    self.input_size = (shape[3], shape[2])
            self.backend_name = f"onnx:{self.model_path.name}"
            logger.info("Modelo ONNX carregado de %s", self.model_path)
        except Exception as exc:
            logger.warning("Falha ao carregar ONNX (%s); voltando ao preview.", exc)
            self.session = None
            self.backend_name = "preview-opencv"

    def detect(self, frame: np.ndarray) -> tuple[np.ndarray, list[Detection]]:
        """Executa detecção no frame e retorna (frame_anotado, deteccoes)."""
        annotated = frame.copy()
        if self.session is not None and self.input_name is not None:
            detections = self._detect_onnx(frame)
        else:
            detections = self._detect_preview(frame)

        for det in detections:
            x1, y1, x2, y2 = det.bbox
            color = (0, 80, 255) if det.label == "buraco" else (0, 200, 255)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            text = f"{det.label} {det.confidence:.0%}"
            cv2.putText(
                annotated,
                text,
                (x1, max(18, y1 - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
                cv2.LINE_AA,
            )

        return annotated, detections

    def _detect_preview(self, frame: np.ndarray) -> list[Detection]:
        """Heurística simples de preview enquanto o modelo YOLO/ONNX ainda não foi treinado."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        # Regiões bem escuras comparadas ao asfalto ao redor (simulando buraco/trinca)
        _, mask = cv2.threshold(blurred, 55, 255, cv2.THRESH_BINARY_INV)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        h, w = frame.shape[:2]
        detections: list[Detection] = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 350 or area > (w * h * 0.45):
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = max(bw, bh) / max(1, min(bw, bh))
            label = "rachadura" if aspect > 2.4 else "buraco"
            conf = min(0.95, 0.50 + area / 8000.0)
            if conf >= self.confidence_threshold:
                detections.append(
                    Detection(label=label, confidence=round(conf, 2), bbox=(x, y, x + bw, y + bh))
                )
        return detections[:5]

    def _detect_onnx(self, frame: np.ndarray) -> list[Detection]:
        """Inferência padrão para modelos YOLO exportados para ONNX."""
        assert self.session is not None and self.input_name is not None
        in_w, in_h = self.input_size
        orig_h, orig_w = frame.shape[:2]

        resized = cv2.resize(frame, (in_w, in_h))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        blob = np.transpose(rgb, (2, 0, 1))[None, ...]

        outputs = self.session.run(None, {self.input_name: blob})[0]
        preds = np.squeeze(outputs)
        if preds.ndim != 2:
            return []

        # YOLOv8/YOLO11 ONNX padrão: shape (4 + num_classes, num_boxes) -> transpor
        if preds.shape[0] < preds.shape[1]:
            preds = preds.T

        boxes: list[list[int]] = []
        scores: list[float] = []
        class_ids: list[int] = []

        scale_x = orig_w / in_w
        scale_y = orig_h / in_h

        for row in preds:
            if len(row) < 5:
                continue
            cls_scores = row[4:]
            cls_id = int(np.argmax(cls_scores))
            conf = float(cls_scores[cls_id])
            if conf < self.confidence_threshold:
                continue

            cx, cy, bw, bh = row[:4]
            x1 = int((cx - bw / 2) * scale_x)
            y1 = int((cy - bh / 2) * scale_y)
            boxes.append([x1, y1, int(bw * scale_x), int(bh * scale_y)])
            scores.append(conf)
            class_ids.append(cls_id)

        if not boxes:
            return []

        indices = cv2.dnn.NMSBoxes(boxes, scores, self.confidence_threshold, 0.45)
        detections: list[Detection] = []
        for idx in np.array(indices).flatten():
            x, y, bw, bh = boxes[idx]
            cls_id = class_ids[idx]
            label = (
                DEFAULT_LABELS[cls_id]
                if cls_id < len(DEFAULT_LABELS)
                else f"falha_{cls_id}"
            )
            detections.append(
                Detection(
                    label=label,
                    confidence=round(scores[idx], 2),
                    bbox=(max(0, x), max(0, y), min(orig_w, x + bw), min(orig_h, y + bh)),
                )
            )
        return detections
