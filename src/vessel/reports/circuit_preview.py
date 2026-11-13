from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from vessel.analytics.circuit_history import FEW_EDITIONS, circuit_facts, editions
from vessel.analytics.form import (
    ChampionshipMath,
    championship_facts,
    championship_math,
    current_grid,
    form_facts,
    recent_form,
)
from vessel.charts.output import save_chart
from vessel.charts.specs.circuit_preview import (
    grid_timeline_spec,
    ranked_dots_spec,
)
from vessel.curation.schema import SeasonTables
from vessel.domain import ChartRef, Draft, Event, Segment, Source
from vessel.reports.drafts import draft_dir, write_draft

FIXED_CAVEATS = (
    "O regulamento técnico novo de 2026 reduz o peso do histórico do circuito.",
    "Média de chegada usa a posição oficial: abandonos entram na ordem de "
    "classificação da corrida.",
)


@dataclass(frozen=True, slots=True)
class Preview:
    draft: Draft
    math: ChampionshipMath | None


def circuit_preview_dir(out_dir: Path, event: Event) -> Path:
    return draft_dir(out_dir, event, Segment.CIRCUIT_PREVIEW)


def build_circuit_preview(
    event: Event,
    events: tuple[Event, ...],
    *,
    history: pd.DataFrame,
    season: SeasonTables,
    team_colors: Mapping[str, str],
    directory: Path,
    handle: str,
    now: datetime,
) -> Preview:
    directory.mkdir(parents=True, exist_ok=True)
    form = recent_form(season.results)
    math = championship_math(season.standings, events, event)
    facts = (
        circuit_facts(
            history, current_grid(season.results), event.location, Source.JOLPICA
        )
        + form_facts(form, Source.JOLPICA)
        + championship_facts(math, Source.JOLPICA)
    )
    charts: list[ChartRef] = []
    if not history.empty:
        charts.append(
            save_chart(
                grid_timeline_spec(history, event.location),
                directory,
                "winners",
                handle,
            )
        )
    if not form.empty and not season.standings.empty:
        charts.append(
            save_chart(
                ranked_dots_spec(form, season.standings, team_colors),
                directory,
                "form",
                handle,
            )
        )
    draft = Draft(
        segment=Segment.CIRCUIT_PREVIEW,
        event=event.ref,
        facts=facts,
        caveats=_caveats(history, math),
        charts=tuple(charts),
        generated_at=now,
    )
    write_draft(draft, directory)
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
