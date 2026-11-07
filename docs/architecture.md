# Architecture

Face Workbench is a local-first single-user application. The browser hosts the
workbench UI; FastAPI owns validation, persistence, jobs, inference, and static
asset delivery.

```text
React workbench
  ├─ REST jobs ──────── FastAPI services ── SQLite metadata
  │                         │
  └─ camera WebSocket ──────┼── OpenCV face detector
                            ├── TensorFlow CNN
                            └── storage/ media files
```

## Boundaries

- `domain/` contains enums, safe label normalization, and immutable result types.
- `vision/` owns decoding, Haar detection, face crops, and model preparation.
- `ml/` builds/trains the CNN and persists model metadata beside the weights.
- `db/` owns SQLAlchemy models, repositories, SQLite pragmas, and Alembic upgrades.
- `services/` coordinates datasets, jobs, video processing, training, and recognition.
- `api/` exposes the OpenAPI contract and camera WebSocket, then serves the built SPA.
- `frontend/` consumes generated OpenAPI types and owns presentation state.

## Recognition path

Every recognition source is converted to BGR frames. Haar detection returns
face boxes; each valid box is cropped to a 128×128 grayscale image, normalized,
classified, checked against the model threshold, and mapped through the model's
persisted label order. Photo and video outputs are annotated and stored under
`storage/outputs/<job-id>/`.

## Storage

SQLite stores relational metadata only: datasets, persons, media locations,
model records, ordered labels, jobs, and the active model setting. Raw images,
videos, rendered results, and model weights stay on the filesystem. Persisted
paths are relative to `storage/`.

## Jobs

Long-running training and batch operations are serialized in-process and exposed
through a persistent `jobs` table. Starting a second batch job returns HTTP 409.
On restart, unfinished `running` jobs become `interrupted`; they are never
silently resumed. Camera inference is interactive and does not create a job.

Camera collection writes each accepted face immediately. When the user stops,
the UI invalidates the bootstrap query and reports the per-session saved and
duplicate counts. Dataset management endpoints expose only registered face
samples by asset ID; the generic asset endpoint never serves SQLite or dataset
storage directly.
