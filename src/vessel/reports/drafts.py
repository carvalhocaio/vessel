from pathlib import Path

from vessel.domain import Draft, Event, Segment

DRAFT_FILE = "draft.json"


def draft_dir(out_dir: Path, event: Event, segment: Segment) -> Path:
    return out_dir / str(event.season) / event.slug / segment.value


def write_draft(draft: Draft, directory: Path) -> Path:
    path = directory / DRAFT_FILE
    path.write_text(draft.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path
