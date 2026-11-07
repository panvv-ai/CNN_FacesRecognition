from typer.testing import CliRunner

import face_workbench.cli as cli
from face_workbench.cli import app


def test_cli_help_lists_product_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "serve" in result.stdout
    assert "collect" in result.stdout
    assert "train" in result.stdout
    assert "recognize" in result.stdout
    assert "import-dataset" in result.stdout


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
