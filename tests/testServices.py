from pathlib import Path
from threading import Event

import cv2
import numpy as np
import pytest

from face_workbench.config import Settings
from face_workbench.db import (
    Database,
    upgrade_database,
)
from face_workbench.domain import FaceBox
from face_workbench.services import (
    DatasetService,
    JobConflict,
    JobManager,
    NoFaceDetected,
    StorageLayout,
)


class FixedDetector:
    def __init__(self, boxes: list[FaceBox]) -> None:
        self.boxes = boxes

    def detect(self, _: np.ndarray) -> list[FaceBox]:
        return list(self.boxes)


def make_services(tmp_path: Path) -> tuple[Settings, Database, StorageLayout]:
    settings = Settings(
        storage_dir=tmp_path / "storage",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'workbench.sqlite3'}",
    )
    settings.ensure_directories()
    upgrade_database(settings.resolved_database_url)
    return settings, Database(settings.resolved_database_url), StorageLayout(settings.storage_dir)


def test_collection_saves_only_largest_face_and_deduplicates(tmp_path: Path) -> None:
    _, database, layout = make_services(tmp_path)
    detector = FixedDetector([FaceBox(0, 0, 20, 20), FaceBox(30, 20, 50, 50)])
    service = DatasetService(database, layout, detector)
    frame = np.full((120, 120, 3), 200, dtype=np.uint8)

    first = service.collect_face("Alice", frame)
    second = service.collect_face("Alice", frame)

    assert first.saved == 1
    assert first.detected == 2
    assert second.saved == 0
    assert second.duplicates == 1
    assert len(list(layout.dataset_faces.glob("**/*.jpg"))) == 1


def test_collection_reports_missing_face(tmp_path: Path) -> None:
    _, database, layout = make_services(tmp_path)
    service = DatasetService(database, layout, FixedDetector([]))

    with pytest.raises(NoFaceDetected):
        service.collect_face("Alice", np.zeros((80, 80, 3), dtype=np.uint8))


def test_training_data_uses_stable_alphabetical_class_order(tmp_path: Path) -> None:
    _, database, layout = make_services(tmp_path)
    detector = FixedDetector([FaceBox(5, 5, 60, 60)])
    service = DatasetService(database, layout, detector)
    rng = np.random.default_rng(1)
    for name in ("Zoe", "Alice"):
        for _ in range(2):
            service.collect_face(name, rng.integers(0, 255, (80, 80, 3), dtype=np.uint8))

    training_data = service.training_data()

    assert [person.name for person in training_data.persons] == ["Alice", "Zoe"]
    assert training_data.class_indices[:2] == [0, 0]
    assert training_data.class_indices[2:] == [1, 1]


def test_job_manager_records_success_and_rejects_concurrent_start(tmp_path: Path) -> None:
    _, database, _ = make_services(tmp_path)
    manager = JobManager(database)
    started = Event()
    release = Event()

    def worker(context: object) -> dict[str, object]:
        started.set()
        release.wait(timeout=5)
        return {"value": 42}

    submitted = manager.submit("train", {"epochs": 1}, worker)  # type: ignore[arg-type]
    assert started.wait(timeout=5) is True
    with pytest.raises(JobConflict):
        manager.submit("recognize", {}, worker)  # type: ignore[arg-type]
    release.set()
    success = manager.wait_for(submitted.id, timeout=10)

    assert success.status == "succeeded"
    assert success.progress == 100
    assert success.result_json == {"value": 42}


def test_job_manager_records_worker_failure(tmp_path: Path) -> None:
    _, database, _ = make_services(tmp_path)
    manager = JobManager(database)

    def worker(_: object) -> dict[str, object]:
        raise ValueError("bad data")

    job = manager.run_sync("train", {}, worker)  # type: ignore[arg-type]

    assert job.status == "failed"
    assert job.error_code == "job_failed"
    assert "bad data" in (job.error_message or "")


def test_storage_layout_resolves_relative_paths(tmp_path: Path) -> None:
    _, _, layout = make_services(tmp_path)

    path = layout.output_path("job-1", "annotated.jpg")

    assert path.is_absolute()
    assert layout.relative(path) == "outputs/job-1/annotated.jpg"
    assert cv2.imwrite(str(path), np.zeros((2, 2, 3), dtype=np.uint8)) is True
