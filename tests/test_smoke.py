from pathlib import Path

import cv2
import numpy as np
from typer.testing import CliRunner

import face_workbench.cli as cli
from face_workbench.cli import app
from face_workbench.legacy import read_file, read_name_list


def test_cli_help_lists_product_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "serve" in result.stdout
    assert "collect" in result.stdout
    assert "train" in result.stdout
    assert "recognize" in result.stdout


def test_cli_without_arguments_starts_the_web_app(monkeypatch) -> None:
    called: list[bool] = []
    monkeypatch.setattr(
        cli,
        "serve",
        lambda host, port, open_browser: called.append(True),
    )

    result = CliRunner().invoke(app, [])

    assert result.exit_code == 0
    assert called == [True]


def test_legacy_dataset_helpers_keep_stable_person_order(tmp_path: Path) -> None:
    for name in ("Zoe", "Alice"):
        directory = tmp_path / name
        directory.mkdir()
        image = np.full((40, 40, 3), 120, dtype=np.uint8)
        assert cv2.imwrite(str(directory / "sample.jpg"), image)

    images, labels, count = read_file(tmp_path)

    assert images.shape == (2, 128, 128)
    assert labels == [0, 1]
    assert count == 2
    assert read_name_list(tmp_path) == ["Alice", "Zoe"]
