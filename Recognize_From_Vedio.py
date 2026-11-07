"""Deprecated compatibility entrypoint. Use ``python main.py recognize``."""

from __future__ import annotations

from face_workbench.cli import app


class Camera_reader:
    def __init__(self) -> None:
        self.img_size = 128

    def build_camera(self) -> None:
        app(["recognize", "--source", "video", "--input", "recognize_faces2.mp4"])


if __name__ == "__main__":
    print("此入口已弃用，正在转发到统一 CLI。建议运行：python main.py")
    Camera_reader().build_camera()
