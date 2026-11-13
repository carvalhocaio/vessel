import json
from pathlib import Path

from typer.testing import CliRunner

from vessel import __version__
from vessel.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_schema_prints_draft_contract() -> None:
    result = runner.invoke(app, ["schema"])

    assert result.exit_code == 0
    schema = json.loads(result.stdout)
    assert schema["title"] == "Draft"
    assert "facts" in schema["required"]


def test_schema_writes_to_file(tmp_path: Path) -> None:
    target = tmp_path / "draft.schema.json"

    result = runner.invoke(app, ["schema", "--output", str(target)])

    assert result.exit_code == 0
    assert json.loads(target.read_text(encoding="utf-8"))["title"] == "Draft"
