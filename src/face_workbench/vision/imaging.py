from __future__ import annotations

import hashlib
from pathlib import Path

import cv2
import numpy as np

from face_workbench.domain import FaceBox


class InvalidImageError(ValueError):
    """Raised when an image cannot be read or decoded."""


def ensure_bgr_image(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.ndim == 3 and image.shape[2] == 3:
        return image
    if image.ndim == 3 and image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    raise InvalidImageError("不支持的图像通道格式")


def read_image(path: str | Path) -> np.ndarray:
    source = Path(path)
    if not source.is_file():
        raise InvalidImageError(f"图片不存在：{source}")
    try:
        encoded = np.fromfile(source, dtype=np.uint8)
        image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    except (OSError, cv2.error) as exc:
        raise InvalidImageError(f"无法读取图片：{source.name}") from exc
    if image is None or image.size == 0:
        raise InvalidImageError(f"图片内容损坏或格式不受支持：{source.name}")
    return image


def decode_image_bytes(data: bytes) -> np.ndarray:
    try:
        image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    except cv2.error as exc:
        raise InvalidImageError("图片内容损坏或格式不受支持") from exc
    if image is None or image.size == 0:
        raise InvalidImageError("图片内容损坏或格式不受支持")
    return image


def build_face_crop(frame: np.ndarray, box: FaceBox, size: int = 128) -> np.ndarray:
    image = ensure_bgr_image(frame)
    height, width = image.shape[:2]
    x0 = max(0, box.x)
    y0 = max(0, box.y)
    x1 = min(width, box.x + box.width)
    y1 = min(height, box.y + box.height)
    if x1 <= x0 or y1 <= y0:
        raise ValueError("人脸区域为空或超出图像边界")
    gray = cv2.cvtColor(image[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
    interpolation = cv2.INTER_AREA if gray.shape[0] > size else cv2.INTER_LINEAR
    return cv2.resize(gray, (size, size), interpolation=interpolation)


def to_model_input(crop: np.ndarray, size: int = 128) -> np.ndarray:
    if crop.ndim == 3 and crop.shape[2] == 1:
        crop = crop[:, :, 0]
    if crop.ndim != 2:
        raise ValueError("模型输入必须是单通道灰度图")
    resized = cv2.resize(crop, (size, size), interpolation=cv2.INTER_AREA)
    normalized = resized.astype(np.float32) / 255.0
    return normalized.reshape(1, size, size, 1)


def image_sha256(image: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(image)
    digest = hashlib.sha256()
    digest.update(str(contiguous.shape).encode("ascii"))
    digest.update(contiguous.tobytes())
    return digest.hexdigest()
