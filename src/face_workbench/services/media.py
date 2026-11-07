from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from face_workbench.ml import ModelBundle
from face_workbench.services.datasets import CollectionResult, DatasetService, NoFaceDetected
from face_workbench.services.recognition import draw_predictions
from face_workbench.vision import build_face_crop

ProgressCallback = Callable[[int, str], None]


@dataclass(frozen=True, slots=True)
class VideoRecognitionResult:
    output_path: str
    frames_processed: int
    prediction_count: int
    codec: str


class MediaService:
    def __init__(self, datasets: DatasetService) -> None:
        self.datasets = datasets

    def collect_from_video(
        self,
        person_name: str,
        video_path: Path,
        *,
        sample_interval: int = 10,
        target: int = 200,
        progress: ProgressCallback | None = None,
    ) -> CollectionResult:
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise ValueError("无法打开视频文件")
        total_frames = max(1, int(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
        detected = saved = duplicates = 0
        frame_index = 0
        try:
            while saved < target:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_index % max(1, sample_interval) == 0:
                    try:
                        result = self.datasets.collect_face(person_name, frame)
                    except NoFaceDetected:
                        pass
                    else:
                        detected += result.detected
                        saved += result.saved
                        duplicates += result.duplicates
                    if progress is not None:
                        progress(min(95, 5 + int(frame_index / total_frames * 90)), "正在采集")
                frame_index += 1
        finally:
            capture.release()
        if progress is not None:
            progress(95, "视频采集完成")
        return CollectionResult(detected=detected, saved=saved, duplicates=duplicates)

    def recognize_video(
        self,
        bundle: ModelBundle,
        video_path: Path,
        *,
        output_id: str,
        progress: ProgressCallback | None = None,
    ) -> VideoRecognitionResult:
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            raise ValueError("无法打开视频文件")
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = float(capture.get(cv2.CAP_PROP_FPS)) or 25.0
        total_frames = max(1, int(capture.get(cv2.CAP_PROP_FRAME_COUNT)))
        output = self.datasets.layout.output_path(output_id, "annotated.mp4")
        codec = "avc1"
        writer = cv2.VideoWriter(
            str(output),
            cv2.VideoWriter_fourcc(*codec),  # type: ignore[attr-defined]
            fps,
            (width, height),
        )
        if not writer.isOpened():
            codec = "mp4v"
            writer = cv2.VideoWriter(
                str(output),
                cv2.VideoWriter_fourcc(*codec),  # type: ignore[attr-defined]
                fps,
                (width, height),
            )
        if not writer.isOpened():
            capture.release()
            raise ValueError("无法创建视频输出文件")

        frames_processed = 0
        prediction_count = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                predictions = self._recognize_frame(bundle, frame)
                prediction_count += len(predictions)
                writer.write(draw_predictions(frame, predictions))
                frames_processed += 1
                if progress is not None:
                    progress(
                        min(95, 5 + int(frames_processed / total_frames * 90)),
                        "正在识别视频",
                    )
        finally:
            capture.release()
            writer.release()
        if progress is not None:
            progress(95, "视频识别完成")
        return VideoRecognitionResult(
            output_path=self.datasets.layout.relative(output),
            frames_processed=frames_processed,
            prediction_count=prediction_count,
            codec=codec,
        )

    def _recognize_frame(
        self,
        bundle: ModelBundle,
        frame: np.ndarray,
    ) -> list:
        predictions = []
        for box in self.datasets.detector.detect(frame):
            crop = build_face_crop(frame, box, self.datasets.image_size)
            predictions.append(bundle.predict(crop, box))
        return predictions
