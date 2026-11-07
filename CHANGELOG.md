# Changelog

All notable changes to Face Workbench are documented here. The project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Unified local Web application for face collection, CNN training, and recognition.
- SQLite metadata store with Alembic migrations and persisted job history.
- Browser camera collection and recognition over WebSocket.
- Automatic dataset refresh and save confirmation after camera collection stops.
- Saved-face management with continue collection, thumbnail review, sample deletion, and person deletion.
- Photo and video collection/recognition jobs with annotated output files.
- React workbench UI, generated OpenAPI types, and responsive design tokens.
- CodeGraph setup guidance and local repository index support.

### Changed

- Replaced duplicated scripts with a layered Python package and thin compatibility wrappers.
- Standardized face detection, label ordering, model metadata, and error handling.
- Upgraded repository tooling, documentation, CI, and dependency management.
