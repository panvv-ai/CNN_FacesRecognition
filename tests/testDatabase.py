from pathlib import Path

from sqlalchemy import inspect

from face_workbench.db import (
    Database,
    add_media_asset,
    create_job,
    get_active_model,
    get_or_create_default_dataset,
    get_or_create_person,
    mark_running_jobs_interrupted,
    register_model,
    set_active_model,
    update_job,
    upgrade_database,
)
from face_workbench.domain import AssetKind, JobKind, JobStatus


def make_database(tmp_path: Path) -> Database:
    url = f"sqlite+pysqlite:///{tmp_path / 'workbench.sqlite3'}"
    upgrade_database(url)
    return Database(url)


def test_upgrade_creates_expected_tables(tmp_path: Path) -> None:
    database = make_database(tmp_path)

    tables = set(inspect(database.engine).get_table_names())

    assert {
        "alembic_version",
        "app_settings",
        "datasets",
        "jobs",
        "media_assets",
        "model_labels",
        "models",
        "persons",
    } <= tables


def test_people_are_unique_per_dataset(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    with database.session() as session:
        dataset = get_or_create_default_dataset(session)
        first = get_or_create_person(session, dataset.id, "Alice")
        second = get_or_create_person(session, dataset.id, "alice")

    assert first.id == second.id
    assert second.name == "Alice"


def test_media_asset_deduplicates_same_hash(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    with database.session() as session:
        dataset = get_or_create_default_dataset(session)
        person = get_or_create_person(session, dataset.id, "Alice")
        first, first_created = add_media_asset(
            session,
            dataset.id,
            AssetKind.DATASET_FACE,
            "datasets/default/faces/alice/one.jpg",
            "same-hash",
            person_id=person.id,
        )
        second, second_created = add_media_asset(
            session,
            dataset.id,
            AssetKind.DATASET_FACE,
            "datasets/default/faces/alice/two.jpg",
            "same-hash",
            person_id=person.id,
        )

    assert first_created is True
    assert second_created is False
    assert first.id == second.id


def test_running_jobs_are_marked_interrupted_after_restart(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    with database.session() as session:
        job = create_job(session, JobKind.TRAIN, payload={"epochs": 2})
        update_job(session, job.id, status=JobStatus.RUNNING, progress=25)
        mark_running_jobs_interrupted(session)
        session.refresh(job)

    assert job.status == JobStatus.INTERRUPTED
    assert job.error_code == "service_restarted"


def test_model_labels_keep_training_order_and_active_model_persists(tmp_path: Path) -> None:
    database = make_database(tmp_path)
    with database.session() as session:
        dataset = get_or_create_default_dataset(session)
        alice = get_or_create_person(session, dataset.id, "Alice")
        bob = get_or_create_person(session, dataset.id, "Bob")
        model = register_model(
            session,
            dataset.id,
            artifact_path="models/model-1/model.keras",
            labels=[bob, alice],
            metrics={"accuracy": 0.9},
            threshold=0.7,
        )
        set_active_model(session, model.id)
        model_id = model.id

    with database.session() as session:
        active = get_active_model(session)

    assert active is not None
    assert active.id == model_id
    assert [(label.class_index, label.person_name) for label in active.labels] == [
        (0, "Bob"),
        (1, "Alice"),
    ]
