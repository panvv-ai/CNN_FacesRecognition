import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CAMEL_CASE_FILE = re.compile(r"^[A-Za-z][A-Za-z0-9]*\.py$")


def test_root_only_contains_the_unified_entrypoint() -> None:
    root_python_files = sorted(path.name for path in PROJECT_ROOT.glob("*.py"))

    assert root_python_files == ["main.py"]


def test_python_source_and_test_files_use_camel_case_names() -> None:
    invalid: list[str] = []
    for directory in ("src", "scripts", "tests", "migrations"):
        for path in (PROJECT_ROOT / directory).rglob("*.py"):
            if path.name == "__init__.py":
                continue
            if not CAMEL_CASE_FILE.fullmatch(path.name):
                invalid.append(path.relative_to(PROJECT_ROOT).as_posix())

    assert invalid == []
