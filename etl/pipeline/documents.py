"""Reading and writing the JSON documents the stages pass between them.

Format only, no policy — the same split `gltf.py` has against `buildings.py`.
What a document *means* belongs to the stage that owns it; what every document
shares is that it carries a `schema_version`, that its positions are rounded the
same way, and that it is serialised with the same three settings.

Its own module rather than a corner of one stage's, because the consumers run in
both directions: `buildings.py` writes one before `roads.py` exists in the run,
and `export.py` reads all four. Anything living inside a stage would have made
the earlier stages import a later one.

The counterpart on the game side is `game/scripts/city/generated_document.gd`,
which does the same version check and pushes a message rather than raising —
a missing file there is a dev scene with nothing to draw, not a broken build.
"""

from __future__ import annotations

import json
from pathlib import Path


def read_document(path: Path, schema_version: int, rebuild: str) -> dict:
    """A stage's JSON output, refusing a schema the reader was not written for.

    Every stage that reads a document has to decide what to do about its
    version. Doing that in one place means the answer is the same everywhere:
    refuse, and say which command rebuilds the file. A stale document that
    parses is the failure this exists to stop — it produces plausible output
    from the wrong data.

    `rebuild` is the command to run, not a description of it, so the message can
    be copied straight into a shell. A hint that exits on a missing argument is
    a second puzzle to solve while already stuck on the first.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as missing:
        raise FileNotFoundError(f"{path} does not exist. Run `{rebuild}` first.") from missing

    document = json.loads(text)
    version = document.get("schema_version")
    if version != schema_version:
        raise ValueError(
            f"{path} declares schema_version {version!r}, this stage reads {schema_version}. "
            f"Re-run `{rebuild}`."
        )
    return document


def write_document(path: Path, document: dict) -> int:
    """A stage's JSON output, written the one way, and its size.

    Shared for a smaller reason than `read_document`, but the settings matter.
    `ensure_ascii=False` is what keeps the bilingual road and fare names
    readable rather than `\\u8ed2\\u5c3c`, and the trailing newline is what
    stops a diff of two builds ending in `\\ No newline at end of file`. Both
    were inconsistent across the four stages that write one.

    Returns the byte count, because every caller reports it.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path.stat().st_size


def round_position(point: tuple[float, float, float]) -> list[float]:
    """A position at millimetre precision, without a negative zero.

    A vertex clipped to the region's western edge lands on -0.0, which is a
    legal JSON number and a confusing thing to read in a file whose whole point
    is that the region starts at zero. Adding 0.0 collapses it: IEEE 754 makes
    -0.0 + 0.0 exactly +0.0, and leaves every other value alone.

    Here rather than in a stage because every stage writing a position into the
    data contract needs the same treatment, and the reason is subtle enough that
    a second copy would eventually lose it.
    """
    return [round(value, 3) + 0.0 for value in point]
