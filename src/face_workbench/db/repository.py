from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from face_workbench.db.models import (
    AppSetting,
    Dataset,
    Job,
    MediaAsset,
    ModelLabel,
    ModelRecord,
    Person,
    utc_now,
)
from face_workbench.domain import AssetKind, JobKind, JobStatus, normalize_person_name

DEFAULT_DATASET = "default"
ACTIVE_MODEL_KEY = "active_model_id"


def get_or_create_default_dataset(session: Session) -> Dataset:
    dataset = session.scalar(select(Dataset).where(Dataset.name == DEFAULT_DATASET))
    if dataset is None:
        dataset = Dataset(name=DEFAULT_DATASET)
        session.add(dataset)
        session.flush()
    return dataset


def get_or_create_person(session: Session, dataset_id: int, name: str) -> Person:
    normalized = normalize_person_name(name)
    lookup_key = normalized.casefold()
    person = session.scalar(
        select(Person).where(
            Person.dataset_id == dataset_id,
            Person.normalized_name == lookup_key,
        )
    )
    if person is None:
        person = Person(dataset_id=dataset_id, name=normalized, normalized_name=lookup_key)
        session.add(person)
        session.flush()
    return person


def get_person(session: Session, person_id: int) -> Person | None:
    return session.get(Person, person_id)


def list_person_face_assets(session: Session, person_id: int) -> list[MediaAsset]:
    return list(
        session.scalars(
            select(MediaAsset)
            .where(
                MediaAsset.person_id == person_id,
                MediaAsset.kind == AssetKind.DATASET_FACE.value,
            )
            .order_by(MediaAsset.created_at.desc(), MediaAsset.id)
        )
    )


def get_face_asset(session: Session, asset_id: str) -> MediaAsset | None:
    return session.scalar(
        select(MediaAsset).where(
            MediaAsset.id == asset_id,
            MediaAsset.kind == AssetKind.DATASET_FACE.value,
        )
    )


def add_media_asset(
    session: Session,
    dataset_id: int,
    kind: AssetKind,
    relative_path: str,
    sha256: str,
    *,
    person_id: int | None = None,
) -> tuple[MediaAsset, bool]:
    existing = session.scalar(
        select(MediaAsset).where(
            MediaAsset.dataset_id == dataset_id,
            MediaAsset.sha256 == sha256,
        )
    )
    if existing is not None:
        return existing, False
    asset = MediaAsset(
        id=str(uuid4()),
        dataset_id=dataset_id,
        person_id=person_id,
        kind=kind.value,
        relative_path=relative_path,
        sha256=sha256,
    )
    session.add(asset)
    session.flush()
    return asset, True


def create_job(
    session: Session,
    kind: JobKind,
    *,
    payload: dict[str, object] | None = None,
) -> Job:
    job = Job(
        id=str(uuid4()),
        kind=kind.value,
        status=JobStatus.QUEUED.value,
        payload_json=payload or {},
    )
    session.add(job)
    session.flush()
    return job


def update_job(
    session: Session,
    job_id: str,
    *,
    status: JobStatus | None = None,
    progress: int | None = None,
    message: str | None = None,
    result: dict[str, object] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> Job:
    job = session.get_one(Job, job_id)
    if status is not None:
        job.status = status.value
    if progress is not None:
        job.progress = max(0, min(100, progress))
    if message is not None:
        job.message = message[:240]
    if result is not None:
        job.result_json = result
    if error_code is not None:
        job.error_code = error_code
    if error_message is not None:
        job.error_message = error_message
    job.updated_at = utc_now()
    session.flush()
    return job


def mark_running_jobs_interrupted(session: Session) -> None:
    session.execute(
        update(Job)
        .where(Job.status == JobStatus.RUNNING.value)
        .values(
            status=JobStatus.INTERRUPTED.value,
            message="服务重启，任务已中断",
            error_code="service_restarted",
            error_message="任务不会自动恢复，请重新发起。",
            updated_at=utc_now(),
        )
    )


def register_model(
    session: Session,
    dataset_id: int,
    *,
    artifact_path: str,
    labels: list[Person],
    metrics: dict[str, float],
    threshold: float,
    name: str | None = None,
) -> ModelRecord:
    model_id = str(uuid4())
    model = ModelRecord(
        id=model_id,
        dataset_id=dataset_id,
        name=name or f"Model {utc_now():%Y-%m-%d %H:%M:%S}",
        artifact_path=artifact_path,
        threshold=threshold,
        metrics_json=metrics,
    )
    model.labels = [
        ModelLabel(
            model_id=model_id,
            class_index=index,
            person_id=person.id,
            person_name=person.name,
        )
        for index, person in enumerate(labels)
    ]
    session.add(model)
    session.flush()
    return model


def set_active_model(session: Session, model_id: str) -> None:
    session.get_one(ModelRecord, model_id)
    setting = session.get(AppSetting, ACTIVE_MODEL_KEY)
    if setting is None:
        session.add(AppSetting(key=ACTIVE_MODEL_KEY, value=model_id))
    else:
        setting.value = model_id
    session.flush()


def get_active_model(session: Session) -> ModelRecord | None:
    setting = session.get(AppSetting, ACTIVE_MODEL_KEY)
    if setting is None:
        return None
    return session.scalar(
        select(ModelRecord)
        .options(selectinload(ModelRecord.labels))
        .where(ModelRecord.id == setting.value)
    )


def get_model(session: Session, model_id: str) -> ModelRecord | None:
    return session.scalar(
        select(ModelRecord)
        .options(selectinload(ModelRecord.labels))
        .where(ModelRecord.id == model_id)
    )


def list_models(session: Session) -> list[ModelRecord]:
    return list(
        session.scalars(
            select(ModelRecord)
            .options(selectinload(ModelRecord.labels))
            .order_by(ModelRecord.created_at.desc())
        )
    )
