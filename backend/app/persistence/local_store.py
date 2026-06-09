from __future__ import annotations

from pathlib import Path

from app.models.ambience import Ambience
from app.models.errors import AmbienceStorageError


class LocalStore:
    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def save(self, ambience: Ambience) -> None:
        path = self._data_dir / f"{ambience.uuid}.json"
        try:
            path.write_text(ambience.model_dump_json(indent=2), encoding="utf-8")
        except OSError as exc:
            raise AmbienceStorageError(f"Failed to write ambience: {exc}") from exc
