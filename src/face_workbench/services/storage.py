from __future__ import annotations

from pathlib import Path


class StorageLayout:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.dataset_faces = self.root / "datasets" / "default" / "faces"
        self.models = self.root / "models"
        self.uploads = self.root / "uploads"
        self.outputs = self.root / "outputs"
        for directory in (
            self.dataset_faces,
            self.models,
            self.uploads,
            self.outputs,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def dataset_face_path(self, normalized_name: str, sha256: str) -> Path:
        directory = self.dataset_faces / normalized_name
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{sha256[:24]}.jpg"

    def model_dir(self, model_id: str) -> Path:
        directory = self.models / model_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def upload_path(self, job_id: str, filename: str) -> Path:
        directory = self.uploads / job_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory / Path(filename).name

    def output_path(self, job_id: str, filename: str) -> Path:
        directory = self.outputs / job_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory / Path(filename).name

    def relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        if not candidate.is_relative_to(self.root):
            raise ValueError("资源路径超出存储目录")
        return candidate
