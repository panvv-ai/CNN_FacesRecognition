from __future__ import annotations

import json
import tempfile
from pathlib import Path

from face_workbench.api import create_app
from face_workbench.config import Settings


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        settings = Settings(storage_dir=Path(temporary) / "storage")
        app = create_app(settings)
        schema = app.openapi()
        app.state.services.close()
    output = Path(__file__).resolve().parents[1] / "openapi.json"
    output.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
