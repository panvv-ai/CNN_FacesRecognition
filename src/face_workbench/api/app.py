from __future__ import annotations

from collections.abc import Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from face_workbench.api.schemas import (
    BootstrapView,
    DatasetView,
    DeleteFaceView,
    DeletePersonView,
    FaceAssetView,
    JobView,
    ModelView,
    PersonCreate,
    PersonView,
    TrainingRequest,
)
from face_workbench.config import PROJECT_ROOT, Settings
from face_workbench.db import get_active_model, list_models, set_active_model
from face_workbench.domain import InvalidPersonName
from face_workbench.ml import ModelBundle, TrainingOptions
from face_workbench.services.container import AppServices
from face_workbench.services.datasets import (
    FaceAssetNotFound,
    NoFaceDetected,
    PersonNotFound,
)
from face_workbench.services.jobs import JobConflict, JobContext
from face_workbench.vision import InvalidImageError, decode_image_bytes


def prediction_payload(prediction: Any) -> dict[str, Any]:
    box = prediction.box
    return {
        "box": [box.x, box.y, box.width, box.height],
        "label": prediction.label,
        "confidence": prediction.confidence,
        "known": prediction.known,
    }


def _bootstrap(services: AppServices) -> BootstrapView:
    with services.database.session() as session:
        active_model = get_active_model(session)
        models = list_models(session)
        active_model_id = active_model.id if active_model is not None else None
        model_views = [
            ModelView.from_entity(model, active=model.id == active_model_id) for model in models
        ]
    return BootstrapView(
        engine_ready=True,
        dataset=DatasetView.from_overview(services.datasets.overview()),
        models=model_views,
        active_model_id=active_model_id,
        recent_jobs=[JobView.from_entity(job) for job in services.jobs.list_recent()],
        camera_frame_edge=services.settings.camera_frame_edge,
        threshold=services.settings.threshold,
    )


def create_app(
    settings: Settings | None = None,
    *,
    detector: object | None = None,
    trainer: object | None = None,
    bundle_loader: Callable[[Path], ModelBundle] | None = None,
) -> FastAPI:
    resolved_settings = settings or Settings()
    services = AppServices(
        resolved_settings,
        detector=detector,
        trainer=trainer,
        bundle_loader=bundle_loader,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        services.close()

    app = FastAPI(
        title="Face Workbench API",
        version="0.1.0",
        description="Local face collection, CNN training, and recognition API.",
        lifespan=lifespan,
    )
    app.state.services = services
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/bootstrap", response_model=BootstrapView)
    def bootstrap() -> BootstrapView:
        return _bootstrap(services)

    @app.post("/api/dataset/persons", response_model=PersonView, status_code=201)
    def create_person(payload: PersonCreate) -> PersonView:
        try:
            person = services.datasets.ensure_person(payload.name)
        except InvalidPersonName as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return PersonView.from_entity(person)

    @app.get(
        "/api/dataset/persons/{person_id}/faces",
        response_model=list[FaceAssetView],
    )
    def list_person_faces(person_id: int) -> list[FaceAssetView]:
        try:
            faces = services.datasets.list_faces(person_id)
        except PersonNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return [
            FaceAssetView(
                id=face.id,
                image_url=f"/api/dataset/faces/{face.id}/image",
                created_at=face.created_at,
            )
            for face in faces
        ]

    @app.get("/api/dataset/faces/{asset_id}/image")
    def face_image(asset_id: str) -> FileResponse:
        try:
            path = services.datasets.face_image_path(asset_id)
        except FaceAssetNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return FileResponse(
            path,
            media_type="image/jpeg",
            headers={"Cache-Control": "private, no-store"},
        )

    @app.delete("/api/dataset/faces/{asset_id}", response_model=DeleteFaceView)
    def delete_face(asset_id: str) -> DeleteFaceView:
        if not services.datasets.delete_face(asset_id):
            raise HTTPException(status_code=404, detail="人脸样本不存在")
        return DeleteFaceView(deleted=True)

    @app.delete("/api/dataset/persons/{person_id}", response_model=DeletePersonView)
    def delete_person(person_id: int) -> DeletePersonView:
        try:
            removed_faces = services.datasets.delete_person(person_id)
        except PersonNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return DeletePersonView(deleted=True, removed_faces=removed_faces)

    @app.post("/api/jobs/collect", response_model=JobView, status_code=202)
    async def collect_job(
        person: str = Form(...),
        source: str = Form(...),
        files: list[UploadFile] = File(...),
        sample_interval: int = Form(10),
        target: int = Form(200),
    ) -> JobView:
        if source not in {"photo", "video"}:
            raise HTTPException(status_code=422, detail="采集来源必须是 photo 或 video")
        if source == "video" and len(files) != 1:
            raise HTTPException(status_code=422, detail="视频采集一次只能上传一个文件")
        try:
            services.datasets.ensure_person(person)
        except InvalidPersonName as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        file_payloads: list[tuple[str, bytes]] = []
        total_size = 0
        for upload in files:
            data = await upload.read()
            total_size += len(data)
            file_payloads.append((upload.filename or "upload", data))
        max_size = (
            services.settings.max_video_bytes
            if source == "video"
            else services.settings.max_image_bytes * max(1, len(files))
        )
        if total_size > max_size:
            raise HTTPException(status_code=413, detail="上传文件超过大小限制")

        def worker(context: JobContext) -> dict[str, Any]:
            if source == "video":
                filename, data = file_payloads[0]
                path = services.layout.upload_path(context.job_id, filename)
                path.write_bytes(data)
                result = services.media.collect_from_video(
                    person,
                    path,
                    sample_interval=sample_interval,
                    target=target,
                    progress=context.update,
                )
                return {
                    "detected": result.detected,
                    "saved": result.saved,
                    "duplicates": result.duplicates,
                }
            detected = saved = duplicates = invalid = missing = 0
            for index, (_, data) in enumerate(file_payloads):
                try:
                    frame = decode_image_bytes(data)
                    result = services.datasets.collect_face(person, frame)
                except InvalidImageError:
                    invalid += 1
                except NoFaceDetected:
                    missing += 1
                else:
                    detected += result.detected
                    saved += result.saved
                    duplicates += result.duplicates
                context.update(
                    min(95, 5 + int((index + 1) / len(file_payloads) * 90)),
                    "正在采集照片",
                )
            return {
                "detected": detected,
                "saved": saved,
                "duplicates": duplicates,
                "invalid": invalid,
                "missingFace": missing,
            }

        try:
            job = services.jobs.submit(
                "collect",
                {"source": source, "person": person, "fileCount": len(files)},
                worker,
            )
        except JobConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return JobView.from_entity(job)

    @app.post("/api/jobs/train", response_model=JobView, status_code=202)
    def train_job(payload: TrainingRequest) -> JobView:
        def worker(context: JobContext) -> dict[str, Any]:
            summary = services.training.train(
                options=TrainingOptions(
                    epochs=payload.epochs,
                    batch_size=payload.batch_size,
                    seed=payload.seed,
                    input_size=services.settings.image_size,
                ),
                threshold=payload.threshold,
                progress=context.update,
            )
            return {
                "modelId": summary.model_id,
                "labels": list(summary.labels),
                "metrics": summary.metrics,
                "artifactPath": summary.artifact_path,
            }

        try:
            job = services.jobs.submit("train", payload.model_dump(), worker)
        except JobConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return JobView.from_entity(job)

    @app.post("/api/jobs/recognize", response_model=JobView, status_code=202)
    async def recognize_job(
        model_id: str = Form(...),
        source: str = Form(...),
        files: list[UploadFile] = File(...),
    ) -> JobView:
        if source not in {"photo", "video"}:
            raise HTTPException(status_code=422, detail="识别来源必须是 photo 或 video")
        file_payloads: list[tuple[str, bytes]] = []
        total_size = 0
        for upload in files:
            data = await upload.read()
            total_size += len(data)
            file_payloads.append((upload.filename or "upload", data))
        max_size = (
            services.settings.max_video_bytes
            if source == "video"
            else services.settings.max_image_bytes * max(1, len(files))
        )
        if total_size > max_size:
            raise HTTPException(status_code=413, detail="上传文件超过大小限制")
        if source == "video" and len(file_payloads) != 1:
            raise HTTPException(status_code=422, detail="视频识别一次只能上传一个文件")

        def worker(context: JobContext) -> dict[str, Any]:
            bundle = services.recognition.load_bundle(model_id)
            if source == "video":
                filename, data = file_payloads[0]
                path = services.layout.upload_path(context.job_id, filename)
                path.write_bytes(data)
                video_result = services.media.recognize_video(
                    bundle,
                    path,
                    output_id=context.job_id,
                    progress=context.update,
                )
                return {
                    "outputs": [
                        {
                            "outputPath": video_result.output_path,
                            "framesProcessed": video_result.frames_processed,
                            "predictionCount": video_result.prediction_count,
                            "codec": video_result.codec,
                        }
                    ]
                }
            outputs: list[dict[str, Any]] = []
            for index, (_, data) in enumerate(file_payloads):
                frame = decode_image_bytes(data)
                photo_result = services.recognition.recognize_photo_with_bundle(
                    bundle,
                    frame,
                    output_id=f"{context.job_id}-{index + 1}",
                )
                outputs.append(
                    {
                        "outputPath": photo_result.output_path,
                        "width": photo_result.width,
                        "height": photo_result.height,
                        "predictions": [
                            prediction_payload(prediction)
                            for prediction in photo_result.predictions
                        ],
                    }
                )
                context.update(
                    min(95, 5 + int((index + 1) / len(file_payloads) * 90)),
                    "正在识别照片",
                )
            return {"outputs": outputs}

        try:
            job = services.jobs.submit(
                "recognize",
                {"source": source, "modelId": model_id, "fileCount": len(files)},
                worker,
            )
        except JobConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return JobView.from_entity(job)

    @app.get("/api/jobs", response_model=list[JobView])
    def jobs() -> list[JobView]:
        return [JobView.from_entity(job) for job in services.jobs.list_recent()]

    @app.get("/api/jobs/{job_id}", response_model=JobView)
    def get_job(job_id: str) -> JobView:
        try:
            return JobView.from_entity(services.jobs.get(job_id))
        except Exception as exc:
            from sqlalchemy.exc import NoResultFound

            if isinstance(exc, NoResultFound):
                raise HTTPException(status_code=404, detail="任务不存在") from exc
            raise

    @app.get("/api/models", response_model=list[ModelView])
    def models() -> list[ModelView]:
        with services.database.session() as session:
            active = get_active_model(session)
            active_id = active.id if active is not None else None
            return [
                ModelView.from_entity(model, active=model.id == active_id)
                for model in list_models(session)
            ]

    @app.post("/api/models/{model_id}/activate", response_model=ModelView)
    def activate_model(model_id: str) -> ModelView:
        with services.database.session() as session:
            candidates = list_models(session)
            selected = next((item for item in candidates if item.id == model_id), None)
            if selected is None:
                raise HTTPException(status_code=404, detail="模型不存在")
            set_active_model(session, model_id)
            return ModelView.from_entity(selected, active=True)

    @app.get("/api/assets/{relative_path:path}")
    def asset(relative_path: str) -> FileResponse:
        try:
            path = services.layout.resolve(relative_path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="非法资源路径") from exc
        allowed_roots = (
            services.layout.outputs.resolve(),
            services.layout.uploads.resolve(),
        )
        if not any(path.resolve().is_relative_to(root) for root in allowed_roots):
            raise HTTPException(status_code=404, detail="资源不存在")
        if not path.is_file():
            raise HTTPException(status_code=404, detail="资源不存在")
        return FileResponse(path)

    @app.websocket("/api/ws/camera")
    async def camera_socket(websocket: WebSocket) -> None:
        mode = websocket.query_params.get("mode", "recognize")
        bundle: ModelBundle | None = None
        person = websocket.query_params.get("person", "")
        if mode == "recognize":
            model_id = websocket.query_params.get("model_id")
            if not model_id:
                await websocket.close(code=1008, reason="缺少模型 ID")
                return
            try:
                bundle = services.recognition.load_bundle(model_id)
            except Exception as exc:
                await websocket.close(code=1008, reason=str(exc))
                return
        elif mode == "collect":
            try:
                services.datasets.ensure_person(person)
            except InvalidPersonName as exc:
                await websocket.close(code=1008, reason=str(exc))
                return
        else:
            await websocket.close(code=1008, reason="未知摄像头模式")
            return

        await websocket.accept()
        frame_id = 0
        saved = duplicates = 0
        try:
            while True:
                data = await websocket.receive_bytes()
                frame_id += 1
                if len(data) > services.settings.max_image_bytes:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "frameId": frame_id,
                            "message": "摄像头帧超过大小限制",
                            "detections": [],
                        }
                    )
                    continue
                try:
                    frame = decode_image_bytes(data)
                except InvalidImageError as exc:
                    await websocket.send_json(
                        {
                            "type": "error",
                            "frameId": frame_id,
                            "message": str(exc),
                            "detections": [],
                        }
                    )
                    continue
                if mode == "collect":
                    try:
                        result = services.datasets.collect_face(person, frame)
                    except NoFaceDetected:
                        await websocket.send_json(
                            {
                                "type": "collection",
                                "frameId": frame_id,
                                "saved": saved,
                                "duplicates": duplicates,
                                "detections": [],
                            }
                        )
                        continue
                    saved += result.saved
                    duplicates += result.duplicates
                    await websocket.send_json(
                        {
                            "type": "collection",
                            "frameId": frame_id,
                            "saved": saved,
                            "duplicates": duplicates,
                            "detections": [],
                        }
                    )
                else:
                    assert bundle is not None
                    predictions = services.recognition.predict_frame(bundle, frame)
                    height, width = frame.shape[:2]
                    await websocket.send_json(
                        {
                            "type": "prediction",
                            "frameId": frame_id,
                            "width": width,
                            "height": height,
                            "detections": [
                                prediction_payload(prediction) for prediction in predictions
                            ],
                        }
                    )
        except WebSocketDisconnect:
            return

    frontend_dist = PROJECT_ROOT / "frontend" / "dist"
    assets_dir = frontend_dist / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="接口不存在")
        candidate = (frontend_dist / full_path).resolve()
        if full_path and candidate.is_relative_to(frontend_dist.resolve()) and candidate.is_file():
            return FileResponse(candidate)
        index = frontend_dist / "index.html"
        if not index.is_file():
            raise HTTPException(
                status_code=503,
                detail="前端尚未构建。请先在 frontend/ 中运行 pnpm build。",
            )
        return FileResponse(index)

    return app
