"""Cut the bundled 黑體 and brush faces down to what the game draws (`Q218`).

Three committed files under `game/assets/authored/fonts/`, each a subset of an
SIL OFL 1.1 font this project did not author:

- `NotoSansHK-subset.ttf` — Noto Sans HK (variable weight), the interface's
  黑體, cut to the text the game itself holds: every character in
  `game/tuning/` and in the scripts' own strings. It is never handed a street
  or a building, which are the Kai's, so the Kai's repertoire is not in it —
  that cut was 3.6 MB for glyphs no line asks for.
- `TaxiAceBrush-Medium.ttf` — Bakudai Medium (莫大毛筆), the menu's choices and
  headings and the HUD's skill and penalty names, cut to the same text as the
  黑體: the two stand side by side in one flash.
- `TaxiAceBrush-Bold.ttf` — Bakudai Bold, the game's name alone, cut to the
  `title` strings.

⚠️ **The brush subsets are RENAMED, and that is a licence term, not taste.**
Bakudai declares the Reserved Font Name "Bakudai", and OFL 1.1 clause 3 bars a
Modified Version from carrying it; a subset is a Modified Version. Noto Sans HK
reserves only 'Source', so its subset keeps its name. Every copyright and
licence record in the `name` table is kept as published, which is how the
notice travels inside the file (clause 2).

⚠️ **A wording change can outrun a subset.** A character the committed file
lacks draws in the next face down — a brush line's in the 黑體, a 黑體 line's
in the Kai — in the middle of the line, never as a box. `etl/tests/test_fonts.py`
fails on it; re-run this tool.

⚠️ **`fontTools` is this tool's alone** (`pip install fonttools`), not an ETL
dependency: `font_coverage.py` and the test read a `cmap` by hand so nothing on
the build's path needs a font library.

The sources are not committed (45 MB). Fetch them into one directory:

    Bakudai-Medium.ttf, Bakudai-Bold.ttf
        https://github.com/max32002/bakudaifont  tw/  @ f1eb195c
    NotoSansHK[wght].ttf
        https://github.com/google/fonts  ofl/notosanshk/  @ 2ac7e8ea

Run:  python tools/make_fonts.py --sources <dir>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "game" / "assets" / "authored" / "fonts"
TUNING = ROOT / "game" / "tuning"
MENU_TEXT = TUNING / "menu_text.json"
SCRIPTS = ROOT / "game" / "scripts"
CITY_CONFIG = ROOT / "etl" / "config" / "hong_kong.yaml"

HEI_OUT = FONTS / "NotoSansHK-subset.ttf"
BRUSH_OUT = FONTS / "TaxiAceBrush-Medium.ttf"
TITLE_OUT = FONTS / "TaxiAceBrush-Bold.ttf"

# What the brush subsets are called, since "Bakudai" is reserved.
BRUSH_FAMILY = "Taxi Ace Brush"

# The published files this was cut from, so a re-run starts from the same glyphs.
SOURCES: dict[str, str] = {
    "Bakudai-Medium.ttf": "6c4a1be29e508fed588d8ec749ed8ae9e3b8325af0e0a973657739256dba9997",
    "Bakudai-Bold.ttf": "59c99887980e8002c4dea7c4ad7b207e9dd080cf1aef0f698750f4f806183cf8",
    "NotoSansHK[wght].ttf": "76098ee78ec234cd4f8c950742b3f766fea2f8b43d5180d901048f4fc86c6849",
}

# The punctuation the game's own lines are composed with in code, beside
# printable ASCII: the middle dot, the multiplication sign, a proper minus, the
# ellipsis, and the full-width marks. Code points, since ruff reads the
# characters themselves as typos.
COMPOSED: tuple[int, ...] = (
    0x00B7,
    0x00D7,
    0x2212,
    0x2026,
    0x3001,
    0x3002,
    0x300C,
    0x300D,
    0xFF08,
    0xFF09,
    0xFF0C,
    0xFF1A,
    0xFF1B,
)

log = logging.getLogger(__name__)


def base_codes() -> set[int]:
    """ASCII and the punctuation every subset carries."""
    return set(range(0x20, 0x7F)) | set(COMPOSED)


def shown_codes() -> set[int]:
    """Every character the game holds to show: its tuning and its scripts' strings."""
    codes: set[int] = set()
    for path in sorted([*TUNING.glob("*.json"), *TUNING.glob("*.tres"), *SCRIPTS.rglob("*.gd")]):
        codes |= {ord(c) for c in path.read_text(encoding="utf-8")}
    return codes


def signboard_codes() -> set[int]:
    """Every character `signboards.text` can letter a board with (`Q260`).

    Read as text, the block's own lines, so the tool needs no YAML library and a
    comment elsewhere in the config adds nothing to the subset.
    """
    lines = CITY_CONFIG.read_text(encoding="utf-8").splitlines()
    start = lines.index("signboards:")
    codes: set[int] = set()
    inside = False
    for line in lines[start + 1 :]:
        if line and not line.startswith(" "):
            break
        if line.startswith("  text:"):
            inside = True
        elif line.startswith("  ") and not line.startswith("   "):
            inside = False
        if inside and not line.lstrip().startswith("#"):
            codes |= {ord(c) for c in line if ord(c) > 0x2E7F}
    if not codes:
        raise ValueError(f"{CITY_CONFIG} has no signboards.text block with a character in it")
    return codes


def title_codes() -> set[int]:
    """The game's name in each language."""
    title = json.loads(MENU_TEXT.read_text(encoding="utf-8"))["strings"]["title"]
    return {ord(c) for said in title.values() for c in said}


def cut(source: Path, out: Path, codes: set[int], family: str = "", style: str = "") -> None:
    """Write `source` cut down to `codes`, renamed to `family` `style` if given."""
    from fontTools import subset
    from fontTools.ttLib import TTFont

    font = TTFont(source, recalcTimestamp=False)
    options = subset.Options()
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    cutter = subset.Subsetter(options)
    cutter.populate(unicodes=sorted(codes))
    cutter.subset(font)
    if family:
        full = f"{family} {style}"
        for name_id, said in ((1, family), (2, style), (4, full), (6, full.replace(" ", ""))):
            for record in list(font["name"].names):
                if record.nameID == name_id:
                    font["name"].setName(
                        said, name_id, record.platformID, record.platEncID, record.langID
                    )
        # The unique id and the typographic family name the source by its own name.
        font["name"].names = [r for r in font["name"].names if r.nameID not in (3, 16, 17)]
    font.save(out)
    log.info(
        "%s: %d characters, %d KB", out.name, len(font.getBestCmap()), out.stat().st_size // 1024
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sources", type=Path, required=True, help="directory of the three fonts")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # The subsetter reports every code point a source lacks; the test is the check.
    logging.getLogger("fontTools").setLevel(logging.ERROR)

    for name, wanted in SOURCES.items():
        path = args.sources / name
        if not path.exists():
            log.error("%s is not in %s", name, args.sources)
            return 1
        if hashlib.sha256(path.read_bytes()).hexdigest() != wanted:
            log.error("%s is not the published file this tool was written against", name)
            return 1

    base = base_codes()
    shown = shown_codes() | signboard_codes() | base
    cut(args.sources / "NotoSansHK[wght].ttf", HEI_OUT, shown)
    cut(args.sources / "Bakudai-Medium.ttf", BRUSH_OUT, shown, BRUSH_FAMILY, "Medium")
    cut(args.sources / "Bakudai-Bold.ttf", TITLE_OUT, title_codes() | base, BRUSH_FAMILY, "Bold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
