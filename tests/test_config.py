from pathlib import Path

import pytest

from vessel.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(data_dir=tmp_path / "data", _env_file=None)


def test_defaults_point_to_profile_and_cuiaba(settings: Settings) -> None:
    assert settings.handle == "1caiocarvalho"
    assert settings.tz.key == "America/Cuiaba"


def test_ensure_dirs_creates_layers(settings: Settings) -> None:
    settings.ensure_dirs()

    assert settings.cache_dir.is_dir()
    assert settings.curated_dir.is_dir()
    assert settings.out_dir.is_dir()


def test_env_overrides_handle(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VESSEL_HANDLE", "outro")

    assert Settings(data_dir=tmp_path, _env_file=None).handle == "outro"
