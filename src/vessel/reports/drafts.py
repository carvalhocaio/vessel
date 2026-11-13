import os
from collections.abc import Callable
from pathlib import Path

from vessel.domain import Draft, Event, Segment

DRAFT_FILE = "draft.json"
PENDING_FILE = "draft.pending.json"
REJECTED_FILE = "draft.rejected.json"


class DraftVerificationError(RuntimeError):
    def __init__(self, path: Path, failures: tuple[str, ...]) -> None:
        super().__init__(
            f"draft rejected ({path}): {len(failures)} divergence(s): "
            + "; ".join(failures)
        )
        self.path = path
        self.failures = failures


Verifier = Callable[[Draft, Path], tuple[str, ...]]


def draft_dir(out_dir: Path, event: Event, segment: Segment) -> Path:
    return out_dir / str(event.season) / event.slug / segment.value


def publish_draft(draft: Draft, directory: Path, verify: Verifier) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    pending = directory / PENDING_FILE
    pending.write_text(draft.model_dump_json(indent=2) + "\n", encoding="utf-8")
    saved = Draft.model_validate_json(pending.read_text(encoding="utf-8"))
    failures = verify(saved, directory)
    final, rejected = directory / DRAFT_FILE, directory / REJECTED_FILE
    if failures:
        os.replace(pending, rejected)
        final.unlink(missing_ok=True)
        raise DraftVerificationError(rejected, failures)
    os.replace(pending, final)
    rejected.unlink(missing_ok=True)
    return final
