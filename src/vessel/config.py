from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class CalendarFeeds(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VESSEL_ICAL_", env_file=".env", extra="ignore"
    )

    f1: HttpUrl | None = None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="VESSEL_", env_file=".env", extra="ignore"
    )

    handle: str = "1caiocarvalho"
    timezone: str = "America/Cuiaba"
    data_dir: Path = Path("data")
    event_status_path: Path = Path("config/event_status.toml")
    circuits_path: Path = Path("config/circuits.toml")
    calendars: CalendarFeeds = Field(default_factory=CalendarFeeds)

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def http_cache_dir(self) -> Path:
        return self.cache_dir / "http"

    @property
    def fastf1_cache_dir(self) -> Path:
        return self.cache_dir / "fastf1"

    @property
    def curated_dir(self) -> Path:
        return self.data_dir / "curated"

    @property
    def out_dir(self) -> Path:
        return self.data_dir / "out"

    def ensure_dirs(self) -> None:
        for directory in (self.cache_dir, self.curated_dir, self.out_dir):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
