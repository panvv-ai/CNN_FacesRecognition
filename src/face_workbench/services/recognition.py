from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from face_workbench.db import Database, add_media_asset, get_model
from face_workbench.domain import AssetKind, FacePrediction
from face_workbench.ml import ModelBundle, load_model_bundle
from face_workbench.services.storage import StorageLayout
from face_workbench.vision import (
    FaceDetector,
    build_face_crop,
    decode_image_bytes,
    image_sha256,
)


@dataclass(frozen=True, slots=True)
class RecognitionResult:
    output_path: str
    predictions: tuple[FacePrediction, ...]
    width: int
    height: int


def draw_predictions(frame: np.ndarray, predictions: list[FacePrediction]) -> np.ndarray:
    annotated = frame.copy()
    for prediction in predictions:
        box = prediction.box
        color = (107, 208, 255) if prediction.known else (91, 175, 255)
        cv2.rectangle(
            annotated,
            (box.x, box.y),
            (box.x + box.width, box.y + box.height),
            color,
            2,
        )
        label = (
            f"{prediction.label} {prediction.confidence:.0%}"
            if prediction.known
            else prediction.label
        )
        text_y = max(20, box.y - 8)
        cv2.putText(
            annotated,
            label,
            (box.x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            color,
            2,
            cv2.LINE_AA,
        )
    return annotated


class RecognitionService:
    def __init__(
        self,
        database: Database,
        layout: StorageLayout,
        detector: FaceDetector,
        *,
        image_size: int = 128,
        bundle_loader: Callable[[Path], ModelBundle] = load_model_bundle,
    ) -> None:
        self.database = database
        self.layout = layout
        self.detector = detector
        self.image_size = image_size
        self.bundle_loader = bundle_loader

    def load_bundle(self, model_id: str) -> ModelBundle:
        with self.database.session() as session:
            model = get_model(session, model_id)
            if model is None:
                raise ValueError("模型不存在")
            artifact_path = self.layout.resolve(model.artifact_path)
        artifact_dir = artifact_path.parent if artifact_path.suffix == ".keras" else artifact_path
        return self.bundle_loader(artifact_dir)

    def predict_frame(
        self,
        bundle: ModelBundle,
        frame: np.ndarray,
    ) -> list[FacePrediction]:
        predictions: list[FacePrediction] = []
        for box in self.detector.detect(frame):
            try:
                crop = build_face_crop(frame, box, self.image_size)
            except ValueError:
                continue
            predictions.append(bundle.predict(crop, box))
        return predictions

    def recognize_photo(
        self,
        model_id: str,
        image_bytes: bytes,
        *,
        output_id: str,
    ) -> RecognitionResult:
        frame = decode_image_bytes(image_bytes)
        bundle = self.load_bundle(model_id)
        return self.recognize_photo_with_bundle(
            bundle,
            frame,
            output_id=output_id,
        )

    def recognize_photo_with_bundle(
        self,
        bundle: ModelBundle,
        frame: np.ndarray,
        *,
        output_id: str,
    ) -> RecognitionResult:
        predictions = self.predict_frame(bundle, frame)
        annotated = draw_predictions(frame, predictions)
        output = self.layout.output_path(output_id, "annotated.jpg")
        success, encoded = cv2.imencode(".jpg", annotated)
        if not success:
            raise ValueError("无法编码识别结果")
        encoded.tofile(output)
        relative_path = self.layout.relative(output)
        with self.database.session() as session:
            from face_workbench.db import get_or_create_default_dataset

            dataset = get_or_create_default_dataset(session)
            add_media_asset(
                session,
                dataset.id,
                AssetKind.RECOGNIZED_PHOTO,
                relative_path,
                image_sha256(annotated),
            )
        height, width = frame.shape[:2]
        return RecognitionResult(
            output_path=relative_path,
            predictions=tuple(predictions),
            width=width,
            height=height,
        )
