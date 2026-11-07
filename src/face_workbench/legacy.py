"""Compatibility adapters for the original flat-script API."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from tensorflow import keras

from face_workbench.ml import build_cnn
from face_workbench.vision import read_image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}


def has_suffix(value: str, suffixes: tuple[str, ...]) -> bool:
    return any(value.casefold().endswith(suffix.casefold().lstrip(".")) for suffix in suffixes)


def read_all_images(path: str | Path, *suffixes: str) -> list[str | np.ndarray]:
    root = Path(path)
    result: list[str | np.ndarray] = [root.name]
    normalized = tuple(suffixes or (".jpg", ".png"))
    for item in sorted(root.iterdir()):
        if item.is_file() and has_suffix(item.name, normalized):
            result.append(read_image(item))
    return result


def read_file(path: str | Path) -> tuple[np.ndarray, list[int], int]:
    root = Path(path)
    images: list[np.ndarray] = []
    labels: list[int] = []
    label_index = 0
    person_dirs = sorted(
        (item for item in root.iterdir() if item.is_dir()),
        key=lambda path: path.name.casefold(),
    )
    for person_dir in person_dirs:
        found = False
        for image_path in sorted(person_dir.iterdir()):
            if image_path.suffix.casefold() not in IMAGE_SUFFIXES:
                continue
            try:
                image = read_image(image_path)
            except ValueError:
                continue
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            images.append(cv2.resize(gray, (128, 128)))
            labels.append(label_index)
            found = True
        if found:
            label_index += 1
    array = np.stack(images) if images else np.empty((0, 128, 128), dtype=np.uint8)
    return array, labels, label_index


def read_name_list(path: str | Path) -> list[str]:
    root = Path(path)
    return sorted(
        (item.name for item in root.iterdir() if item.is_dir()),
        key=str.casefold,
    )


class DataSet:
    def __init__(self, path: str | Path) -> None:
        images, labels, counter = read_file(path)
        from sklearn.model_selection import train_test_split

        self.num_classes = counter
        self.img_size = 128
        x_train, x_test, y_train, y_test = train_test_split(
            images,
            labels,
            test_size=0.2,
            random_state=42,
            stratify=labels if counter > 1 and len(images) >= 4 else None,
        )
        self.X_train = x_train.reshape((-1, 128, 128, 1)).astype("float32") / 255.0
        self.X_test = x_test.reshape((-1, 128, 128, 1)).astype("float32") / 255.0
        self.Y_train = keras.utils.to_categorical(y_train, num_classes=counter)
        self.Y_test = keras.utils.to_categorical(y_test, num_classes=counter)

    def check(self) -> None:
        print("train", self.X_train.shape, "test", self.X_test.shape)


class Model:
    FILE_PATH = "./MyModel/model.keras"
    IMAGE_SIZE = 128

    def __init__(self) -> None:
        self.model: keras.Model | None = None
        self.dataset: DataSet | None = None

    def read_trainData(self, dataset: DataSet) -> None:
        self.dataset = dataset

    def build_model(self) -> None:
        if self.dataset is None:
            raise RuntimeError("先调用 read_trainData")
        self.model = build_cnn(self.dataset.num_classes, self.IMAGE_SIZE)

    def train_model(self) -> None:
        if self.model is None or self.dataset is None:
            raise RuntimeError("先调用 build_model")
        self.model.compile(
            optimizer="adam",
            loss="categorical_crossentropy",
            metrics=["accuracy"],
        )
        self.model.fit(self.dataset.X_train, self.dataset.Y_train, epochs=8, batch_size=20)

    def evaluate_model(self) -> tuple[float, float]:
        if self.model is None or self.dataset is None:
            raise RuntimeError("先训练模型")
        loss, accuracy = self.model.evaluate(self.dataset.X_test, self.dataset.Y_test)
        print("模型损失：", loss, "模型精确度：", accuracy)
        return float(loss), float(accuracy)

    def save(self, file_path: str = FILE_PATH) -> None:
        if self.model is None:
            raise RuntimeError("没有可保存的模型")
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        self.model.save(file_path)

    def load(self, file_path: str = FILE_PATH) -> None:
        self.model = keras.models.load_model(file_path)

    def predict(self, image: np.ndarray) -> tuple[int, float]:
        if self.model is None:
            raise RuntimeError("没有可预测的模型")
        data = image.reshape((1, self.IMAGE_SIZE, self.IMAGE_SIZE, 1)).astype("float32") / 255.0
        result = self.model.predict(data, verbose=0)
        index = int(np.argmax(result))
        return index, float(result[0, index])
