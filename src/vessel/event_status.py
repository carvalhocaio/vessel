import tomllib
from pathlib import Path

from pydantic import RootModel, ValidationError

from vessel.domain import Event, EventNotice


class EventStatusFileError(ValueError):
    pass


class StatusRegistry(RootModel[dict[int, dict[int, EventNotice]]]):
    def notices(self, season: int) -> dict[int, EventNotice]:
        return self.root.get(season, {})


EMPTY_REGISTRY = StatusRegistry({})


def load_event_status(path: Path) -> StatusRegistry:
    if not path.is_file():
        return EMPTY_REGISTRY
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        return StatusRegistry.model_validate(document)
    except tomllib.TOMLDecodeError as exc:
        raise EventStatusFileError(f"{path}: invalid TOML ({exc})") from exc
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise EventStatusFileError(f"{path}: {problems}") from exc


class EventStatusFile:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.registry = load_event_status(path)

    def apply(self, events: tuple[Event, ...]) -> tuple[Event, ...]:
        if not events:
            return events
        season = events[0].season
        notices = self.registry.notices(season)
        unknown = sorted(set(notices) - {event.round for event in events})
        if unknown:
            rounds = ", ".join(str(round_) for round_ in unknown)
            raise EventStatusFileError(
                f"{self.path}: {season} round {rounds} does not exist"
            )
        return tuple(
            event.with_notice(notices[event.round]) if event.round in notices else event
            for event in events
        )
