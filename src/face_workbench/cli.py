from __future__ import annotations

import json
import threading
import time
import webbrowser
from pathlib import Path

import cv2
import typer

from face_workbench.config import Settings
from face_workbench.db import get_active_model
from face_workbench.ml import TrainingOptions
from face_workbench.services.container import AppServices
from face_workbench.services.importer import DirectoryDatasetImporter
from face_workbench.vision import read_image

app = typer.Typer(
    name="face-workbench",
    help="Face Workbench 本地人脸采集、训练与识别工具。",
    no_args_is_help=False,
)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv"}


def _settings() -> Settings:
    return Settings()


def _services() -> AppServices:
    settings = _settings()
    return AppServices(settings)


def _active_model_id(services: AppServices, requested: str | None) -> str:
    if requested:
        return requested
    with services.database.session() as session:
        model = get_active_model(session)
        if model is None:
            raise typer.BadParameter("没有启用模型，请先训练模型或用 --model-id 指定")
        return model.id


def _print_result(value: object) -> None:
    typer.echo(json.dumps(value, ensure_ascii=False, indent=2, default=str))


@app.callback(invoke_without_command=True)
def callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        settings = Settings()
        serve(host=settings.host, port=settings.port, open_browser=True)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="监听地址"),
    port: int = typer.Option(8000, help="监听端口"),
    open_browser: bool = typer.Option(True, help="启动后打开浏览器"),
) -> None:
    """启动 Face Workbench Web 应用。"""
    import uvicorn

    frontend_index = Path(__file__).resolve().parents[2] / "frontend" / "dist" / "index.html"
    if not frontend_index.is_file():
        typer.echo("前端尚未构建，请先运行：pnpm --dir frontend build", err=True)
        raise typer.Exit(code=1)
    if open_browser:
        threading.Timer(1.1, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run(
        "face_workbench.api:create_app",
        factory=True,
        host=host,
        port=port,
        log_level="info",
    )


@app.command("db-upgrade")
def db_upgrade() -> None:
    """升级本地 SQLite 数据库结构。"""
    services = _services()
    services.close()
    typer.echo("数据库已升级到最新版本。")


@app.command("import-dataset")
def import_dataset(
    source: Path = typer.Option(..., "--source", help="按人物目录组织的源数据目录"),
) -> None:
    """将 <姓名>/<图片> 目录中的照片复制并登记到应用存储。"""
    services = _services()
    try:
        result = DirectoryDatasetImporter(services.datasets).import_from(source)
        _print_result(result)
    finally:
        services.close()


@app.command()
def collect(
    source: str = typer.Option(..., help="photo、video 或 camera"),
    person: str = typer.Option(..., help="人物名称"),
    input_path: Path | None = typer.Option(None, "--input", help="照片或视频路径"),
    camera_index: int = typer.Option(0, help="本地摄像头编号"),
    sample_interval: int = typer.Option(10, help="视频隔帧采样数"),
    target: int = typer.Option(200, help="目标样本数"),
) -> None:
    """采集人物人脸样本。"""
    services = _services()
    try:
        if source == "photo":
            if input_path is None:
                raise typer.BadParameter("照片采集需要 --input")
            paths = (
                sorted(
                    path
                    for path in input_path.rglob("*")
                    if path.suffix.casefold() in IMAGE_SUFFIXES
                )
                if input_path.is_dir()
                else [input_path]
            )
            saved = duplicates = missing = invalid = 0
            for path in paths:
                try:
                    frame = read_image(path)
                    result = services.datasets.collect_face(person, frame)
                except ValueError:
                    invalid += 1
                    continue
                saved += result.saved
                duplicates += result.duplicates
                missing += int(result.detected == 0)
            _print_result(
                {
                    "saved": saved,
                    "duplicates": duplicates,
                    "missingFace": missing,
                    "invalid": invalid,
                }
            )
        elif source == "video":
            if input_path is None:
                raise typer.BadParameter("视频采集需要 --input")
            result = services.media.collect_from_video(
                person,
                input_path,
                sample_interval=sample_interval,
                target=target,
            )
            _print_result(result)
        elif source == "camera":
            _collect_camera(services, person, camera_index, target)
        else:
            raise typer.BadParameter("source 必须是 photo、video 或 camera")
    finally:
        services.close()


@app.command()
def train(
    epochs: int = typer.Option(8, min=1, max=100),
    batch_size: int = typer.Option(20, min=1),
    threshold: float = typer.Option(0.7, min=0.01, max=1.0),
    seed: int = typer.Option(42),
) -> None:
    """训练 CNN 并保存带标签元数据的模型。"""
    services = _services()
    try:
        result = services.training.train(
            options=TrainingOptions(
                epochs=epochs,
                batch_size=batch_size,
                seed=seed,
                input_size=services.settings.image_size,
            ),
            threshold=threshold,
            progress=lambda value, message: typer.echo(f"[{value:3d}%] {message}"),
        )
        _print_result(result)
    finally:
        services.close()


@app.command()
def recognize(
    source: str = typer.Option(..., help="photo、video 或 camera"),
    input_path: Path | None = typer.Option(None, "--input", help="照片或视频路径"),
    model_id: str | None = typer.Option(None, help="模型 ID，默认使用当前启用模型"),
    camera_index: int = typer.Option(0, help="本地摄像头编号"),
) -> None:
    """识别照片、视频或本地摄像头中的人脸。"""
    services = _services()
    try:
        resolved_model_id = _active_model_id(services, model_id)
        if source in {"photo", "video"}:
            if input_path is None:
                raise typer.BadParameter(f"{source} 识别需要 --input")
            if source == "photo" and input_path.is_dir():
                paths = sorted(
                    path
                    for path in input_path.rglob("*")
                    if path.suffix.casefold() in IMAGE_SUFFIXES
                )
                for index, path in enumerate(paths):
                    result = services.recognition.recognize_photo(
                        resolved_model_id,
                        path.read_bytes(),
                        output_id=f"cli-{int(time.time())}-{index}",
                    )
                    _print_result(result)
                return
            if source == "photo":
                result = services.recognition.recognize_photo(
                    resolved_model_id,
                    input_path.read_bytes(),
                    output_id=f"cli-{int(time.time())}",
                )
                _print_result(result)
                return
            bundle = services.recognition.load_bundle(resolved_model_id)
            video_result = services.media.recognize_video(
                bundle,
                input_path,
                output_id=f"cli-{int(time.time())}",
            )
            _print_result(video_result)
            return
        if source == "camera":
            _recognize_camera(services, resolved_model_id, camera_index)
            return
        raise typer.BadParameter("source 必须是 photo、video 或 camera")
    finally:
        services.close()


def _collect_camera(
    services: AppServices,
    person: str,
    camera_index: int,
    target: int,
) -> None:
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        raise typer.BadParameter(f"无法打开摄像头 {camera_index}")
    saved = 0
    try:
        typer.echo("按 q 停止采集。")
        while saved < target:
            ok, frame = capture.read()
            if not ok:
                break
            try:
                result = services.datasets.collect_face(person, frame)
                saved += result.saved
            except ValueError:
                pass
            cv2.putText(
                frame,
                f"{person}: {saved}/{target}",
                (16, 36),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (208, 230, 255),
                2,
                cv2.LINE_AA,
            )
            cv2.imshow("Face Workbench - Collect", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()
    typer.echo(f"已保存 {saved} 张人脸。")


def _recognize_camera(services: AppServices, model_id: str, camera_index: int) -> None:
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        raise typer.BadParameter(f"无法打开摄像头 {camera_index}")
    bundle = services.recognition.load_bundle(model_id)
    try:
        typer.echo("按 q 停止识别。")
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            predictions = services.recognition.predict_frame(bundle, frame)
            annotated = frame.copy()
            for prediction in predictions:
                box = prediction.box
                label = (
                    f"{prediction.label} {prediction.confidence:.0%}"
                    if prediction.known
                    else prediction.label
                )
                cv2.rectangle(
                    annotated,
                    (box.x, box.y),
                    (box.x + box.width, box.y + box.height),
                    (208, 230, 255),
                    2,
                )
                cv2.putText(
                    annotated,
                    label,
                    (box.x, max(20, box.y - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (208, 230, 255),
                    2,
                    cv2.LINE_AA,
                )
            cv2.imshow("Face Workbench - Recognize", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    app()
