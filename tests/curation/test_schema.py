import pandas as pd
import pytest

from vessel.curation import LAP_DTYPES, RESULT_DTYPES, RaceTables, SchemaError, conform


def test_conform_selects_orders_and_types_columns() -> None:
    frame = pd.DataFrame({"extra": [1], "grid": [3.0], "driver": ["VER"]})

    conformed = conform(frame, {"driver": "string", "grid": "Int16"})

    assert list(conformed.columns) == ["driver", "grid"]
    assert str(conformed["grid"].dtype) == "Int16"


def test_conform_rejects_missing_columns() -> None:
    with pytest.raises(SchemaError, match="grid"):
        conform(
            pd.DataFrame({"driver": ["VER"]}), {"driver": "string", "grid": "Int16"}
        )


def test_recorded_race_matches_curated_schema(race_2026_20: RaceTables) -> None:
    assert dict(race_2026_20.laps.dtypes.astype(str)) == LAP_DTYPES
    assert dict(race_2026_20.results.dtypes.astype(str)) == RESULT_DTYPES
