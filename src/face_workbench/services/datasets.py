from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy import func, select

from face_workbench.db import (
    Database,
    MediaAsset,
    Person,
    add_media_asset,
    get_face_asset,
    get_or_create_default_dataset,
    get_or_create_person,
    get_person,
    list_person_face_assets,
)
from face_workbench.domain import AssetKind, normalize_person_name
from face_workbench.services.storage import StorageLayout
from face_workbench.vision import (
    FaceDetector,
    build_face_crop,
    image_sha256,
    read_image,
    select_largest_box,
)


class NoFaceDetected(ValueError):
    """Raised when a source does not contain a detectable face."""


@dataclass(frozen=True, slots=True)
class CollectionResult:
    detected: int
    saved: int
    duplicates: int


@dataclass(frozen=True, slots=True)
class TrainingData:
    images: np.ndarray
    class_indices: list[int]
    persons: list[Person]


@dataclass(frozen=True, slots=True)
class PersonSummary:
    id: int
    name: str
    sample_count: int


@dataclass(frozen=True, slots=True)
class DatasetOverview:
    name: str
    people: list[PersonSummary]
    total_faces: int
    ready_to_train: bool


class PersonNotFound(LookupError):
    """Raised when a person does not exist."""


class FaceAssetNotFound(LookupError):
    """Raised when a saved face sample does not exist."""


@dataclass(frozen=True, slots=True)
class SavedFace:
    id: str
    relative_path: str
    created_at: datetime


class DatasetService:
    def __init__(
        self,
        database: Database,
        layout: StorageLayout,
        detector: FaceDetector,
        *,
        image_size: int = 128,
    ) -> None:
        self.database = database
        self.layout = layout
        self.detector = detector
        self.image_size = image_size

    def ensure_person(self, name: str) -> Person:
        normalized = normalize_person_name(name)
        with self.database.session() as session:
            dataset = get_or_create_default_dataset(session)
            person = get_or_create_person(session, dataset.id, normalized)
            session.expunge(person)
            return person

    def collect_face(self, person_name: str, frame: np.ndarray) -> CollectionResult:
        boxes = self.detector.detect(frame)
        if not boxes:
            raise NoFaceDetected("未检测到可保存的人脸")
        largest = select_largest_box(boxes)
        if largest is None:
            raise NoFaceDetected("未检测到可保存的人脸")
        crop = build_face_crop(frame, largest, self.image_size)
        sha256 = image_sha256(crop)
        normalized = normalize_person_name(person_name)

        with self.database.session() as session:
            dataset = get_or_create_default_dataset(session)
            person = get_or_create_person(session, dataset.id, normalized)
            asset, created = add_media_asset(
                session,
                dataset.id,
                AssetKind.DATASET_FACE,
                f"datasets/default/faces/{person.normalized_name}/{sha256[:24]}.jpg",
                sha256,
                person_id=person.id,
            )
            if created:
                path = self.layout.resolve(asset.relative_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                success, encoded = cv2.imencode(".jpg", crop)
                if not success:
                    raise ValueError("无法编码人脸图片")
                encoded.tofile(path)

        return CollectionResult(
            detected=len(boxes),
            saved=int(created),
            duplicates=int(not created),
        )

    def training_data(self) -> TrainingData:
        with self.database.session() as session:
            persons = list(session.scalars(select(Person)))
            rows = session.execute(
                select(Person.id, MediaAsset.relative_path)
                .join(MediaAsset, MediaAsset.person_id == Person.id)
                .where(MediaAsset.kind == AssetKind.DATASET_FACE.value)
            )
            assets = list(rows)
            people_with_samples = {row.id for row in assets}
            persons = [person for person in persons if person.id in people_with_samples]
            persons.sort(key=lambda person: (person.name.casefold(), person.id))
            person_order = {person.id: index for index, person in enumerate(persons)}
            assets.sort(key=lambda row: (person_order[row.id], row.relative_path))

        images: list[np.ndarray] = []
        class_indices: list[int] = []
        for row in assets:
            relative_path = row.relative_path
            try:
                image = read_image(self.layout.resolve(relative_path))
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                resized = cv2.resize(gray, (self.image_size, self.image_size))
            except (ValueError, OSError, cv2.error):
                continue
            images.append(resized)
            class_indices.append(person_order[row.id])
        if not images:
            return TrainingData(
                images=np.empty((0, self.image_size, self.image_size), dtype=np.uint8),
                class_indices=[],
                persons=persons,
            )
        return TrainingData(
            images=np.stack(images),
            class_indices=class_indices,
            persons=persons,
        )

    def overview(self) -> DatasetOverview:
        with self.database.session() as session:
            dataset = get_or_create_default_dataset(session)
            rows = session.execute(
                select(Person.id, Person.name, func.count(MediaAsset.id))
                .outerjoin(
                    MediaAsset,
                    (MediaAsset.person_id == Person.id)
                    & (MediaAsset.kind == AssetKind.DATASET_FACE.value),
                )
                .where(Person.dataset_id == dataset.id)
                .group_by(Person.id, Person.name)
                .order_by(func.lower(Person.name), Person.id)
            )
            people = [
                PersonSummary(id=int(row[0]), name=str(row[1]), sample_count=int(row[2]))
                for row in rows
            ]
        return DatasetOverview(
            name=dataset.name,
            people=people,
            total_faces=sum(person.sample_count for person in people),
            ready_to_train=sum(person.sample_count >= 2 for person in people) >= 2,
        )

    def list_faces(self, person_id: int) -> list[SavedFace]:
        with self.database.session() as session:
            if get_person(session, person_id) is None:
                raise PersonNotFound("人物不存在")
            return [
                SavedFace(
                    id=asset.id,
                    relative_path=asset.relative_path,
                    created_at=asset.created_at,
                )
                for asset in list_person_face_assets(session, person_id)
            ]

    def face_image_path(self, asset_id: str) -> Path:
        with self.database.session() as session:
            asset = get_face_asset(session, asset_id)
            if asset is None:
                raise FaceAssetNotFound("人脸样本不存在")
            path = self.layout.resolve(asset.relative_path)
        if not path.is_file():
            raise FaceAssetNotFound("人脸样本文件不存在")
        return path

    def delete_face(self, asset_id: str) -> bool:
        with self.database.session() as session:
            asset = get_face_asset(session, asset_id)
            if asset is None:
                return False
            path = self.layout.resolve(asset.relative_path)
            if path.is_file():
                path.unlink()
            session.delete(asset)
            session.flush()
        return True

    def delete_person(self, person_id: int) -> int:
        with self.database.session() as session:
            person = get_person(session, person_id)
            if person is None:
                raise PersonNotFound("人物不存在")
            assets = list_person_face_assets(session, person_id)
            for asset in assets:
                path = self.layout.resolve(asset.relative_path)
                if path.is_file():
                    path.unlink()
                session.delete(asset)
            session.delete(person)
            session.flush()
        return len(assets)
