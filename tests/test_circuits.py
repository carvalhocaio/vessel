from pathlib import Path

import pytest

from vessel.circuits import CircuitMapError, load_circuits
from vessel.domain import Event

CONFIG = Path(__file__).parent.parent / "config" / "circuits.toml"


def test_every_2026_event_has_a_circuit(schedule_2026: tuple[Event, ...]) -> None:
    circuits = load_circuits(CONFIG)

    mapped = {
        event.round: circuits.circuit_for(event, CONFIG) for event in schedule_2026
    }

    assert mapped[16] == "sepang"
    assert mapped[20] == "interlagos"
    assert mapped[21] == "vegas"
    assert mapped[14] == "madring"


def test_missing_location_fails_clearly(
    tmp_path: Path, schedule_2026: tuple[Event, ...]
) -> None:
    path = tmp_path / "circuits.toml"
    path.write_text('"Las Vegas" = "vegas"\n', encoding="utf-8")

    with pytest.raises(CircuitMapError, match="no circuit for location 'São Paulo'"):
        load_circuits(path).circuit_for(
            next(e for e in schedule_2026 if e.round == 20), path
        )


def test_broken_file_fails_clearly(tmp_path: Path) -> None:
    path = tmp_path / "circuits.toml"
    path.write_text('"Las Vegas" = \n', encoding="utf-8")

    with pytest.raises(CircuitMapError, match="invalid TOML"):
        load_circuits(path)


def test_absent_file_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(CircuitMapError, match="file not found"):
        load_circuits(tmp_path / "absent.toml")
