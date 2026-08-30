"""Every character the street plate can be asked to draw, against the font that draws it (`P3-24`).

A **check**, not a grader. There is no judgment in it and no bar to tune: a
character in a published street name is either in the font, or in the display
substitution table, or the plate renders a tofu box in front of the player. It
exits non-zero on the third.

**Why this exists as a tool rather than as a fact someone once measured.** The
region needs **166** distinct CJK characters and Free HK Kai carries 165 of them.
The miss is `啓` (U+5553) in `KAI CHIU ROAD / 啓超道`, two edges in Causeway Bay,
where the font carries `啟` (U+555F) — the *same character* in the form Hong
Kong's Education Bureau standardised and the Transport Department did not use.
So the failure is not a gap in the typeface. It is two arms of one government
disagreeing about how to write *kai*, and it surfaces as a broken-looking box on
one street's plate that nobody meets unless they drive down that street.

That is this repository's recurring defect shape — correct everywhere except one
place, and invisible to `check.sh` because `check.sh` grades assets and not
frames (`Q73`). The answer is the same one the rest of the bundle uses: publish
the thing that can see it fail, and fail on it.

⚠️ **The substitution is a DISPLAY decision and the data is untouched.**
`roadgraph.json` keeps `啓超道` exactly as TD published it (`Q54`), and
`game/tuning/street_plate.json` says what to draw instead. A fix applied in the
pipeline would be a rewritten street name, which is the one thing this project
does not do to sourced data.

⚠️ **`fontTools` is deliberately not a dependency.** This reads the `cmap` table
directly — one table, two subtable formats, ~50 lines — rather than putting a
font library on the critical path of an ETL that has no other use for one. The
same argument `pyproject.toml` makes about geopandas and about a glTF library.

⚠️ **City-agnostic, per hard rule 3.** Nothing here knows Hong Kong: the names
come from the region's own `roadgraph.json` and the table from the game's tuning.
A second city brings its own variants and its own row in that table.

Run:  .venv/bin/python tools/font_coverage.py --region wan_chai
"""

from __future__ import annotations

import argparse
import json
import logging
import struct
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "etl"))

from pipeline.config import load_config  # noqa: E402
from pipeline.roads import ROADGRAPH_NAME, read_graph  # noqa: E402

log = logging.getLogger(__name__)

# The plate's own tuning, which names the font and carries the substitutions.
# Read rather than duplicated: this tool and `hud.gd` must agree about both, and
# the way to guarantee that is for there to be one file.
PLATE_TUNING = ROOT / "game" / "tuning" / "street_plate.json"

# `res://` is Godot's project root, which is `game/`.
RES_PREFIX = "res://"


def read_cmap(path: Path) -> set[int]:
    """Every Unicode code point the font maps to a glyph.

    Formats 4 (BMP) and 12 (full range) only. A CJK font that offered neither
    would be unusable in Godot too, so an empty result is a real failure rather
    than a parser limitation to work around.
    """
    data = path.read_bytes()
    (table_count,) = struct.unpack(">H", data[4:6])
    offset: int | None = None
    for index in range(table_count):
        base = 12 + 16 * index
        if data[base : base + 4] == b"cmap":
            (offset,) = struct.unpack(">I", data[base + 8 : base + 12])
            break
    if offset is None:
        raise ValueError(f"{path.name} has no cmap table")

    (subtable_count,) = struct.unpack(">H", data[offset + 2 : offset + 4])
    # Deduplicated: a font commonly points several (platform, encoding) records
    # at one subtable — the shipped face aims both 0/3 and 3/1 at the same
    # format-4 table — and parsing it once per record is pure repetition.
    starts: set[int] = set()
    for index in range(subtable_count):
        record = offset + 4 + 8 * index
        (sub_offset,) = struct.unpack(">I", data[record + 4 : record + 8])
        starts.add(offset + sub_offset)
    codes: set[int] = set()
    for start in starts:
        codes |= _read_subtable(data, start)
    return codes


def _read_subtable(data: bytes, start: int) -> set[int]:
    (fmt,) = struct.unpack(">H", data[start : start + 2])
    if fmt == 4:
        return _read_format4(data, start)
    if fmt == 12:
        return _read_format12(data, start)
    return set()


def _read_format4(data: bytes, start: int) -> set[int]:
    (seg_x2,) = struct.unpack(">H", data[start + 6 : start + 8])
    segments = seg_x2 // 2
    ends = struct.unpack(f">{segments}H", data[start + 14 : start + 14 + seg_x2])
    starts_at = start + 14 + seg_x2 + 2
    starts = struct.unpack(f">{segments}H", data[starts_at : starts_at + seg_x2])
    deltas_at = starts_at + seg_x2
    deltas = struct.unpack(f">{segments}h", data[deltas_at : deltas_at + seg_x2])
    ranges_at = deltas_at + seg_x2
    ranges = struct.unpack(f">{segments}H", data[ranges_at : ranges_at + seg_x2])

    codes: set[int] = set()
    for seg in range(segments):
        first, last = starts[seg], ends[seg]
        if first == 0xFFFF:
            continue
        for code in range(first, last + 1):
            if ranges[seg] == 0:
                glyph = (code + deltas[seg]) & 0xFFFF
            else:
                at = ranges_at + 2 * seg + ranges[seg] + 2 * (code - first)
                if at + 2 > len(data):
                    continue
                (glyph,) = struct.unpack(">H", data[at : at + 2])
                if glyph:
                    glyph = (glyph + deltas[seg]) & 0xFFFF
            if glyph:
                codes.add(code)
    return codes


def _read_format12(data: bytes, start: int) -> set[int]:
    (groups,) = struct.unpack(">I", data[start + 12 : start + 16])
    codes: set[int] = set()
    for index in range(groups):
        at = start + 16 + 12 * index
        first, last, _glyph = struct.unpack(">III", data[at : at + 12])
        codes.update(range(first, last + 1))
    return codes


def street_names(graph: dict) -> list[tuple[str, str]]:
    """The distinct `(en, zh)` pairs the region publishes, names only.

    Takes an already-read document rather than a path, matching
    `carriageway_occupancy.road_names` and `roads.plan_lengths` — so the schema
    check happens once, in `read_graph`, where it belongs.
    """
    pairs: set[tuple[str, str]] = set()
    lopsided = 0
    for edge in graph.get("edges", []):
        names = edge.get("road_name") or {}
        english, chinese = names.get("en"), names.get("zh")
        if isinstance(english, str) and isinstance(chinese, str):
            pairs.add((english, chinese))
        elif isinstance(english, str) or isinstance(chinese, str):
            lopsided += 1
    # ⚠️ Counted rather than skipped in silence. `road_graph.gd` states the
    # invariant that a name is published in both languages or in neither — 0 and
    # 0 over the region's 797 edges — and an edge with only `zh` is exactly the
    # shape an uncovered character could hide behind, since this reads no name
    # it cannot pair.
    if lopsided:
        log.warning("⚠️  %d edge(s) name one language and not the other — not checked", lopsided)
    return sorted(pairs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--region", required=True)
    parser.add_argument("--out-root", type=Path, default=None, help="override the out tree")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    out_dir = city.out_dir(args.region, args.out_root)
    # 🔴 **Through `read_graph`, never `json.loads`.** It is the one place
    # `ROADGRAPH_SCHEMA` is enforced, and it prints the rebuild command. Reading
    # the document directly means a stale or reshaped one yields no `edges`, so
    # this tool reports `streets 0` and exits **0** — "every published street
    # name is drawable", having looked at nothing. That is exactly the inert
    # check this file's own docstring is written against.
    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, args.region)

    tuning = json.loads(PLATE_TUNING.read_text(encoding="utf-8"))
    font_res = tuning.get("font_zh")
    if not isinstance(font_res, str):
        log.error("%s does not name a `font_zh`", PLATE_TUNING.name)
        return 2
    font = ROOT / "game" / font_res.removeprefix(RES_PREFIX)
    substitutions: dict[str, str] = tuning.get("substitutions", {})

    if not font.exists():
        log.error("%s names a font that is not there: %s", PLATE_TUNING.name, font)
        return 2

    codes = read_cmap(font)
    pairs = street_names(graph)

    # Counted over streets rather than over edges: a character is a font problem
    # once, however many edges carry the name.
    needed: Counter[str] = Counter()
    for _english, chinese in pairs:
        for character in chinese:
            needed[character] += 1

    substituted: list[tuple[str, str]] = []
    missing: list[str] = []
    for character in sorted(needed):
        if ord(character) in codes:
            continue
        replacement = substitutions.get(character)
        # No row, or a row whose replacement is itself undrawable — a table that
        # maps one missing glyph to another is a fix that did not happen.
        if replacement is None or any(ord(part) not in codes for part in replacement):
            missing.append(character)
        else:
            substituted.append((character, replacement))

    log.info("font      %s  (%d code points mapped)", font.name, len(codes))
    log.info("region    %s/%s", city.id, args.region)
    log.info("streets   %d named", len(pairs))
    log.info("chars     %d distinct", len(needed))
    log.info("covered   %d", len(needed) - len(substituted) - len(missing))
    log.info("via table %d%s", len(substituted), f"  {substituted}" if substituted else "")

    # Reported and never failed on: the English line is set in Godot's built-in
    # Noto Sans, not in this font, so its coverage is not this tool's to assert.
    # It is printed because a name that is not plain ASCII is worth knowing about
    # before it is worth checking.
    non_ascii = sorted({c for english, _ in pairs for c in english if ord(c) > 0x7E})
    if non_ascii:
        log.info("latin     non-ASCII in English names: %s", "".join(non_ascii))

    if missing:
        log.error("MISSING %d: %s", len(missing), "".join(missing))
        for character in missing:
            where = [en for en, zh in pairs if character in zh]
            log.error("  %s U+%04X — %s", character, ord(character), ", ".join(where))
        log.error(
            "Each draws as a tofu box on the plate. Add a row to %s mapping it to the SAME "
            "character in a form the font carries — never to a different word, and never by "
            "editing the name in the pipeline (Q54).",
            PLATE_TUNING.relative_to(ROOT),
        )
        return 1

    log.info("OK — every published street name is drawable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
