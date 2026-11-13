---
name: chart-check
description: Rules and visual checklist for vessel charts (matplotlib via vessel.charts.Chart, X/feed/story presets). Auto-loaded when editing chart code.
user-invocable: false
paths:
  - "src/vessel/charts/**"
---

## Build

- Always `vessel.charts.Chart(title, subtitle, preset, theme)`; never `pyplot`.
- Title states the conclusion ("Verstappen ganhou 19 posições"); subtitle says what is plotted and the rule used.
- Identity never by color alone: with more than one series, label directly (driver code at the end of the line or next to the bar). Text labels on dark backgrounds get a surface-colored halo (`patheffects.withStroke`).
- One y axis; recessive grid; no extra spines. Inverted axis when lower is better (positions).
- Team and compound colors come from FastF1 (resolved at curation time and stored in the tables); missing color falls back to `theme.muted`.
- Don't connect points across seasons without a race (2020 gap).
- Numbers on axes and labels in pt-BR (`format_decimal`, `format_lap_time`).
- `chart.save(draft_dir, name, sources, handle)` writes the credit footer; list every source actually used (FastF1 colors + Jolpica data → both).

## Check before saying it's done

Render with real data and open the PNG:
- title fits the width (long team names, "na Sprint");
- no overlapping labels; dark team colors (Cadillac, Aston Martin) still visible;
- footer readable and not touching the axis;
- empty space balanced (no huge padding on one side);
- legible on a phone (the X preset is shown at ~1/4 size).
