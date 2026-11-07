"""Deprecated compatibility entrypoint. Use ``python main.py collect``."""

from __future__ import annotations

from pathlib import Path

from face_workbench.cli import app
from face_workbench.legacy import read_all_images

faces_my_path = "./dataset/grandpa"
size = 128
img_change = None
detector = None
camera = None
index = 1
datasetSize = 200


if __name__ == "__main__":
    print("此入口已弃用，正在转发到统一 CLI。建议运行：python main.py")
    app(
        [
            "collect",
            "--source",
            "camera",
            "--person",
            Path(faces_my_path).name,
            "--camera-index",
            "0",
            "--target",
            str(datasetSize),
        ]
    )


__all__ = ["read_all_images"]
