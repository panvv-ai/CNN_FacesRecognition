"""Deprecated compatibility entrypoint. Use ``python main.py recognize``."""

from __future__ import annotations

from face_workbench.cli import app


def test_onePicture(path: str) -> None:
    app(["recognize", "--source", "photo", "--input", path])


def test_onBatch(path: str) -> None:
    app(["recognize", "--source", "photo", "--input", path])


if __name__ == "__main__":
    print("此入口已弃用，正在转发到统一 CLI。建议运行：python main.py")
    test_onBatch("./model_test")
