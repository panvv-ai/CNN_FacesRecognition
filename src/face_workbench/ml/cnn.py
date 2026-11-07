from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import numpy as np
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from tensorflow import keras

from face_workbench.domain import FaceBox, FacePrediction, unknown_prediction
from face_workbench.vision import to_model_input


class InsufficientTrainingData(ValueError):
    """Raised when the dataset cannot produce a trainable classifier."""


class PredictModel(Protocol):
    def predict(self, data: np.ndarray, verbose: int = 0) -> np.ndarray: ...


@dataclass(frozen=True, slots=True)
class TrainingOptions:
    epochs: int = 8
    batch_size: int = 20
    input_size: int = 128
    validation_fraction: float = 0.2
    seed: int = 42


@dataclass(frozen=True, slots=True)
class TrainingResult:
    artifact_dir: Path
    metrics: dict[str, float]
    labels: tuple[str, ...]
    threshold: float
    input_size: int


class ModelBundle:
    def __init__(
        self,
        *,
        model: PredictModel,
        labels: tuple[str, ...] | list[str],
        threshold: float,
        input_size: int,
    ) -> None:
        if not labels:
            raise ValueError("模型至少需要一个标签")
        if not 0.0 < threshold <= 1.0:
            raise ValueError("识别阈值必须位于 (0, 1]")
        self.model = model
        self.labels = tuple(labels)
        self.threshold = threshold
        self.input_size = input_size

    def predict(self, crop: np.ndarray, box: FaceBox) -> FacePrediction:
        probabilities = np.asarray(
            self.model.predict(to_model_input(crop, self.input_size), verbose=0)
        )
        if probabilities.size != len(self.labels):
            return unknown_prediction(box)
        class_index = int(np.argmax(probabilities[0]))
        confidence = float(probabilities[0, class_index])
        if confidence < self.threshold:
            return unknown_prediction(box)
        return FacePrediction(
            box=box,
            label=self.labels[class_index],
            confidence=confidence,
            known=True,
        )


def build_cnn(num_classes: int, input_size: int) -> keras.Model:
    return keras.Sequential(
        [
            keras.layers.Input(shape=(input_size, input_size, 1)),
            keras.layers.Conv2D(32, (5, 5), padding="same", activation="relu"),
            keras.layers.MaxPooling2D(pool_size=(2, 2)),
            keras.layers.Conv2D(64, (5, 5), padding="same", activation="relu"),
            keras.layers.MaxPooling2D(pool_size=(2, 2)),
            keras.layers.Flatten(),
            keras.layers.Dense(512, activation="relu"),
            keras.layers.Dense(num_classes, activation="softmax"),
        ],
        name="face_workbench_cnn",
    )


class CnnTrainer:
    def train(
        self,
        *,
        images: np.ndarray,
        class_indices: list[int],
        labels: list[str],
        artifact_dir: Path,
        options: TrainingOptions | None = None,
        threshold: float = 0.7,
    ) -> TrainingResult:
        settings = options or TrainingOptions()
        if len(labels) < 2:
            raise InsufficientTrainingData("训练至少需要 2 个类别")
        counts = np.bincount(np.asarray(class_indices, dtype=np.int32), minlength=len(labels))
        if np.any(counts < 2):
            raise InsufficientTrainingData("每个类别至少需要 2 张可读人脸")
        if images.shape[0] != len(class_indices):
            raise ValueError("图片数量与标签数量不一致")

        keras.utils.set_random_seed(settings.seed)
        data = images.astype(np.float32) / 255.0
        if data.ndim == 3:
            data = data[:, :, :, np.newaxis]
        target = np.asarray(class_indices, dtype=np.int32)
        x_train, x_test, y_train, y_test = train_test_split(
            data,
            target,
            test_size=settings.validation_fraction,
            random_state=settings.seed,
            stratify=target,
        )
        model = build_cnn(len(labels), settings.input_size)
        model.compile(
            optimizer="adam",
            loss="sparse_categorical_crossentropy",
            metrics=["accuracy"],
        )
        callbacks = [
            keras.callbacks.EarlyStopping(
                monitor="val_loss",
                patience=3,
                restore_best_weights=True,
            )
        ]
        model.fit(
            x_train,
            y_train,
            validation_data=(x_test, y_test),
            epochs=settings.epochs,
            batch_size=settings.batch_size,
            callbacks=callbacks,
            verbose=0,
        )
        loss, accuracy = model.evaluate(x_test, y_test, verbose=0)
        probabilities = model.predict(x_test, verbose=0)
        predicted = np.argmax(probabilities, axis=1)
        metrics = {
            "loss": float(loss),
            "accuracy": float(accuracy_score(y_test, predicted)),
            "macroF1": float(f1_score(y_test, predicted, average="macro", zero_division=0)),
            "evaluationAccuracy": float(accuracy),
        }

        artifact_dir.mkdir(parents=True, exist_ok=True)
        model.save(artifact_dir / "model.keras")
        metadata = {
            "schemaVersion": 1,
            "engineVersion": "cnn-v1",
            "labels": labels,
            "threshold": threshold,
            "inputSize": settings.input_size,
            "metrics": metrics,
            "seed": settings.seed,
            "createdAt": datetime.now(UTC).isoformat(),
        }
        (artifact_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return TrainingResult(
            artifact_dir=artifact_dir,
            metrics=metrics,
            labels=tuple(labels),
            threshold=threshold,
            input_size=settings.input_size,
        )


def load_model_bundle(artifact_dir: Path) -> ModelBundle:
    metadata: dict[str, Any] = json.loads(
        (artifact_dir / "metadata.json").read_text(encoding="utf-8")
    )
    model = keras.models.load_model(artifact_dir / "model.keras")
    return ModelBundle(
        model=model,
        labels=tuple(metadata["labels"]),
        threshold=float(metadata["threshold"]),
        input_size=int(metadata["inputSize"]),
    )
