from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import select

from face_workbench.db import (
    Database,
    Job,
    create_job,
    mark_running_jobs_interrupted,
    update_job,
)
from face_workbench.domain import JobKind, JobStatus


class JobConflict(RuntimeError):
    """Raised when another long-running job is already active."""


class JobContext:
    def __init__(self, database: Database, job_id: str) -> None:
        self.database = database
        self.job_id = job_id

    def update(self, progress: int, message: str) -> None:
        with self.database.session() as session:
            update_job(
                session,
                self.job_id,
                status=JobStatus.RUNNING,
                progress=progress,
                message=message,
            )


Worker = Callable[[JobContext], dict[str, Any]]


class JobManager:
    def __init__(self, database: Database) -> None:
        self.database = database
        self._lock = threading.Lock()
        self._running = False
        with database.session() as session:
            mark_running_jobs_interrupted(session)

    def submit(self, kind: str, payload: dict[str, Any], worker: Worker) -> Job:
        job = self._create_queued_job(kind, payload)
        thread = threading.Thread(
            target=self._execute,
            args=(job.id, worker),
            name=f"face-workbench-{kind}-{job.id[:8]}",
            daemon=True,
        )
        thread.start()
        return job

    def run_sync(self, kind: str, payload: dict[str, Any], worker: Worker) -> Job:
        job = self._create_queued_job(kind, payload)
        self._execute(job.id, worker)
        return self.get(job.id)

    def get(self, job_id: str) -> Job:
        with self.database.session() as session:
            job = session.get_one(Job, job_id)
            session.expunge(job)
            return job

    def list_recent(self, limit: int = 20) -> list[Job]:
        with self.database.session() as session:
            jobs = list(session.scalars(select(Job).order_by(Job.created_at.desc()).limit(limit)))
            for job in jobs:
                session.expunge(job)
            return jobs

    def wait_for(self, job_id: str, timeout: float = 10.0) -> Job:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            job = self.get(job_id)
            if job.status in {
                JobStatus.SUCCEEDED.value,
                JobStatus.FAILED.value,
                JobStatus.INTERRUPTED.value,
            }:
                return job
            time.sleep(0.05)
        raise TimeoutError(f"任务 {job_id} 未在 {timeout} 秒内完成")

    def _create_queued_job(self, kind: str, payload: dict[str, Any]) -> Job:
        with self._lock:
            if self._running:
                raise JobConflict("已有训练或批量任务正在运行")
            self._running = True
        try:
            with self.database.session() as session:
                job = create_job(session, JobKind(kind), payload=payload)
                session.expunge(job)
                return job
        except Exception:
            with self._lock:
                self._running = False
            raise

    def _execute(self, job_id: str, worker: Worker) -> None:
        context = JobContext(self.database, job_id)
        try:
            context.update(1, "任务已启动")
            result = worker(context)
            with self.database.session() as session:
                update_job(
                    session,
                    job_id,
                    status=JobStatus.SUCCEEDED,
                    progress=100,
                    message="任务完成",
                    result=result,
                )
        except Exception as exc:
            with self.database.session() as session:
                update_job(
                    session,
                    job_id,
                    status=JobStatus.FAILED,
                    message="任务失败",
                    error_code="job_failed",
                    error_message=str(exc),
                )
        finally:
            with self._lock:
                self._running = False
