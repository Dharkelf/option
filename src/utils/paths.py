"""Repository pattern — all file-system paths derived from settings.yaml."""
from pathlib import Path


class PathRepository:
    """Single source of truth for all data file locations."""

    def __init__(self, cfg: dict) -> None:
        self._raw = Path(cfg["paths"]["raw_dir"])
        self._processed = Path(cfg["paths"]["processed_dir"])

    def raw_dir(self) -> Path:
        return self._raw

    def processed_dir(self) -> Path:
        return self._processed

    def raw_file(self, name: str) -> Path:
        return self._raw / f"{name}.parquet"

    def processed_file(self, name: str) -> Path:
        return self._processed / f"{name}.parquet"

    def ensure_dirs(self) -> None:
        self._raw.mkdir(parents=True, exist_ok=True)
        self._processed.mkdir(parents=True, exist_ok=True)
