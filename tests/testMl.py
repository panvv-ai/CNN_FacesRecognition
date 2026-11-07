from pathlib import Path

import numpy as np
import pytest

from face_workbench.domain import FaceBox
from face_workbench.ml import (
    CnnTrainer,
    InsufficientTrainingData,
    ModelBundle,
    TrainingOptions,
    load_model_bundle,
)


class FakeModel:
    def predict(self, data: np.ndarray, verbose: int = 0) -> np.ndarray:
        assert data.shape == (1, 16, 16, 1)
        assert verbose == 0
        return np.array([[0.2, 0.8]], dtype=np.float32)


def test_model_bundle_applies_threshold_and_returns_unknown() -> None:
    bundle = ModelBundle(
        model=FakeModel(),
        labels=("Alice", "Bob"),
        threshold=0.9,
        input_size=16,
    )
    crop = np.zeros((16, 16), dtype=np.uint8)

    prediction = bundle.predict(crop, FaceBox(1, 2, 3, 4))

    assert prediction.label == "Unknown"
    assert prediction.known is False
    assert prediction.box == FaceBox(1, 2, 3, 4)


def test_cnn_training_rejects_single_class(tmp_path: Path) -> None:
    images = np.zeros((4, 16, 16), dtype=np.uint8)

    with pytest.raises(InsufficientTrainingData, match="至少需要 2 个类别"):
        CnnTrainer().train(
            images=images,
            class_indices=[0, 0, 0, 0],
            labels=["Alice"],
            artifact_dir=tmp_path / "model",
            options=TrainingOptions(epochs=1, batch_size=2, input_size=16),
        )


def test_cnn_train_save_reload_and_predict(tmp_path: Path) -> None:
    rng = np.random.default_rng(42)
    images = rng.integers(0, 256, size=(12, 16, 16), dtype=np.uint8)
    class_indices = [0] * 6 + [1] * 6
    artifact_dir = tmp_path / "model"

    result = CnnTrainer().train(
        images=images,
        class_indices=class_indices,
        labels=["Alice", "Bob"],
        artifact_dir=artifact_dir,
        options=TrainingOptions(epochs=1, batch_size=4, input_size=16),
    )
    restored = load_model_bundle(artifact_dir)
    prediction = restored.predict(images[0], FaceBox(0, 0, 10, 10))

    assert (artifact_dir / "model.keras").is_file()
    assert (artifact_dir / "metadata.json").is_file()
    assert 0.0 <= result.metrics["accuracy"] <= 1.0
    assert prediction.label in {"Alice", "Bob", "Unknown"}
    assert prediction.box == FaceBox(0, 0, 10, 10)
