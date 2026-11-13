import json
import logging
import os
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from vessel.cache.freshness import Freshness

logger = logging.getLogger(__name__)

Clock = Callable[[], datetime]
Loader = Callable[[], bytes]

_KEY = re.compile(r"^[a-z0-9][a-z0-9_.-]*(/[a-z0-9][a-z0-9_.-]*)*$")
_META_SUFFIX = ".meta.json"
_TMP_SUFFIX = ".tmp"


def utc_now() -> datetime:
    return datetime.now(UTC)


class InvalidCacheKeyError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CacheEntry:
    data: bytes
    written_at: datetime


class FileCache:
    def __init__(self, root: Path, clock: Clock = utc_now) -> None:
        self._root = root
        self._clock = clock

    def read(self, key: str) -> CacheEntry | None:
        data_path, meta_path = self._paths(key)
        if not (data_path.is_file() and meta_path.is_file()):
            return None
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return CacheEntry(
            data=data_path.read_bytes(),
            written_at=datetime.fromisoformat(meta["written_at"]),
        )

    def get(self, key: str, freshness: Freshness) -> bytes | None:
        entry = self.read(key)
        if entry is None or not freshness.is_fresh(entry.written_at, self._clock()):
            return None
        return entry.data

    def put(self, key: str, data: bytes) -> None:
        data_path, meta_path = self._paths(key)
        data_path.parent.mkdir(parents=True, exist_ok=True)
        meta = json.dumps({"written_at": self._clock().isoformat()})
        _atomic_write(data_path, data)
        _atomic_write(meta_path, meta.encode("utf-8"))

    def fetch(self, key: str, freshness: Freshness, loader: Loader) -> bytes:
        cached = self.get(key, freshness)
        if cached is not None:
            return cached
        try:
            data = loader()
        except Exception:
            stale = self.read(key)
            if stale is None:
                raise
            logger.warning("serving stale cache for %s after loader failure", key)
            return stale.data
        self.put(key, data)
        return data

    def _paths(self, key: str) -> tuple[Path, Path]:
        if not _KEY.fullmatch(key) or key.endswith((_META_SUFFIX, _TMP_SUFFIX)):
            raise InvalidCacheKeyError(key)
        data_path = self._root / key
        return data_path, data_path.with_name(data_path.name + _META_SUFFIX)


def _atomic_write(path: Path, data: bytes) -> None:
    tmp_path = path.with_name(path.name + _TMP_SUFFIX)
    tmp_path.write_bytes(data)
    os.replace(tmp_path, path)
