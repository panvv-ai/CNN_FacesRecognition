from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from face_workbench.db import (
    Database,
    get_active_model,
    get_or_create_default_dataset,
    register_model,
    set_active_model,
)
from face_workbench.ml import CnnTrainer, InsufficientTrainingData, TrainingOptions
from face_workbench.services.datasets import DatasetService
from face_workbench.services.storage import StorageLayout


@dataclass(frozen=True, slots=True)
class TrainingSummary:
    model_id: str
    labels: tuple[str, ...]
    metrics: dict[str, float]
    artifact_path: str


class TrainingService:
    def __init__(
        self,
        database: Database,
        layout: StorageLayout,
        datasets: DatasetService,
        *,
        trainer: CnnTrainer | object | None = None,
    ) -> None:
        self.database = database
        self.layout = layout
        self.datasets = datasets
        self.trainer = trainer or CnnTrainer()

    def train(
        self,
        *,
        options: TrainingOptions | None = None,
        threshold: float = 0.7,
        progress: Callable[[int, str], None] | None = None,
    ) -> TrainingSummary:
        training_data = self.datasets.training_data()
        if not training_data.images.size:
            raise InsufficientTrainingData("当前数据集没有可用于训练的人脸")
        labels = [person.name for person in training_data.persons]
        if progress is not None:
            progress(10, "读取训练数据")

        from uuid import uuid4

        model_id = str(uuid4())
        artifact_dir = self.layout.model_dir(model_id)
        result = self.trainer.train(  # type: ignore[attr-defined]
            images=training_data.images,
            class_indices=training_data.class_indices,
            labels=labels,
            artifact_dir=artifact_dir,
            options=options or TrainingOptions(),
            threshold=threshold,
        )
        if progress is not None:
            progress(90, "保存模型与标签映射")
        artifact_path = artifact_dir / "model.keras"
        with self.database.session() as session:
            dataset = get_or_create_default_dataset(session)
            model = register_model(
                session,
                dataset.id,
                artifact_path=self.layout.relative(artifact_path),
                labels=training_data.persons,
                metrics=result.metrics,
                threshold=threshold,
            )
            if get_active_model(session) is None:
                set_active_model(session, model.id)
        return TrainingSummary(
            model_id=model.id,
            labels=result.labels,
            metrics=result.metrics,
            artifact_path=self.layout.relative(artifact_path),
        )
