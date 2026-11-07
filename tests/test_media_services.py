from pathlib import Path

import cv2
import numpy as np

from face_workbench.config import Settings
from face_workbench.db import Database, upgrade_database
from face_workbench.domain import FaceBox
from face_workbench.ml import ModelBundle
from face_workbench.services import DatasetService, StorageLayout
from face_workbench.services.importer import LegacyImporter
from face_workbench.services.media import MediaService


class FixedDetector:
    def __init__(self, boxes: list[FaceBox]) -> None:
        self.boxes = boxes

    def detect(self, _: np.ndarray) -> list[FaceBox]:
        return list(self.boxes)


class FixedProbabilityModel:
    def predict(self, _: np.ndarray, verbose: int = 0) -> np.ndarray:
        assert verbose == 0
        return np.array([[0.2, 0.8]], dtype=np.float32)


def make_stack(tmp_path: Path) -> tuple[Database, StorageLayout]:
    settings = Settings(
        storage_dir=tmp_path / "storage",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'workbench.sqlite3'}",
    )
    settings.ensure_directories()
    upgrade_database(settings.resolved_database_url)
    return Database(settings.resolved_database_url), StorageLayout(settings.storage_dir)


def write_video(path: Path, frames: int = 5) -> None:
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        5.0,
        (80, 80),
    )
    assert writer.isOpened()
    rng = np.random.default_rng(7)
    try:
        for _ in range(frames):
            writer.write(rng.integers(0, 255, (80, 80, 3), dtype=np.uint8))
    finally:
        writer.release()


def test_video_collection_samples_frames(tmp_path: Path) -> None:
    _, layout = make_stack(tmp_path)
    database = Database(f"sqlite+pysqlite:///{tmp_path / 'workbench.sqlite3'}")
    datasets = DatasetService(database, layout, FixedDetector([FaceBox(5, 5, 50, 50)]))
    video = tmp_path / "sample.mp4"
    write_video(video)
    service = MediaService(datasets)
    progress: list[int] = []

    result = service.collect_from_video(
        "Alice",
        video,
        sample_interval=2,
        target=10,
        progress=lambda value, _: progress.append(value),
    )

    assert result.saved >= 2
    assert progress[-1] == 95


def test_video_recognition_writes_annotation(tmp_path: Path) -> None:
    database, layout = make_stack(tmp_path)
    datasets = DatasetService(database, layout, FixedDetector([FaceBox(5, 5, 50, 50)]))
    service = MediaService(datasets)
    video = tmp_path / "sample.mp4"
    write_video(video, frames=3)
    bundle = ModelBundle(
        model=FixedProbabilityModel(),
        labels=("Alice", "Bob"),
        threshold=0.7,
        input_size=128,
    )

    result = service.recognize_video(
        bundle,
        video,
        output_id="video-job",
        progress=lambda value, _: None,
    )

    assert result.frames_processed == 3
    assert result.prediction_count == 3
    assert (layout.root / result.output_path).is_file()


def test_legacy_import_copies_faces_without_editing_sources(tmp_path: Path) -> None:
    database, layout = make_stack(tmp_path)
    datasets = DatasetService(database, layout, FixedDetector([FaceBox(2, 2, 50, 50)]))
    source = tmp_path / "legacy"
    for index, name in enumerate(("Alice", "Bob")):
        directory = source / name
        directory.mkdir(parents=True)
        image = np.full((70, 70, 3), 120 + index * 10, dtype=np.uint8)
        assert cv2.imwrite(str(directory / "face.jpg"), image) is True
    before = {path: path.stat().st_mtime_ns for path in source.rglob("*") if path.is_file()}
    result = LegacyImporter(datasets).import_from(source)

    assert result.imported == 2
    assert result.missing_face == 0
    assert before == {path: path.stat().st_mtime_ns for path in source.rglob("*") if path.is_file()}
