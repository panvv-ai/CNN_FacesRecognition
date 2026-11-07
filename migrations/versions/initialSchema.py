"""Initial Face Workbench schema.

Revision ID: 20261107_0001
Revises:
Create Date: 2026-11-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261107_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=80), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "persons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("normalized_name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dataset_id", "normalized_name", name="uq_person_label"),
    )
    op.create_table(
        "media_assets",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            sa.Integer(),
            sa.ForeignKey("persons.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("relative_path", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("dataset_id", "sha256", name="uq_media_dataset_hash"),
    )
    op.create_table(
        "models",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("input_size", sa.Integer(), nullable=False),
        sa.Column("engine_version", sa.String(length=32), nullable=False),
        sa.Column("metrics_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "model_labels",
        sa.Column(
            "model_id",
            sa.String(length=36),
            sa.ForeignKey("models.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("class_index", sa.Integer(), primary_key=True),
        sa.Column(
            "person_id",
            sa.Integer(),
            sa.ForeignKey("persons.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("person_name", sa.String(length=80), nullable=False),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("message", sa.String(length=240), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=80), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
    op.drop_table("jobs")
    op.drop_table("model_labels")
    op.drop_table("models")
    op.drop_table("media_assets")
    op.drop_table("persons")
    op.drop_table("datasets")
