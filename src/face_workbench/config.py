from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="FACE_WORKBENCH_",
        extra="ignore",
    )

    host: str = "127.0.0.1"
    port: int = 8000
    storage_dir: Path = Field(default_factory=lambda: PROJECT_ROOT / "storage")
    database_url: str | None = None
    threshold: float = 0.7
    image_size: int = 128
    camera_frame_edge: int = 960
    max_image_bytes: int = 20 * 1024 * 1024
    max_video_bytes: int = 500 * 1024 * 1024

    @property
    def resolved_database_url(self) -> str:
        default_database = self.storage_dir / "face_workbench.sqlite3"
        return self.database_url or f"sqlite+pysqlite:///{default_database}"

    def ensure_directories(self) -> None:
        for name in ("datasets", "models", "uploads", "outputs"):
            (self.storage_dir / name).mkdir(parents=True, exist_ok=True)
