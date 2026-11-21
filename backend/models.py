from pydantic import BaseModel, Field


class DriveCommand(BaseModel):
    """Comando diferencial dos motores enviado ao rover (-255 a 255)."""

    left: int = Field(default=0, ge=-255, le=255)
    right: int = Field(default=0, ge=-255, le=255)


class Detection(BaseModel):
    """Detecção de falha no pavimento."""

    label: str
    confidence: float
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)


class RoverStatus(BaseModel):
    """Estado atual da conexão, stream e detector."""

    mock_mode: bool
    ai_enabled: bool
    detector_backend: str
    stream_connected: bool
    esp32_connected: bool
    fps: float
    last_command: DriveCommand
    detections: list[Detection]
