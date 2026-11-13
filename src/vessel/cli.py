import json
from pathlib import Path
from typing import Annotated

import typer

from vessel import __version__
from vessel.config import get_settings
from vessel.domain import Draft

app = typer.Typer(no_args_is_help=True, help="Data pipeline for the F1 profile.")


@app.command()
def version() -> None:
    typer.echo(f"vessel {__version__}")


@app.command()
def doctor() -> None:
    settings = get_settings()
    settings.ensure_dirs()
    typer.echo(f"handle:   @{settings.handle}")
    typer.echo(f"timezone: {settings.timezone}")
    typer.echo(f"data dir: {settings.data_dir.resolve()}")
    status = "ok" if settings.calendars.f1 else "missing"
    typer.echo(f"ical f1:  {status}")


@app.command()
def schema(
    output: Annotated[
        Path | None, typer.Option(help="Write the JSON Schema to a file.")
    ] = None,
) -> None:
    document = json.dumps(Draft.model_json_schema(), indent=2, ensure_ascii=False)
    if output is None:
        typer.echo(document)
        return
    output.write_text(document + "\n", encoding="utf-8")
    typer.echo(f"draft schema written to {output}")
