from pathlib import Path

import numpy as np
import pytest

from face_workbench.domain import FaceBox
from face_workbench.vision import (
    InvalidImageError,
    build_face_crop,
    ensure_bgr_image,
    image_sha256,
    read_image,
    select_largest_box,
    to_model_input,
)


def test_build_face_crop_returns_grayscale_square() -> None:
    frame = np.zeros((240, 320, 3), dtype=np.uint8)

    crop = build_face_crop(frame, FaceBox(40, 30, 100, 80), size=128)

    assert crop.shape == (128, 128)
    assert crop.dtype == np.uint8
    assert crop.ndim == 2


def test_build_face_crop_rejects_empty_box() -> None:
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    with pytest.raises(ValueError, match="人脸区域"):
        build_face_crop(frame, FaceBox(100, 100, 0, 30))


def test_largest_box_uses_area_and_breaks_ties_by_position() -> None:
    boxes = [FaceBox(0, 0, 20, 20), FaceBox(30, 30, 40, 50), FaceBox(5, 5, 20, 20)]

    assert select_largest_box(boxes) == FaceBox(30, 30, 40, 50)
    assert select_largest_box([]) is None


def test_to_model_input_adds_batch_channel_and_normalizes() -> None:
    crop = np.full((128, 128), 127, dtype=np.uint8)

    model_input = to_model_input(crop)

    assert model_input.shape == (1, 128, 128, 1)
    assert model_input.dtype == np.float32
    assert 0.49 < float(model_input[0, 0, 0, 0]) < 0.50


def test_image_sha256_is_stable() -> None:
    image = np.arange(48, dtype=np.uint8).reshape(4, 4, 3)

    assert image_sha256(image) == image_sha256(image.copy())


def test_read_image_rejects_missing_or_corrupt_files(tmp_path: Path) -> None:
    with pytest.raises(InvalidImageError):
        read_image(tmp_path / "missing.jpg")

    corrupt = tmp_path / "corrupt.jpg"
    corrupt.write_bytes(b"not-an-image")
    with pytest.raises(InvalidImageError):
        read_image(corrupt)


def test_ensure_bgr_image_converts_grayscale_and_rgba() -> None:
    gray = np.zeros((10, 10), dtype=np.uint8)
    rgba = np.zeros((10, 10, 4), dtype=np.uint8)

    assert ensure_bgr_image(gray).shape == (10, 10, 3)
    assert ensure_bgr_image(rgba).shape == (10, 10, 3)


def test_detector_returns_boxes_with_injected_cascade() -> None:
    from face_workbench.vision import FaceDetector

    class Cascade:
        def detectMultiScale(self, gray: np.ndarray, **_: object) -> np.ndarray:
            assert gray.ndim == 2
            return np.array([[10, 20, 30, 40]])

    detector = FaceDetector(cascade=Cascade())
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    assert detector.detect(frame) == [FaceBox(10, 20, 30, 40)]


def test_default_detector_loads_the_bundled_haar_model() -> None:
    from face_workbench.vision import FaceDetector

    detector = FaceDetector()

    assert detector.detect(np.zeros((80, 80, 3), dtype=np.uint8)) == []
