from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from vessel.cache import FileCache, Forever, InvalidCacheKeyError, Ttl

T0 = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
KEY = "calendar/f1.ics"


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


class CountingLoader:
    def __init__(self, payload: bytes = b"payload") -> None:
        self.payload = payload
        self.calls = 0

    def __call__(self) -> bytes:
        self.calls += 1
        return self.payload


def _failing_loader() -> bytes:
    raise ConnectionError("source down")


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(T0)


@pytest.fixture
def cache(tmp_path: Path, clock: FakeClock) -> FileCache:
    return FileCache(tmp_path, clock=clock)


def test_put_then_read_keeps_data_and_write_time(cache: FileCache) -> None:
    cache.put(KEY, b"BEGIN:VCALENDAR")

    entry = cache.read(KEY)

    assert entry is not None
    assert entry.data == b"BEGIN:VCALENDAR"
    assert entry.written_at == T0


def test_missing_key_reads_none(cache: FileCache) -> None:
    assert cache.read(KEY) is None
    assert cache.get(KEY, Forever()) is None


def test_get_respects_freshness(cache: FileCache, clock: FakeClock) -> None:
    cache.put(KEY, b"x")
    clock.advance(timedelta(hours=2))

    assert cache.get(KEY, Ttl(timedelta(hours=1))) is None
    assert cache.get(KEY, Forever()) == b"x"


def test_fetch_loads_once_while_fresh(cache: FileCache) -> None:
    loader = CountingLoader()

    first = cache.fetch(KEY, Forever(), loader)
    second = cache.fetch(KEY, Forever(), loader)

    assert first == second == b"payload"
    assert loader.calls == 1


def test_fetch_reloads_when_stale(cache: FileCache, clock: FakeClock) -> None:
    loader = CountingLoader()
    cache.fetch(KEY, Ttl(timedelta(minutes=5)), loader)
    clock.advance(timedelta(minutes=10))

    cache.fetch(KEY, Ttl(timedelta(minutes=5)), loader)

    assert loader.calls == 2


def test_fetch_serves_stale_entry_when_source_fails(
    cache: FileCache, clock: FakeClock
) -> None:
    cache.put(KEY, b"old")
    clock.advance(timedelta(days=1))

    assert cache.fetch(KEY, Ttl(timedelta(minutes=5)), _failing_loader) == b"old"


def test_fetch_raises_when_source_fails_without_cache(cache: FileCache) -> None:
    with pytest.raises(ConnectionError):
        cache.fetch(KEY, Forever(), _failing_loader)


def test_put_leaves_no_temporary_files(cache: FileCache, tmp_path: Path) -> None:
    cache.put(KEY, b"x")

    assert not list(tmp_path.rglob("*.tmp"))


@pytest.mark.parametrize(
    "key",
    ["", "../secret", "/etc/passwd", "Calendar/f1.ics", "a//b", "a.meta.json", "a.tmp"],
)
def test_rejects_unsafe_keys(cache: FileCache, key: str) -> None:
    with pytest.raises(InvalidCacheKeyError):
        cache.put(key, b"x")
