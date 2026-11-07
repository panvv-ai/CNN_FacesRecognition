"""Deprecated compatibility entrypoint. Use ``python main.py collect``."""

from __future__ import annotations

from pathlib import Path

from face_workbench.cli import app


def readPicSaveFace(
    sourcePath: str,
    objectPath: str,
    *suffix: str,
) -> None:
    print("readPicSaveFace 已弃用，正在使用统一人脸采集服务。")
    app(
        [
            "collect",
            "--source",
            "photo",
            "--person",
            Path(objectPath).name,
            "--input",
            sourcePath,
        ]
    )


if __name__ == "__main__":
    readPicSaveFace("./MySource_faces", "./my_faces/alice", ".jpg", ".JPG", "png", "PNG")
