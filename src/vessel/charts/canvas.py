import re
from collections.abc import Iterable
from pathlib import Path

from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from vessel.charts.theme import DARK, Theme
from vessel.domain import ChartPreset, Source
from vessel.formatting import format_decimal

DPI = 200
BASE_WIDTH_PX = 1600
CHARTS_DIR = "charts"

PRESET_SIZES_PX = {
    ChartPreset.X: (1600, 900),
    ChartPreset.FEED: (1080, 1350),
    ChartPreset.STORY: (1080, 1920),
}

MARGIN_PX = 64
TICK_LABEL_PX = 88
HEADER_PX = 210
FOOTER_PX = 160
SUBTITLE_OFFSET_PX = 72
CREDIT_BASELINE_PX = 40

TITLE_PT = 20
SUBTITLE_PT = 13
TICK_PT = 11
CREDIT_PT = 10

_CHART_NAME = re.compile(r"^[a-z][a-z0-9_]*$")


def credit_line(sources: Iterable[Source], handle: str) -> str:
    used = set(sources)
    if not used:
        raise ValueError("a chart needs at least one data source")
    names = " / ".join(source.value for source in Source if source in used)
    return f"Dados: {names} · @{handle}"


def decimal_formatter(places: int = 1) -> FuncFormatter:
    return FuncFormatter(lambda value, _: format_decimal(value, places))


class Chart:
    def __init__(
        self,
        title: str,
        subtitle: str | None = None,
        preset: ChartPreset = ChartPreset.X,
        theme: Theme = DARK,
    ) -> None:
        self.preset = preset
        self.theme = theme
        self._width, self._height = PRESET_SIZES_PX[preset]
        self._scale = self._width / BASE_WIDTH_PX
        self.figure = Figure(
            figsize=(self._width / DPI, self._height / DPI),
            dpi=DPI,
            facecolor=theme.surface,
        )
        self.ax = self.figure.add_subplot()
        self._layout()
        self._header(title, subtitle)
        self._style_axes()

    def save(
        self, draft_dir: Path, name: str, sources: Iterable[Source], handle: str
    ) -> str:
        if not _CHART_NAME.fullmatch(name):
            raise ValueError(f"invalid chart name: {name!r}")
        used = tuple(source for source in Source if source in set(sources))
        self.figure.text(
            self._x(MARGIN_PX),
            self._y(CREDIT_BASELINE_PX),
            credit_line(used, handle),
            color=self.theme.muted,
            fontsize=self._pt(CREDIT_PT),
        )
        relative = f"{CHARTS_DIR}/{name}_{self.preset.value}.png"
        path = draft_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        self.figure.savefig(path, dpi=DPI, facecolor=self.theme.surface)
        return relative

    def _layout(self) -> None:
        self.figure.subplots_adjust(
            left=self._x(MARGIN_PX + TICK_LABEL_PX),
            right=1 - self._x(MARGIN_PX),
            top=1 - self._y(HEADER_PX),
            bottom=self._y(FOOTER_PX),
        )

    def _header(self, title: str, subtitle: str | None) -> None:
        left = self._x(MARGIN_PX)
        self.figure.text(
            left,
            1 - self._y(MARGIN_PX),
            title,
            color=self.theme.text_primary,
            fontsize=self._pt(TITLE_PT),
            fontweight="bold",
            va="top",
        )
        if subtitle:
            self.figure.text(
                left,
                1 - self._y(MARGIN_PX + SUBTITLE_OFFSET_PX),
                subtitle,
                color=self.theme.text_secondary,
                fontsize=self._pt(SUBTITLE_PT),
                va="top",
            )

    def _style_axes(self) -> None:
        ax = self.ax
        ax.set_facecolor(self.theme.surface)
        ax.set_axisbelow(True)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(self.theme.baseline)
        ax.grid(axis="y", color=self.theme.grid, linewidth=0.8)
        ax.tick_params(
            colors=self.theme.muted, labelsize=self._pt(TICK_PT), length=0, pad=6
        )
        ax.xaxis.label.set_color(self.theme.text_secondary)
        ax.yaxis.label.set_color(self.theme.text_secondary)

    def _x(self, px: float) -> float:
        return px * self._scale / self._width

    def _y(self, px: float) -> float:
        return px * self._scale / self._height

    def _pt(self, size: float) -> float:
        return size * self._scale
