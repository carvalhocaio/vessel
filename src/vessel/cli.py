import typer

from vessel import __version__
from vessel.config import get_settings

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
