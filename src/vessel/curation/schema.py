from dataclasses import dataclass

import pandas as pd

LAP_DTYPES: dict[str, str] = {
    "driver": "string",
    "team": "string",
    "lap": "Int16",
    "lap_time_s": "Float64",
    "stint": "Int16",
    "compound": "string",
    "compound_color": "string",
    "tyre_life": "Int16",
    "position": "Int16",
    "pit_in": "boolean",
    "pit_out": "boolean",
    "track_status": "string",
    "is_accurate": "boolean",
}

DRIVER_DTYPES: dict[str, str] = {
    "driver": "string",
    "name": "string",
    "team": "string",
    "team_color": "string",
    "nationality": "string",
}

RESULT_DTYPES: dict[str, str] = {
    **DRIVER_DTYPES,
    "grid": "Int16",
    "finish": "Int16",
    "classified": "boolean",
    "status": "string",
    "points": "Float64",
}


class SchemaError(ValueError):
    pass


def conform(frame: pd.DataFrame, dtypes: dict[str, str]) -> pd.DataFrame:
    missing = [column for column in dtypes if column not in frame.columns]
    if missing:
        raise SchemaError(f"missing columns: {', '.join(missing)}")
    return frame[list(dtypes)].astype(dtypes).reset_index(drop=True)


@dataclass(frozen=True, slots=True)
class RaceTables:
    laps: pd.DataFrame
    results: pd.DataFrame

    def conformed(self) -> "RaceTables":
        return RaceTables(
            laps=conform(self.laps, LAP_DTYPES),
            results=conform(self.results, RESULT_DTYPES),
        )


@dataclass(frozen=True, slots=True)
class SessionTables:
    laps: pd.DataFrame
    drivers: pd.DataFrame

    def conformed(self) -> "SessionTables":
        return SessionTables(
            laps=conform(self.laps, LAP_DTYPES),
            drivers=conform(self.drivers, DRIVER_DTYPES),
        )
