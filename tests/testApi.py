from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np
from fastapi.testclient import TestClient

from face_workbench.api import create_app
from face_workbench.config import Settings
from face_workbench.db import (
    get_or_create_default_dataset,
    get_or_create_person,
    register_model,
    set_active_model,
)
from face_workbench.domain import FaceBox
from face_workbench.ml import ModelBundle, TrainingResult


class FixedDetector:
    def __init__(self, boxes: list[FaceBox] | None = None) -> None:
        self.boxes = boxes or [FaceBox(5, 5, 60, 60)]

    def detect(self, _: np.ndarray) -> list[FaceBox]:
        return list(self.boxes)


class FixedProbabilityModel:
    def predict(self, _: np.ndarray, verbose: int = 0) -> np.ndarray:
        assert verbose == 0
        return np.array([[0.1, 0.9]], dtype=np.float32)


class FakeTrainer:
    def train(
        self,
        *,
        images: np.ndarray,
        class_indices: list[int],
        labels: list[str],
        artifact_dir: Path,
        options: object,
        threshold: float,
    ) -> TrainingResult:
        artifact_dir.mkdir(parents=True, exist_ok=True)
        (artifact_dir / "model.keras").write_bytes(b"fake")
        return TrainingResult(
            artifact_dir=artifact_dir,
            metrics={"accuracy": 0.8},
            labels=tuple(labels),
            threshold=threshold,
            input_size=128,
        )


def make_app(tmp_path: Path) -> tuple[TestClient, object, FixedDetector]:
    settings = Settings(
        storage_dir=tmp_path / "storage",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'workbench.sqlite3'}",
    )
    detector = FixedDetector()
    bundle = ModelBundle(
        model=FixedProbabilityModel(),
        labels=("Alice", "Bob"),
        threshold=0.7,
        input_size=128,
    )
    app = create_app(
        settings,
        detector=detector,  # type: ignore[arg-type]
        trainer=FakeTrainer(),
        bundle_loader=lambda _: bundle,
    )
    return TestClient(app), app, detector


def image_bytes(value: int = 180) -> bytes:
    image = np.full((100, 100, 3), value, dtype=np.uint8)
    success, encoded = cv2.imencode(".jpg", image)
    assert success
    return encoded.tobytes()


def wait_job(client: TestClient, job_id: str) -> dict[str, object]:
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        response = client.get(f"/api/jobs/{job_id}")
        payload = response.json()
        if payload["status"] in {"succeeded", "failed", "interrupted"}:
            return payload
        time.sleep(0.05)
    raise AssertionError("job did not finish")


def test_bootstrap_and_person_creation(tmp_path: Path) -> None:
    client, _, _ = make_app(tmp_path)

    bootstrap = client.get("/api/bootstrap")
    created = client.post("/api/dataset/persons", json={"name": "Alice"})

    assert bootstrap.status_code == 200
    assert bootstrap.json()["dataset"]["totalFaces"] == 0
    assert created.status_code == 201
    assert created.json()["name"] == "Alice"


def test_photo_collection_job(tmp_path: Path) -> None:
    client, _, _ = make_app(tmp_path)
    client.post("/api/dataset/persons", json={"name": "Alice"})

    response = client.post(
        "/api/jobs/collect",
        data={"person": "Alice", "source": "photo"},
        files=[("files", ("face.jpg", image_bytes(), "image/jpeg"))],
    )
    job = wait_job(client, response.json()["id"])

    assert response.status_code == 202
    assert job["status"] == "succeeded"
    assert job["result"]["saved"] == 1


def test_training_and_photo_recognition_jobs(tmp_path: Path) -> None:
    client, app, _ = make_app(tmp_path)
    services = app.state.services
    for index, name in enumerate(("Alice", "Bob")):
        for sample in range(2):
            services.datasets.collect_face(
                name,
                np.full((100, 100, 3), 100 + index * 20 + sample, dtype=np.uint8),
            )

    train = client.post(
        "/api/jobs/train",
        json={"epochs": 1, "batchSize": 2, "threshold": 0.7},
    )
    trained = wait_job(client, train.json()["id"])
    bootstrap = client.get("/api/bootstrap").json()
    model_id = bootstrap["activeModelId"]

    recognized = client.post(
        "/api/jobs/recognize",
        data={"model_id": model_id, "source": "photo"},
        files=[("files", ("target.jpg", image_bytes(), "image/jpeg"))],
    )
    result = wait_job(client, recognized.json()["id"])

    assert trained["status"] == "succeeded"
    assert model_id
    assert result["status"] == "succeeded"
    assert result["result"]["outputs"][0]["outputPath"].endswith("annotated.jpg")


def test_camera_websocket_returns_detections(tmp_path: Path) -> None:
    client, app, _ = make_app(tmp_path)
    with app.state.services.database.session() as session:
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
        set_active_model(session, model.id)
        model_id = model.id

    with client.websocket_connect(
        f"/api/ws/camera?mode=recognize&model_id={model_id}"
    ) as websocket:
        websocket.send_bytes(image_bytes())
        event = websocket.receive_json()

    assert event["type"] == "prediction"
    assert len(event["detections"]) == 1
    assert event["detections"][0]["label"] == "Bob"


def test_asset_endpoint_does_not_expose_the_database(tmp_path: Path) -> None:
    client, _, _ = make_app(tmp_path)
    database = tmp_path / "storage" / "face_workbench.sqlite3"
    database.write_bytes(b"sensitive-local-database")

    response = client.get("/api/assets/face_workbench.sqlite3")

    assert response.status_code == 404


def test_saved_faces_can_be_listed_and_deleted_individually(tmp_path: Path) -> None:
    client, app, _ = make_app(tmp_path)
    created = client.post("/api/dataset/persons", json={"name": "Alice"})
    person_id = created.json()["id"]
    app.state.services.datasets.collect_face(
        "Alice",
        np.full((100, 100, 3), 120, dtype=np.uint8),
    )
    app.state.services.datasets.collect_face(
        "Alice",
        np.full((100, 100, 3), 160, dtype=np.uint8),
    )

    listed = client.get(f"/api/dataset/persons/{person_id}/faces")
    faces = listed.json()
    image = client.get(faces[0]["imageUrl"])
    deleted = client.delete(f"/api/dataset/faces/{faces[0]['id']}")
    remaining = client.get(f"/api/dataset/persons/{person_id}/faces").json()

    assert listed.status_code == 200
    assert len(faces) == 2
    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/jpeg")
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] is True
    assert len(remaining) == 1
    assert client.get(faces[0]["imageUrl"]).status_code == 404


def test_deleting_a_person_removes_all_face_samples(tmp_path: Path) -> None:
    client, app, _ = make_app(tmp_path)
    created = client.post("/api/dataset/persons", json={"name": "Alice"})
    person_id = created.json()["id"]
    for value in (90, 130):
        app.state.services.datasets.collect_face(
            "Alice",
            np.full((100, 100, 3), value, dtype=np.uint8),
        )
    faces = client.get(f"/api/dataset/persons/{person_id}/faces").json()

    deleted = client.delete(f"/api/dataset/persons/{person_id}")
    bootstrap = client.get("/api/bootstrap").json()

    assert deleted.status_code == 200
    assert deleted.json()["removedFaces"] == 2
    assert bootstrap["dataset"]["people"] == []
    assert bootstrap["dataset"]["totalFaces"] == 0
    assert client.get(faces[0]["imageUrl"]).status_code == 404
