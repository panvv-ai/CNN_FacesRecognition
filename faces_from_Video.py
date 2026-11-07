"""Deprecated compatibility entrypoint. Use ``python main.py collect``."""

from __future__ import annotations

from face_workbench.cli import app
from face_workbench.legacy import Model, read_all_images

faces_my_path = "./my_faces"
size = 128
datasetSize = 200
img_change = None
detector = None
camera = None
index = 1


if __name__ == "__main__":
    print("此入口已弃用，正在转发到统一 CLI。建议运行：python main.py")
    app(
        [
            "collect",
            "--source",
            "video",
            "--person",
            "default",
            "--input",
            "collect_faces1.mp4",
            "--target",
            str(datasetSize),
        ]
    )


__all__ = ["Model", "read_all_images"]
