"""The vision-read façade grammar survey (`Q41`) — per-face grammar from photo texture.

`Q40` proved fin-versus-curtain-versus-punched is unreachable by a per-pixel
statistic; `Q41` claims a vision reader reaches it, and this tool is that
reader. It unwraps each building's elevations (`tools/facade_unwrap.py`), sends
them to a pinned Claude model, and writes a per-face table the pipeline can one
day join by building stem — after, and only after, the validation gate below
has passed.

⚠️ **This is the repo's first non-deterministic input producer, and three
mechanisms answer `Q37`'s ghost** ("a table nobody can re-derive"):

- **Every raw API response is cached** beside the output table, keyed by
  model, prompt hash **and the fingerprint of the encoded image it answered**.
  A rerun replays the cache byte-for-byte; a prompt, model or unwrap change
  re-spends only the calls it actually invalidates.
- **Every output row records `model`, `prompt_hash` and `image_hash`.** A
  row's provenance — including the image it was read from — is in the row, not
  in anyone's memory.
- **Re-derivation acceptance is the `Q41` thresholds passing again**, not
  byte-equality — `Q37`'s own move of making survey acceptance a tolerance.

⚠️ **The model is pinned and a model change is a resurvey.** The validation run
validates *this* reader; swapping the model silently would carry the old run's
authority onto an unmeasured reader.

⚠️ **Every gate refuses rather than guesses** (`Q40`'s contract): a face the
reader declines yields a refusal row, and a face the unwrap cannot produce is
simply absent from its building's table — a consumer reads both as the same
thing, the fall-back to the existing hash that `facade_hue` already performs
for an unmeasured building.

Run:  .venv/bin/python tools/facade_grammar.py --validate
      .venv/bin/python tools/facade_grammar.py 11-SW-9D
"""

from __future__ import annotations

import argparse
import inspect
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

from facade_survey import INDIVIDUALISED_DIR, load_building, sheet_documents  # noqa: E402
from facade_unwrap import Elevation, unwrap_building  # noqa: E402
from pipeline.buildings import stem  # noqa: E402
from pipeline.fetch import source_dir  # noqa: E402

log = logging.getLogger(__name__)

# Where the table and the raw-response cache live: the same uncommitted source
# cache facade_lab.json uses, because both are derived government data (hard
# rule 7) that the committed tool re-derives.
SURVEY_SOURCE_ID = "facade_grammar"

# Pinned. `Q41` records that changing this is a resurvey, not a settings tweak —
# exercised once: Sonnet 5 passed the same graded gate (strict 18/20, marginal
# 6/6, refusal 14/14, glazed 24/24) at two-fifths of Opus's price.
MODEL = "claude-sonnet-5"

# Larger elevations are downscaled so the long edge fits the model's native
# resolution; at 8 texels/m even a halved image keeps a 2.4 m bay legible.
MAX_EDGE_PX = 2048

# Below this the canvas is nearly empty and there is nothing to send. Every
# validation face sits well above it; the gate exists for degenerate slivers.
MIN_COVERAGE = 0.05

LABELS = ROOT / "tools" / "facade_grammar_labels.json"

# The taxonomy, defined once. The SCHEMA enum is built from it, the labels file
# is tested against it, and a typo'd label can no longer silently score a miss.
GRAMMARS: tuple[str, ...] = ("curtain", "punched", "fin", "blank", "mixed")

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
                {"type": "string", "enum": list(GRAMMARS)},
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


# The per-building row cache skips the unwrap itself, so the image fingerprint
# in each response entry's key never gets a chance to guard a row hit. The row
# key therefore hashes the code the images actually pass through: the unwrap
# and the wall survey it reads, the glTF parser and texture decoder under
# both, and this file's encoder with the two knobs that shape a row. Any edit
# invalidates every row, which costs file reads and rasterising but **no API
# spend**: regenerating a row re-derives each face's fingerprint against the
# response cache, so a no-op refactor replays every paid entry free.
# Deliberately *not* the whole of this file — a log-message tweak should not
# re-rasterise a sheet, and a prompt change already renames the row via
# `PROMPT_HASH`. Folding any of this into PROMPT_HASH would instead discard
# the paid entries themselves — `Q41` records that as the wrong shape, because
# it keys on source rather than on the image it produces.
UNWRAP_HASH = blake2b(
    b"".join(
        path.read_bytes()
        for path in (
            ROOT / "tools" / "facade_survey.py",
            ROOT / "tools" / "facade_unwrap.py",
            ROOT / "etl" / "pipeline" / "gltf.py",
            ROOT / "etl" / "pipeline" / "buildings.py",
        )
    )
    + inspect.getsource(encode_elevation).encode()
    + f"{MAX_EDGE_PX} {MIN_COVERAGE}".encode(),
    digest_size=8,
).hexdigest()


def request_params(png: bytes) -> dict:
    """The complete request, built in one place so the synchronous path and
    the batch path cannot drift: whichever transport carries it, the read the
    API performs is the one `PROMPT_HASH` names."""
    return {
        "model": MODEL,
        "max_tokens": 16000,
        "messages": [
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
        "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
    }


def parse_message(message) -> dict:
    """One response into one cache entry, for either transport. The schema is
    enforced at the API layer, so the text parses or the SDK has retried."""
    if message.stop_reason == "refusal":
        # A classifier decline is a refusal row, not an error — the same
        # fallback contract as every other gate.
        return refusal_row("api refusal")
    text = next((block.text for block in message.content if block.type == "text"), None)
    if text is None:
        raise RuntimeError(f"response carried no text block (stop_reason={message.stop_reason})")
    return json.loads(text)


def read_face(client, png: bytes) -> dict:
    """One structured read over the synchronous API."""
    return parse_message(client.messages.create(**request_params(png)))


def cached_read(get_client, cache_dir: Path, key: str, elevation: Elevation) -> dict:
    """The raw-response cache. A hit costs an encode and reproduces exactly —
    including needing neither the SDK nor a credential, which is why the
    client arrives as a factory and is only called on a miss.

    The image is in the key: an entry answers one prompt about one encoded
    PNG, so an unwrap change makes a stale entry unfindable rather than
    silently replayed — `Q37`'s ghost, entering through the one input
    `PROMPT_HASH` cannot see. Superseded entries are kept: they are the raw
    record of a paid read, and an unwrap change that is later reverted hits
    them again for free."""
    png = encode_elevation(elevation)
    fingerprint = blake2b(png, digest_size=8).hexdigest()
    path = cache_dir / f"{key}.{PROMPT_HASH}.{fingerprint}.json"
    try:
        result = json.loads(path.read_text())
    except FileNotFoundError:
        if any(cache_dir.glob(f"{key}.{PROMPT_HASH}.*.json")):
            log.warning("%s: cached answers exist, but none for this image — re-reading", key)
        result = read_face(get_client(), png)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=1, sort_keys=True))
    return {**result, "image_hash": fingerprint}


def refusal_row(reason: str) -> dict:
    # `image_hash` is None honestly: a refusal minted here never encoded an
    # image, unlike an API refusal, which `cached_read` stamps like any read.
    row = dict.fromkeys(SCHEMA["required"])
    row.update(readable=False, confidence="low", notes=reason, image_hash=None)
    return row


def client_factory():
    """A memoised SDK client — constructed on first use, or a gate message
    when the package or a credential is missing."""
    state: dict = {}

    def get():
        if "client" not in state:
            try:
                import anthropic
            except ImportError:
                raise SystemExit(
                    "the `anthropic` package is not installed — .venv/bin/pip install anthropic"
                ) from None
            state["client"] = anthropic.Anthropic()
        return state["client"]

    return get


# --- Batch transport --------------------------------------------------------
# The Batch API halves the price of a read and changes nothing else: a
# submitted request carries `request_params` verbatim, so the read the API
# performs is still the one `PROMPT_HASH` names, and collection writes the
# same content-addressed entries `cached_read` would have written. The output
# tables are then authored by the ordinary survey path replaying that cache —
# the batch layer is transport, never interpretation.

# Comfortably under the API's 256 MB per-batch cap; a sheet that encodes
# larger is split, since results are keyed per face and never per batch.
MAX_BATCH_BYTES = 120 * 1024 * 1024


def batch_entry(key: str, png: bytes) -> dict:
    """One batch request. A custom_id may not contain dots, so the cache
    path's pieces ride around a dash: `{key}-{fingerprint}`."""
    fingerprint = blake2b(png, digest_size=8).hexdigest()
    return {"custom_id": f"{key}-{fingerprint}", "params": request_params(png)}


def entry_path(cache_dir: Path, custom_id: str) -> Path:
    """The cache entry a batch result lands in — `cached_read`'s key exactly,
    so a collected face replays for free in every later run."""
    key, _, fingerprint = custom_id.rpartition("-")
    return cache_dir / f"{key}.{PROMPT_HASH}.{fingerprint}.json"


def batch_submit(sheets: list[str], city: str, zip_dir: Path) -> int:
    """Enumerate every un-cached face of the named sheets and submit them to
    the Batch API. Batch ids land in a state file beside the caches; nothing
    else is written until `--batch-collect`."""
    client = client_factory()()
    out_root = source_dir(city, SURVEY_SOURCE_ID) / "raw"
    state_path = out_root / f"batch.{PROMPT_HASH}.json"
    try:
        state = json.loads(state_path.read_text())
    except FileNotFoundError:
        state = {"model": MODEL, "prompt_hash": PROMPT_HASH, "batches": []}

    def flush(sheet: str, pending: list[dict]) -> None:
        batch = client.messages.batches.create(requests=pending)
        state["batches"].append({"id": batch.id, "sheet": sheet, "count": len(pending)})
        out_root.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=1))
        log.info("%s: submitted %d faces as %s", sheet, len(pending), batch.id)

    for sheet in sheets:
        cache_dir = out_root / sheet
        pending: list[dict] = []
        pending_bytes = 0
        cached = gated = submitted = 0
        with zipfile.ZipFile(zip_dir / f"{sheet}.zip") as bundle:
            for name, entry in sorted(sheet_documents(bundle).items()):
                for face, elevation in unwrap_building(load_building(bundle, entry)).items():
                    if elevation.coverage < MIN_COVERAGE:
                        gated += 1
                        continue
                    request = batch_entry(f"{name}_{face}", encode_elevation(elevation))
                    if entry_path(cache_dir, request["custom_id"]).exists():
                        cached += 1
                        continue
                    pending.append(request)
                    pending_bytes += len(
                        request["params"]["messages"][0]["content"][0]["source"]["data"]
                    )
                    submitted += 1
                    if pending_bytes > MAX_BATCH_BYTES:
                        flush(sheet, pending)
                        pending, pending_bytes = [], 0
        if pending:
            flush(sheet, pending)
        log.info(
            "%s: %d submitted, %d already cached, %d below gate", sheet, submitted, cached, gated
        )
    return 0


def batch_collect(city: str) -> int:
    """Write every ended batch's results into the response cache. Exit 0 once
    all batches are collected, 1 while any is still processing — an errored or
    expired face is left a cache miss, so any later run reads it again."""
    client = client_factory()()
    out_root = source_dir(city, SURVEY_SOURCE_ID) / "raw"
    state_path = out_root / f"batch.{PROMPT_HASH}.json"
    try:
        state = json.loads(state_path.read_text())
    except FileNotFoundError:
        raise SystemExit(
            f"no submission recorded for prompt {PROMPT_HASH} — run --batch-submit"
        ) from None

    still_open = 0
    for record in state["batches"]:
        if record.get("collected"):
            continue
        batch = client.messages.batches.retrieve(record["id"])
        if batch.processing_status != "ended":
            log.info("%s (%s): %s", record["id"], record["sheet"], batch.processing_status)
            still_open += 1
            continue
        cache_dir = out_root / record["sheet"]
        counts = {"succeeded": 0, "refused": 0, "errored": 0}
        for result in client.messages.batches.results(record["id"]):
            if result.result.type != "succeeded":
                counts["errored"] += 1
                log.warning(
                    "%s: %s — left uncached for a later read", result.custom_id, result.result.type
                )
                continue
            row = parse_message(result.result.message)
            counts["refused" if row.get("notes") == "api refusal" else "succeeded"] += 1
            path = entry_path(cache_dir, result.custom_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(row, indent=1, sort_keys=True))
        record["collected"] = counts
        state_path.write_text(json.dumps(state, indent=1))
        log.info("%s (%s): %s", record["id"], record["sheet"], counts)
    if still_open:
        log.info("%d batch(es) still processing", still_open)
    else:
        log.info("all batches collected")
    return 1 if still_open else 0


def survey_sheet(sheet: str, city: str, zip_dir: Path) -> dict[str, dict]:
    """Every face of every building on one sheet, keyed by the pipeline's stem.

    Beside the per-face response cache sits a per-building row cache, written
    only once every face of the building is settled: a rerun that regenerates
    the table skips the unwrap itself, not just the API spend, so re-emitting
    a 651-building sheet costs file reads rather than minutes of rasterising.
    Because it skips the unwrap, its key carries `UNWRAP_HASH` — a row is only
    replayed while the code its images came from is the code on disk.
    """
    get_client = client_factory()
    cache_dir = source_dir(city, SURVEY_SOURCE_ID) / "raw" / sheet
    rows: dict[str, dict] = {}
    with zipfile.ZipFile(zip_dir / f"{sheet}.zip") as bundle:
        documents = sheet_documents(bundle)
        for index, (name, entry) in enumerate(sorted(documents.items()), 1):
            row_path = cache_dir / f"{name}.row.{PROMPT_HASH}.{UNWRAP_HASH}.json"
            try:
                row = json.loads(row_path.read_text())
            except FileNotFoundError:
                faces = unwrap_building(load_building(bundle, entry))
                row = {}
                for face, elevation in faces.items():
                    if elevation.coverage < MIN_COVERAGE:
                        row[face] = refusal_row("coverage below gate")
                        continue
                    row[face] = cached_read(get_client, cache_dir, f"{name}_{face}", elevation)
                row_path.parent.mkdir(parents=True, exist_ok=True)
                row_path.write_text(json.dumps(row, indent=1, sort_keys=True))
            rows[stem(name)] = {
                "faces": row,
                "model": MODEL,
                "prompt_hash": PROMPT_HASH,
                "unwrap_hash": UNWRAP_HASH,
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
    get_client = client_factory()
    labels = json.loads(LABELS.read_text())["faces"]

    results = []
    by_sheet: dict[str, list[dict]] = {}
    for label in labels:
        by_sheet.setdefault(label["sheet"], []).append(label)
    for sheet, sheet_labels in by_sheet.items():
        # The same cache namespace the sheet survey uses, deliberately: a
        # validation face's response is byte-identical to the survey's read of
        # that face, so the validation spend seeds the later full-sheet run.
        cache_dir = source_dir(city, SURVEY_SOURCE_ID) / "raw" / sheet
        by_building: dict[str, list[dict]] = {}
        for label in sheet_labels:
            by_building.setdefault(label["building"], []).append(label)
        with zipfile.ZipFile(zip_dir / f"{sheet}.zip") as bundle:
            documents = sheet_documents(bundle)
            for name, building_labels in by_building.items():
                if name not in documents:
                    raise SystemExit(f"labels name {name}, which is not on sheet {sheet}")
                faces = unwrap_building(
                    load_building(bundle, documents[name]),
                    faces=[label["face"] for label in building_labels],
                )
                for label in building_labels:
                    elevation = faces.get(label["face"])
                    if elevation is None:
                        result = refusal_row("unwrap refused")
                    else:
                        result = cached_read(
                            get_client, cache_dir, f"{name}_{label['face']}", elevation
                        )
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
        elif (
            la["glazed"] is not None
            and re["readable"]
            and re["glazed"] is not None
            and la["glazed"] != re["glazed"]
        ):
            # Not a miss, but it counts against the glazed axis — without this
            # line a failing glazed check would print no culprits at all.
            log.info(
                "GLAZED %s %s %s: reader %s vs label %s",
                la["sheet"],
                la["building"],
                la["face"],
                re["glazed"],
                la["glazed"],
            )
    log.info("verdict: %s (model %s, prompt %s)", "PASS" if passed else "FAIL", MODEL, PROMPT_HASH)
    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("sheets", nargs="*", help="sheet ids to survey, e.g. 11-SW-9D")
    parser.add_argument("--validate", action="store_true", help="grade the Q41 validation set")
    parser.add_argument(
        "--batch-submit",
        action="store_true",
        help="submit the sheets' un-cached faces to the Batch API at half price",
    )
    parser.add_argument(
        "--batch-collect",
        action="store_true",
        help="write ended batches into the response cache (exit 1 while any is processing)",
    )
    parser.add_argument("--city", default="hong_kong")
    parser.add_argument(
        "--zip-dir",
        type=Path,
        default=INDIVIDUALISED_DIR,
        help="where the individualised sheet archives live",
    )
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if arguments.validate:
        return validate(arguments.city, arguments.zip_dir)
    if arguments.batch_collect:
        return batch_collect(arguments.city)
    if arguments.batch_submit:
        if not arguments.sheets:
            parser.error("--batch-submit needs sheet ids")
        return batch_submit(arguments.sheets, arguments.city, arguments.zip_dir)
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
