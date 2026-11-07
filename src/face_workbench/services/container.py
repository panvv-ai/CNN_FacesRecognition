from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from face_workbench.config import Settings
from face_workbench.db import Database, upgrade_database
from face_workbench.ml import ModelBundle
from face_workbench.services.datasets import DatasetService
from face_workbench.services.jobs import JobManager
from face_workbench.services.media import MediaService
from face_workbench.services.recognition import RecognitionService
from face_workbench.services.storage import StorageLayout
from face_workbench.services.training import TrainingService
from face_workbench.vision import FaceDetector


class AppServices:
    def __init__(
        self,
        settings: Settings,
        *,
        detector: FaceDetector | object | None = None,
        trainer: object | None = None,
        bundle_loader: Callable[[Path], ModelBundle] | None = None,
    ) -> None:
        settings.ensure_directories()
        upgrade_database(settings.resolved_database_url)
        self.settings = settings
        self.database = Database(settings.resolved_database_url)
        self.layout = StorageLayout(settings.storage_dir)
        self.detector = detector or FaceDetector()
        self.datasets = DatasetService(
            self.database,
            self.layout,
            self.detector,  # type: ignore[arg-type]
            image_size=settings.image_size,
        )
        self.training = TrainingService(
            self.database,
            self.layout,
            self.datasets,
            trainer=trainer,
        )
        options: dict[str, object] = {"image_size": settings.image_size}
        if bundle_loader is not None:
            options["bundle_loader"] = bundle_loader
        self.recognition = RecognitionService(
            self.database,
            self.layout,
            self.detector,  # type: ignore[arg-type]
            **options,  # type: ignore[arg-type]
        )
        self.media = MediaService(self.datasets)
        self.jobs = JobManager(self.database)

    def close(self) -> None:
        self.database.close()
