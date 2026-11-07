from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from face_workbench.services.datasets import DatasetService, NoFaceDetected
from face_workbench.vision import InvalidImageError, read_image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


@dataclass(frozen=True, slots=True)
class ImportResult:
    imported: int
    duplicates: int
    missing_face: int
    invalid_images: int


class DirectoryDatasetImporter:
    def __init__(self, datasets: DatasetService) -> None:
        self.datasets = datasets

    def import_from(self, source: Path) -> ImportResult:
        imported = duplicates = missing_face = invalid_images = 0
        for person_dir in sorted(path for path in source.iterdir() if path.is_dir()):
            for image_path in sorted(
                path for path in person_dir.iterdir() if path.suffix.casefold() in IMAGE_SUFFIXES
            ):
                try:
                    image = read_image(image_path)
                except InvalidImageError:
                    invalid_images += 1
                    continue
                try:
                    result = self.datasets.collect_face(person_dir.name, image)
                except NoFaceDetected:
                    missing_face += 1
                    continue
                imported += result.saved
                duplicates += result.duplicates
        return ImportResult(
            imported=imported,
            duplicates=duplicates,
            missing_face=missing_face,
            invalid_images=invalid_images,
        )
