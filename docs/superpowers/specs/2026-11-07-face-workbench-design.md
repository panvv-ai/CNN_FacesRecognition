# Face Workbench Design

## Product

Face Workbench is a local, single-user web application for collecting face
samples from photos, videos, or a browser camera; training the existing CNN
classifier; and recognizing faces from the same three source types.

## Architecture

- FastAPI provides REST jobs, camera WebSocket inference, OpenAPI, and the React SPA.
- SQLAlchemy and Alembic persist metadata in SQLite.
- OpenCV Haar detection feeds one shared 128×128 grayscale preprocessing path.
- TensorFlow/Keras uses persisted label order and thresholds.
- Long-running work is serialized in-process but reflected in the jobs table.

## UX

The single-page workbench uses a floating navigation pill, a scan stage, a task
console, real dataset/model ledgers, job history, and a closing statement. The
visual system uses a dark blue atmospheric canvas, one blue accent, local Manrope
and IBM Plex Mono fonts, and a custom scan-surface signature.

## Quality

Core behavior is covered by unit/API/WebSocket/integration tests. Frontend
behavior is tested with Vitest and responsive behavior with Playwright. Runtime
artifacts, local indexes, and personal media are excluded from Git.
