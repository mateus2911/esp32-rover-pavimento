from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Configurações centralizadas do backend carregadas do ambiente e do arquivo .env."""

    model_config = SettingsConfigDict(
        env_prefix="ROVER_",
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mock_mode: bool = True
    esp32_stream_url: str = "http://192.168.4.1:81/stream"
    esp32_ws_url: str = "ws://192.168.4.1:82"
    model_path: Path = Path("ai/models/pavement_yolov8n.onnx")
    confidence_threshold: float = Field(default=0.45, ge=0.0, le=1.0)
    capture_dir: Path = Path("ai/dataset/raw")

    @property
    def frontend_dir(self) -> Path:
        return PROJECT_ROOT / "frontend"

    @property
    def resolved_model_path(self) -> Path:
        return self.model_path if self.model_path.is_absolute() else PROJECT_ROOT / self.model_path

    @property
    def resolved_capture_dir(self) -> Path:
        return self.capture_dir if self.capture_dir.is_absolute() else PROJECT_ROOT / self.capture_dir


settings = Settings()
