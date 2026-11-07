from pathlib import Path

import cv2
import numpy as np

from face_workbench.config import Settings
from face_workbench.db import (
    Database,
    get_active_model,
    get_or_create_default_dataset,
    get_or_create_person,
    list_models,
    register_model,
    upgrade_database,
)
from face_workbench.domain import FaceBox
from face_workbench.ml import ModelBundle, TrainingOptions, TrainingResult
from face_workbench.services import DatasetService, StorageLayout
from face_workbench.services.recognition import RecognitionService
from face_workbench.services.training import TrainingService


class FixedDetector:
    def __init__(self, boxes: list[FaceBox]) -> None:
        self.boxes = boxes

    def detect(self, _: np.ndarray) -> list[FaceBox]:
        return list(self.boxes)


class FixedProbabilityModel:
    def __init__(self, probabilities: list[float]) -> None:
        self.probabilities = probabilities

    def predict(self, _: np.ndarray, verbose: int = 0) -> np.ndarray:
        assert verbose == 0
        return np.array([self.probabilities], dtype=np.float32)


class FakeTrainer:
    def __init__(self, root: Path) -> None:
        self.root = root

    def train(
        self,
        *,
        images: np.ndarray,
        class_indices: list[int],
        labels: list[str],
        artifact_dir: Path,
        options: TrainingOptions,
        threshold: float,
    ) -> TrainingResult:
        assert images.shape[0] == len(class_indices)
        assert len(labels) == 2
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "model.keras").write_bytes(b"fake")
        return TrainingResult(
            artifact_dir=artifact_dir,
            metrics={"accuracy": 0.8},
            labels=tuple(labels),
            threshold=threshold,
            input_size=options.input_size,
        )


def make_stack(tmp_path: Path) -> tuple[Database, StorageLayout]:
    settings = Settings(
        storage_dir=tmp_path / "storage",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'workbench.sqlite3'}",
    )
    settings.ensure_directories()
    upgrade_database(settings.resolved_database_url)
    return Database(settings.resolved_database_url), StorageLayout(settings.storage_dir)


def test_training_service_registers_and_activates_first_model(tmp_path: Path) -> None:
    database, layout = make_stack(tmp_path)
    datasets = DatasetService(
        database,
        layout,
        FixedDetector([FaceBox(0, 0, 60, 60)]),
    )
    rng = np.random.default_rng(4)
    for name in ("Alice", "Bob"):
        for _ in range(2):
            datasets.collect_face(name, rng.integers(0, 255, (70, 70, 3), dtype=np.uint8))
    progress: list[int] = []
    service = TrainingService(
        database,
        layout,
        datasets,
        trainer=FakeTrainer(tmp_path),
    )

    result = service.train(
        options=TrainingOptions(epochs=1, batch_size=2),
        threshold=0.7,
        progress=lambda value, _: progress.append(value),
    )

    with database.session() as session:
        models = list_models(session)
        active = get_active_model(session)

    assert result.metrics["accuracy"] == 0.8
    assert len(models) == 1
    assert active is not None
    assert [label.person_name for label in active.labels] == ["Alice", "Bob"]
    assert progress == [10, 90]


def test_recognition_predicts_every_face_and_writes_annotated_photo(tmp_path: Path) -> None:
    database, layout = make_stack(tmp_path)
    with database.session() as session:
        dataset = get_or_create_default_dataset(session)
        alice = get_or_create_person(session, dataset.id, "Alice")
        bob = get_or_create_person(session, dataset.id, "Bob")
        model = register_model(
            session,
            dataset.id,
            artifact_path="models/fake/model.keras",
            labels=[alice, bob],
            metrics={"accuracy": 0.8},
            threshold=0.7,
        )
        model_id = model.id

    bundle = ModelBundle(
        model=FixedProbabilityModel([0.1, 0.9]),
        labels=("Alice", "Bob"),
        threshold=0.7,
        input_size=128,
    )
    service = RecognitionService(
        database,
        layout,
        FixedDetector([FaceBox(5, 5, 50, 50), FaceBox(70, 10, 40, 40)]),
        bundle_loader=lambda _: bundle,
    )
    frame = np.full((140, 140, 3), 200, dtype=np.uint8)
    success, encoded = cv2.imencode(".jpg", frame)
    assert success

    result = service.recognize_photo(model_id, encoded.tobytes(), output_id="job-1")

    assert len(result.predictions) == 2
    assert {prediction.label for prediction in result.predictions} == {"Bob"}
    assert (layout.root / result.output_path).is_file()
