from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from vessel.analytics.circuit_history import (
    CIRCUIT_FACTS,
    FEW_EDITIONS,
    circuit_params,
    editions,
)
from vessel.analytics.form import (
    CHAMPIONSHIP_FACTS,
    FORM_FACTS,
    ChampionshipMath,
    championship_math,
    championship_params,
    form_params,
    recent_form,
)
from vessel.analytics.registry import CalcInputs, compute_facts
from vessel.charts.output import save_registered_chart
from vessel.curation.schema import RaceTables, SeasonTables
from vessel.domain import (
    ChartRef,
    CircuitHistoryRef,
    Draft,
    Event,
    SeasonTableRef,
    Segment,
    SessionTableRef,
    TableRef,
)
from vessel.reports.drafts import Verifier, draft_dir, publish_draft

FIXED_CAVEATS = (
    "O regulamento técnico novo de 2026 reduz o peso do histórico do circuito.",
    "Média de chegada usa a posição oficial: abandonos entram na ordem de "
    "classificação da corrida.",
)


@dataclass(frozen=True, slots=True)
class Preview:
    draft: Draft
    math: ChampionshipMath | None


@dataclass(frozen=True, slots=True)
class PreviewInputs:
    circuit: CircuitHistoryRef
    history: pd.DataFrame
    season: SeasonTables
    last_race: tuple[SessionTableRef, RaceTables] | None = None


def circuit_preview_dir(out_dir: Path, event: Event) -> Path:
    return draft_dir(out_dir, event, Segment.CIRCUIT_PREVIEW)


def build_circuit_preview(
    event: Event,
    events: tuple[Event, ...],
    data: PreviewInputs,
    directory: Path,
    *,
    handle: str,
    now: datetime,
    verify: Verifier,
) -> Preview:
    directory.mkdir(parents=True, exist_ok=True)
    season_ref = SeasonTableRef(season=event.season)
    inputs = CalcInputs(
        history_table=data.history,
        season_tables=data.season,
        race_tables=data.last_race[1] if data.last_race else None,
    )
    location = circuit_params(event.location, data.circuit.editions)
    form = form_params()
    title = championship_params(events, event)
    facts = (
        compute_facts(CIRCUIT_FACTS, inputs, (data.circuit, season_ref), location)
        + compute_facts(FORM_FACTS, inputs, (season_ref,), form)
        + compute_facts(CHAMPIONSHIP_FACTS, inputs, (season_ref,), title)
    )
    charts: list[ChartRef] = []
    if not data.history.empty:
        charts.append(
            save_registered_chart(
                "chart.winners",
                inputs,
                (data.circuit,),
                location,
                (directory, "winners", handle),
            )
        )
    if not recent_form(data.season.results).empty and not data.season.standings.empty:
        form_refs: tuple[TableRef, ...] = (season_ref,)
        if data.last_race:
            form_refs += (data.last_race[0],)
        charts.append(
            save_registered_chart(
                "chart.form", inputs, form_refs, form, (directory, "form", handle)
            )
        )
    math = championship_math(data.season.standings, title)
    draft = Draft(
        segment=Segment.CIRCUIT_PREVIEW,
        event=event.ref,
        facts=facts,
        caveats=_caveats(data.history, math),
        charts=tuple(charts),
        generated_at=now,
    )
    publish_draft(draft, directory, verify)
    return Preview(draft=draft, math=math)


def _caveats(history: pd.DataFrame, math: ChampionshipMath | None) -> tuple[str, ...]:
    caveats = list(FIXED_CAVEATS)
    count = editions(history)
    if 0 < count < FEW_EDITIONS:
        caveats.append(
            f"Circuito com poucas edições ({count}): o histórico pesa pouco."
        )
    if math is not None and math.at_risk:
        rounds = ", ".join(str(round_) for round_ in math.at_risk)
        caveats.append(
            f"Pontos em disputa incluem rodadas em risco ({rounds}); "
            "se forem canceladas, a conta muda."
        )
    if math is not None:
        caveats.append("Empate em pontos no fim é decidido pelo número de vitórias.")
    return tuple(caveats)
