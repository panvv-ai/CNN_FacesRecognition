from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import NamedTuple


class InvalidPersonName(ValueError):
    """Raised when a person label is unsafe or empty."""


class FaceBox(NamedTuple):
    x: int
    y: int
    width: int
    height: int


class SourceKind(StrEnum):
    PHOTO = "photo"
    VIDEO = "video"
    CAMERA = "camera"


class JobKind(StrEnum):
    COLLECT = "collect"
    TRAIN = "train"
    RECOGNIZE = "recognize"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class AssetKind(StrEnum):
    DATASET_FACE = "dataset_face"
    SOURCE_PHOTO = "source_photo"
    SOURCE_VIDEO = "source_video"
    RECOGNIZED_PHOTO = "recognized_photo"
    RECOGNIZED_VIDEO = "recognized_video"


@dataclass(frozen=True, slots=True)
class FacePrediction:
    box: FaceBox
    label: str
    confidence: float
    known: bool = True


def normalize_person_name(value: str) -> str:
    normalized = " ".join(unicodedata.normalize("NFKC", value).strip().split())
    if (
        not normalized
        or normalized in {".", ".."}
        or "/" in normalized
        or "\\" in normalized
        or "\x00" in normalized
    ):
        raise InvalidPersonName("人物名称不能为空，也不能包含路径分隔符")
    if len(normalized) > 80:
        raise InvalidPersonName("人物名称不能超过 80 个字符")
    return normalized


def unknown_prediction(box: FaceBox | tuple[int, int, int, int]) -> FacePrediction:
    return FacePrediction(box=FaceBox(*box), label="Unknown", confidence=0.0, known=False)
