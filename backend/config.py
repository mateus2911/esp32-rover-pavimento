from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações da aplicação carregadas de variáveis de ambiente (.env)."""

    model_config = SettingsConfigDict(
        env_prefix="ROVER_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mock_mode: bool = True
    esp32_stream_url: str = "http://192.168.4.1:81/stream"
    esp32_ws_url: str = "ws://192.168.4.1:82"
    model_path: Path = Path("ai/models/pavement_yolov8n.onnx")
    confidence_threshold: float = 0.45
    capture_dir: Path = Path("ai/dataset/raw")


settings = Settings()
