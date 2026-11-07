from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Protocol

import cv2
import numpy as np

from face_workbench.domain import FaceBox
from face_workbench.vision.imaging import ensure_bgr_image


class CascadeLike(Protocol):
    def detectMultiScale(self, image: np.ndarray, **kwargs: object) -> Sequence[Sequence[int]]: ...


def select_largest_box(boxes: Iterable[FaceBox]) -> FaceBox | None:
    return max(boxes, key=lambda box: (box.width * box.height, -box.y, -box.x), default=None)


class FaceDetector:
    def __init__(self, cascade: CascadeLike | None = None) -> None:
        self._cascade = cascade or cv2.CascadeClassifier(
            cv2.data.haarcascades  # type: ignore[attr-defined]
            + "haarcascade_frontalface_alt.xml"
        )
        empty_check = getattr(self._cascade, "empty", None)
        if callable(empty_check) and empty_check():
            raise RuntimeError("无法加载 OpenCV 人脸检测模型")

    def detect(self, frame: np.ndarray) -> list[FaceBox]:
        image = ensure_bgr_image(frame)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self._cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30),
        )
        return [FaceBox(*(int(value) for value in face)) for face in faces]
