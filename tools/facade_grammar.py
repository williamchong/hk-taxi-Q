"""The vision-read façade grammar survey (`Q41`) — per-face grammar from photo texture.

`Q40` proved fin-versus-curtain-versus-punched is unreachable by a per-pixel
statistic; `Q41` claims a vision reader reaches it, and this tool is that
reader. It unwraps each building's elevations (`tools/facade_unwrap.py`), sends
them to a pinned Claude model, and writes a per-face table the pipeline can one
day join by building stem — after, and only after, the validation gate below
has passed.

⚠️ **This is the repo's first non-deterministic input producer, and three
mechanisms answer `Q37`'s ghost** ("a table nobody can re-derive"):

- **Every raw API response is cached** beside the output table, keyed by model
  and prompt hash. A rerun replays the cache byte-for-byte; only a deliberate
  prompt or model change re-spends a call.
- **Every output row records `model` and `prompt_hash`.** A row's provenance is
  in the row, not in anyone's memory.
- **Re-derivation acceptance is the `Q41` thresholds passing again**, not
  byte-equality — `Q37`'s own move of making survey acceptance a tolerance.

⚠️ **The model is pinned and a model change is a resurvey.** The validation run
validates *this* reader; swapping the model silently would carry the old run's
authority onto an unmeasured reader.

⚠️ **Every gate refuses rather than guesses** (`Q40`'s contract): a face the
unwrap cannot produce, or the reader declines, yields a refusal row, and a
refusal falls back to the existing hash exactly as `facade_hue` already does
for an unmeasured building.

Run:  .venv/bin/python tools/facade_grammar.py --validate
      .venv/bin/python tools/facade_grammar.py 11-SW-9D
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import sys
import zipfile
from base64 import standard_b64encode
from hashlib import blake2b
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(ROOT / "tools"))

from facade_unwrap import Elevation, load_building, sheet_documents, unwrap_building  # noqa: E402
from pipeline.buildings import stem  # noqa: E402
from pipeline.fetch import SOURCES_ROOT, source_dir  # noqa: E402

log = logging.getLogger(__name__)

# Where the table and the raw-response cache live: the same uncommitted source
# cache facade_lab.json uses, because both are derived government data (hard
# rule 7) that the committed tool re-derives.
SURVEY_SOURCE_ID = "facade_grammar"

# Pinned. `Q41` records that changing this is a resurvey, not a settings tweak.
MODEL = "claude-opus-5"

# Larger elevations are downscaled so the long edge fits the model's native
# resolution; at 8 texels/m even a halved image keeps a 2.4 m bay legible.
MAX_EDGE_PX = 2048

# Below this the canvas is nearly empty and there is nothing to send. Every
# validation face sits well above it; the gate exists for degenerate slivers.
MIN_COVERAGE = 0.05

LABELS = ROOT / "tools" / "facade_grammar_labels.json"

PROMPT = """\
You are reading one unwrapped façade elevation of a Hong Kong building, \
re-projected from aerial photogrammetry into a true-scale grid (metres across \
x metres up). Artefact guide: pure black = no photographic data; large flat \
grey = untextured filler or an occluded wall, not architecture; glass carries \
reflections of sky, streets and neighbouring buildings — reflections on a \
regular pane grid are evidence OF glazing, not noise; trees or vehicles may be \
baked into wall texels as photographed occluders; blur means the wall was far \
from the camera.

Classify the dominant façade treatment:
- "curtain": predominantly glazed — mirror or ribbon curtain wall, pane grids, \
glazing bands with spandrels.
- "punched": openings (windows, balconies, verandas) cut into a dominant solid \
wall — tenements, public housing, concrete frames.
- "fin": continuous vertical piers or fins dominate, with glazing recessed \
between them and little horizontal expression.
- "blank": a solid wall with no meaningful fenestration (party walls, service \
walls, decorative feature walls).
- "mixed": two or more of the above each covering a substantial share.

Set "readable" to false — and "grammar" to null — when the image does not \
carry enough legible façade to classify: slivers, filler-dominated faces, \
smears, scattered fragments. Refusing is the correct answer for such faces; \
never guess a grammar from a hint. Set "confidence" to "low" whenever a \
reasonable reader could disagree. "glazed" is whether glazing dominates the \
façade area; "tint" is the glass colour family only when glass is present and \
its own colour (not a reflection) is discernible, else null. "signage" is any \
legible sign text or a short description of a distinctive sign, else null.

The remaining fields feed a renderer and are null whenever you cannot count \
or see them directly — never estimate from building size: "storey_count" is \
the number of visible floors on this face; "band_period_floors" is the period, \
in floors, of any heavier recurring horizontal band (structural or mechanical \
floors), null if none repeats; "podium_floors" is how many lowest floors form \
a visibly distinct podium (shopfronts, different treatment), null if none; \
"podium_glazed" is whether that podium is predominantly shopfront glazing; \
"balconies" is whether open or recessed balconies are part of the façade; \
"emphasis" is the dominant reading direction of the façade pattern — \
"horizontal" (ribbons, bands), "vertical" (piers, fins), "grid" (both \
equally), or "none". Keep "notes" to one sentence."""

SCHEMA = {
    "type": "object",
    "properties": {
        "readable": {"type": "boolean"},
        "confidence": {"type": "string", "enum": ["high", "low"]},
        "grammar": {
            "anyOf": [
                {"type": "string", "enum": ["curtain", "punched", "fin", "blank", "mixed"]},
                {"type": "null"},
            ]
        },
        "glazed": {"anyOf": [{"type": "boolean"}, {"type": "null"}]},
        "tint": {
            "anyOf": [
                {"type": "string", "enum": ["neutral", "blue", "green", "bronze"]},
                {"type": "null"},
            ]
        },
        "signage": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "storey_count": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "band_period_floors": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "podium_floors": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "podium_glazed": {"anyOf": [{"type": "boolean"}, {"type": "null"}]},
        "balconies": {"anyOf": [{"type": "boolean"}, {"type": "null"}]},
        "emphasis": {
            "anyOf": [
                {"type": "string", "enum": ["horizontal", "vertical", "grid", "none"]},
                {"type": "null"},
            ]
        },
        "notes": {"type": "string"},
    },
    "required": [
        "readable",
        "confidence",
        "grammar",
        "glazed",
        "tint",
        "signage",
        "storey_count",
        "band_period_floors",
        "podium_floors",
        "podium_glazed",
        "balconies",
        "emphasis",
        "notes",
    ],
    "additionalProperties": False,
}

# The provenance stamp every row and cache entry carries. Prompt, schema and
# model are hashed together: a change to any of them is a different reader.
PROMPT_HASH = blake2b(
    (PROMPT + json.dumps(SCHEMA, sort_keys=True) + MODEL).encode(), digest_size=8
).hexdigest()


def encode_elevation(elevation: Elevation) -> bytes:
    """The elevation as PNG bytes, long edge capped at `MAX_EDGE_PX`."""
    image = Image.fromarray(elevation.canvas)
    longest = max(image.size)
    if longest > MAX_EDGE_PX:
        scale = MAX_EDGE_PX / longest
        image = image.resize(
            (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
            Image.LANCZOS,
        )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def read_face(client, png: bytes) -> dict:
    """One structured read. The schema is enforced at the API layer, so the
    text that comes back parses or the SDK has already retried."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=16000,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": standard_b64encode(png).decode(),
                        },
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    if response.stop_reason == "refusal":
        # A classifier decline is a refusal row, not an error — the same
        # fallback contract as every other gate.
        return refusal_row("api refusal")
    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)


def cached_read(client, cache_dir: Path, key: str, elevation: Elevation) -> dict:
    """The raw-response cache. A hit costs nothing and reproduces exactly."""
    path = cache_dir / f"{key}.{PROMPT_HASH}.json"
    if path.exists():
        return json.loads(path.read_text())
    result = read_face(client, encode_elevation(elevation))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=1, sort_keys=True))
    return result


def refusal_row(reason: str) -> dict:
    row = dict.fromkeys(SCHEMA["required"])
    row.update(readable=False, confidence="low", notes=reason)
    return row


def make_client():
    """The SDK client, or a gate message when no credential resolves."""
    try:
        import anthropic
    except ImportError:
        raise SystemExit(
            "the `anthropic` package is not installed — .venv/bin/pip install anthropic"
        ) from None
    return anthropic.Anthropic()


def survey_sheet(sheet: str, city: str, zip_dir: Path) -> dict[str, dict]:
    """Every face of every building on one sheet, keyed by the pipeline's stem."""
    client = make_client()
    cache_dir = source_dir(city, SURVEY_SOURCE_ID) / "raw" / sheet
    rows: dict[str, dict] = {}
    with zipfile.ZipFile(zip_dir / f"{sheet}.zip") as bundle:
        documents = sheet_documents(bundle)
        for index, (name, entry) in enumerate(sorted(documents.items()), 1):
            faces = unwrap_building(load_building(bundle, entry))
            row: dict[str, dict] = {}
            for face, elevation in faces.items():
                if elevation.coverage < MIN_COVERAGE:
                    row[face] = refusal_row("coverage below gate")
                    continue
                row[face] = cached_read(client, cache_dir, f"{name}_{face}", elevation)
            rows[stem(name)] = {
                "faces": row,
                "model": MODEL,
                "prompt_hash": PROMPT_HASH,
                "sheet": sheet,
            }
            log.info(
                "[%d/%d] %s: %s",
                index,
                len(documents),
                name,
                {f: (r["grammar"] or "refused") for f, r in row.items()},
            )
    return rows


def agrees(label: dict, result: dict) -> bool:
    """Grammar agreement: the label, or its recorded `alt_grammar`, counts."""
    accepted = {label["grammar"], label["alt_grammar"]} - {None}
    return result["readable"] and result["grammar"] in accepted


def is_miss(label: dict, result: dict) -> bool:
    """One face's verdict under its pool's rule, as `Q41` states them."""
    if label["readable"] and not label["refusal_ok"]:
        return not agrees(label, result)
    if label["readable"]:
        return result["readable"] and result["confidence"] == "high" and not agrees(label, result)
    return result["readable"] and result["confidence"] == "high"


def score(results: list[tuple[dict, dict]]) -> list[tuple[str, int, int, float]]:
    """The four `Q41` checks over (label, reader) pairs: name, hits, total, bar."""
    strict = [(la, re) for la, re in results if la["readable"] and not la["refusal_ok"]]
    marginal = [(la, re) for la, re in results if la["readable"] and la["refusal_ok"]]
    refusal = [(la, re) for la, re in results if not la["readable"]]
    glazed_pairs = [
        (la, re)
        for la, re in results
        if la["glazed"] is not None and re["readable"] and re["glazed"] is not None
    ]
    return [
        ("strict grammar", sum(not is_miss(la, re) for la, re in strict), len(strict), 16 / 20),
        ("marginal", sum(not is_miss(la, re) for la, re in marginal), len(marginal), 5 / 6),
        ("refusal", sum(not is_miss(la, re) for la, re in refusal), len(refusal), 13 / 14),
        (
            "glazed",
            sum(la["glazed"] == re["glazed"] for la, re in glazed_pairs),
            len(glazed_pairs),
            0.9,
        ),
    ]


def validate(city: str, zip_dir: Path) -> int:
    """Run the reader over the labelled 40 faces and grade it against the
    thresholds `Q41` fixed in advance. The exit code is the verdict."""
    client = make_client()
    labels = json.loads(LABELS.read_text())["faces"]
    cache_dir = source_dir(city, SURVEY_SOURCE_ID) / "raw" / "validation"

    results = []
    by_sheet: dict[str, list[dict]] = {}
    for label in labels:
        by_sheet.setdefault(label["sheet"], []).append(label)
    for sheet, sheet_labels in by_sheet.items():
        with zipfile.ZipFile(zip_dir / f"{sheet}.zip") as bundle:
            documents = sheet_documents(bundle)
            unwrapped: dict[str, dict] = {}
            for label in sheet_labels:
                name = label["building"]
                if name not in unwrapped:
                    unwrapped[name] = unwrap_building(load_building(bundle, documents[name]))
                elevation = unwrapped[name].get(label["face"])
                if elevation is None:
                    results.append((label, refusal_row("unwrap refused")))
                    continue
                key = f"{sheet}_{name}_{label['face']}"
                result = cached_read(client, cache_dir, key, elevation)
                results.append((label, result))
                log.info(
                    "%s %s: reader=%s/%s conf=%s | label=%s%s",
                    name,
                    label["face"],
                    "ok" if result["readable"] else "refuse",
                    result["grammar"],
                    result["confidence"],
                    "refuse" if not label["readable"] else label["grammar"],
                    " (refusal ok)" if label["refusal_ok"] else "",
                )

    passed = True
    for label_text, hits, total, threshold in score(results):
        ok = total == 0 or hits / total >= threshold
        passed &= ok
        log.info(
            "%-16s %2d/%2d  (needs %.0f%%)  %s",
            label_text,
            hits,
            total,
            threshold * 100,
            "PASS" if ok else "FAIL",
        )
    for la, re in results:
        if is_miss(la, re):
            log.info(
                "MISS %s %s %s: reader %s/%s (%s) vs label %s — %s",
                la["sheet"],
                la["building"],
                la["face"],
                "ok" if re["readable"] else "refuse",
                re["grammar"],
                re["confidence"],
                la["grammar"] or "refuse",
                re["notes"],
            )
    log.info("verdict: %s (model %s, prompt %s)", "PASS" if passed else "FAIL", MODEL, PROMPT_HASH)
    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sheets", nargs="*", help="sheet ids to survey, e.g. 11-SW-9D")
    parser.add_argument("--validate", action="store_true", help="grade the Q41 validation set")
    parser.add_argument("--city", default="hong_kong")
    parser.add_argument(
        "--zip-dir",
        type=Path,
        default=SOURCES_ROOT / "individualised",
        help="where the individualised sheet archives live",
    )
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if arguments.validate:
        return validate(arguments.city, arguments.zip_dir)
    if not arguments.sheets:
        parser.error("name at least one sheet, or pass --validate")
    out_dir = source_dir(arguments.city, SURVEY_SOURCE_ID)
    out_dir.mkdir(parents=True, exist_ok=True)
    for sheet in arguments.sheets:
        rows = survey_sheet(sheet, arguments.city, arguments.zip_dir)
        destination = out_dir / f"facade_grammar.{sheet}.json"
        destination.write_text(json.dumps(rows, indent=1, sort_keys=True))
        log.info("%s: %d buildings -> %s", sheet, len(rows), destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
