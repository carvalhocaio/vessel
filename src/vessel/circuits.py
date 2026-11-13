import tomllib
from pathlib import Path

from pydantic import Field, RootModel, ValidationError

from vessel.domain import Event

CircuitId = str


class CircuitMapError(ValueError):
    pass


class CircuitMap(RootModel[dict[str, CircuitId]]):
    root: dict[str, CircuitId] = Field(default_factory=dict)

    def circuit_for(self, event: Event, source: Path) -> CircuitId:
        circuit = self.root.get(event.location)
        if circuit is None:
            raise CircuitMapError(
                f"{source}: no circuit for location {event.location!r}; "
                f"add it to {source}"
            )
        return circuit


def load_circuits(path: Path) -> CircuitMap:
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        return CircuitMap.model_validate(document)
    except FileNotFoundError as exc:
        raise CircuitMapError(f"{path}: file not found") from exc
    except tomllib.TOMLDecodeError as exc:
        raise CircuitMapError(f"{path}: invalid TOML ({exc})") from exc
    except ValidationError as exc:
        raise CircuitMapError(f"{path}: {exc.errors()[0]['msg']}") from exc
