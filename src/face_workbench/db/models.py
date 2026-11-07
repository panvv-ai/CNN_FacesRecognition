from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    persons: Mapped[list[Person]] = relationship(back_populates="dataset")
    assets: Mapped[list[MediaAsset]] = relationship(back_populates="dataset")
    models: Mapped[list[ModelRecord]] = relationship(back_populates="dataset")


class Person(Base):
    __tablename__ = "persons"
    __table_args__ = (UniqueConstraint("dataset_id", "normalized_name", name="uq_person_label"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(80))
    normalized_name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    dataset: Mapped[Dataset] = relationship(back_populates="persons")
    assets: Mapped[list[MediaAsset]] = relationship(back_populates="person")


class MediaAsset(Base):
    __tablename__ = "media_assets"
    __table_args__ = (UniqueConstraint("dataset_id", "sha256", name="uq_media_dataset_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    person_id: Mapped[int | None] = mapped_column(
        ForeignKey("persons.id", ondelete="SET NULL"),
        nullable=True,
    )
    kind: Mapped[str] = mapped_column(String(32))
    relative_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    dataset: Mapped[Dataset] = relationship(back_populates="assets")
    person: Mapped[Person | None] = relationship(back_populates="assets")


class ModelRecord(Base):
    __tablename__ = "models"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[int] = mapped_column(ForeignKey("datasets.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    artifact_path: Mapped[str] = mapped_column(Text)
    threshold: Mapped[float]
    input_size: Mapped[int] = mapped_column(Integer, default=128)
    engine_version: Mapped[str] = mapped_column(String(32), default="cnn-v1")
    metrics_json: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    dataset: Mapped[Dataset] = relationship(back_populates="models")
    labels: Mapped[list[ModelLabel]] = relationship(
        back_populates="model",
        cascade="all, delete-orphan",
        order_by="ModelLabel.class_index",
    )


class ModelLabel(Base):
    __tablename__ = "model_labels"

    model_id: Mapped[str] = mapped_column(
        ForeignKey("models.id", ondelete="CASCADE"),
        primary_key=True,
    )
    class_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int | None] = mapped_column(
        ForeignKey("persons.id", ondelete="SET NULL"),
        nullable=True,
    )
    person_name: Mapped[str] = mapped_column(String(80))

    model: Mapped[ModelRecord] = relationship(back_populates="labels")
    person: Mapped[Person | None] = relationship()


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kind: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[str] = mapped_column(String(240), default="")
    payload_json: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
    )


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text)
