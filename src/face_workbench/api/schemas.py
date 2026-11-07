from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from face_workbench.db import Job, ModelRecord, Person
from face_workbench.services.datasets import DatasetOverview


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class PersonCreate(ApiModel):
    name: str


class PersonView(ApiModel):
    id: int
    name: str
    sample_count: int = 0

    @classmethod
    def from_entity(cls, person: Person, sample_count: int = 0) -> PersonView:
        return cls(id=person.id, name=person.name, sample_count=sample_count)


class FaceAssetView(ApiModel):
    id: str
    image_url: str
    created_at: datetime


class DeleteFaceView(ApiModel):
    deleted: bool


class DeletePersonView(ApiModel):
    deleted: bool
    removed_faces: int


class DatasetView(ApiModel):
    name: str
    people: list[PersonView]
    total_faces: int
    ready_to_train: bool

    @classmethod
    def from_overview(cls, overview: DatasetOverview) -> DatasetView:
        return cls(
            name=overview.name,
            people=[
                PersonView(
                    id=person.id,
                    name=person.name,
                    sample_count=person.sample_count,
                )
                for person in overview.people
            ],
            total_faces=overview.total_faces,
            ready_to_train=overview.ready_to_train,
        )


class ModelView(ApiModel):
    id: str
    name: str
    labels: list[str]
    metrics: dict[str, float]
    threshold: float
    input_size: int
    created_at: datetime
    active: bool = False

    @classmethod
    def from_entity(cls, model: ModelRecord, active: bool) -> ModelView:
        return cls(
            id=model.id,
            name=model.name,
            labels=[label.person_name for label in model.labels],
            metrics=model.metrics_json,
            threshold=model.threshold,
            input_size=model.input_size,
            created_at=model.created_at,
            active=active,
        )


class JobView(ApiModel):
    id: str
    kind: str
    status: str
    progress: int
    message: str
    result: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, job: Job) -> JobView:
        return cls(
            id=job.id,
            kind=job.kind,
            status=job.status,
            progress=job.progress,
            message=job.message,
            result=job.result_json,
            error_code=job.error_code,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )


class BootstrapView(ApiModel):
    engine_ready: bool
    dataset: DatasetView
    models: list[ModelView]
    active_model_id: str | None
    recent_jobs: list[JobView]
    camera_frame_edge: int
    threshold: float


class TrainingRequest(ApiModel):
    epochs: int = Field(default=8, ge=1, le=100)
    batch_size: int = Field(default=20, ge=1, le=512)
    threshold: float = Field(default=0.7, gt=0, le=1)
    seed: int = Field(default=42, ge=0, le=2**31 - 1)


class CameraEvent(ApiModel):
    type: str
    frame_id: int
    width: int
    height: int
    detections: list[dict[str, Any]] = Field(default_factory=list)
    saved: int = 0
    duplicates: int = 0
    message: str | None = None
