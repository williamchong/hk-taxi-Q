"""The bundled font subsets against the text they are asked to draw (`Q218`).

**The committed-asset guard**, like `test_make_splash.py`: the three subsets
under `game/assets/authored/fonts/` are cut by `tools/make_fonts.py` from the
game's own text, and `tools/check.sh` does not know that tool exists. A wording
change the subset has not caught up with draws one character of a brush line
in the 黑體 — the loader's fallback, so never a box, and never noticed.

Read with `font_coverage.read_cmap`, so this needs no font library.
"""

from __future__ import annotations

import json
from pathlib import Path

from font_coverage import read_cmap

ROOT = Path(__file__).resolve().parent.parent.parent
FONTS = ROOT / "game" / "assets" / "authored" / "fonts"
TUNING = ROOT / "game" / "tuning"
SCRIPTS = ROOT / "game" / "scripts"
MENU_TEXT = TUNING / "menu_text.json"

# The CJK blocks a line is set in — ideographs, their punctuation and the
# full-width forms. Latin may come from another face without it showing, and a
# comment's emoji is not text the game draws.
CJK_BLOCKS: tuple[tuple[int, int], ...] = ((0x3000, 0x303F), (0x4E00, 0x9FFF), (0xFF00, 0xFFEF))


def _cjk(text: str) -> set[int]:
    return {ord(c) for c in text if any(low <= ord(c) <= high for low, high in CJK_BLOCKS)}


def _lacking(font: str, wanted: set[int]) -> str:
    return "".join(sorted(chr(code) for code in wanted - read_cmap(FONTS / font)))


def test_the_brush_draws_every_character_of_the_menu() -> None:
    lacking = _lacking("TaxiAceBrush-Medium.ttf", _cjk(MENU_TEXT.read_text(encoding="utf-8")))
    assert not lacking, f"the brush subset lacks {lacking} — re-run tools/make_fonts.py"


def test_the_title_brush_draws_the_name() -> None:
    title = json.loads(MENU_TEXT.read_text(encoding="utf-8"))["strings"]["title"]
    lacking = _lacking("TaxiAceBrush-Bold.ttf", _cjk("".join(title.values())))
    assert not lacking, f"the title subset lacks {lacking} — re-run tools/make_fonts.py"


def test_the_hei_draws_every_character_the_game_shows() -> None:
    # The tuning and the scripts' own strings: a caption decided in code
    # (`FareFace`, `hud.gd`) is interface text like any other.
    shown: set[int] = set()
    for path in sorted([*TUNING.glob("*.json"), *TUNING.glob("*.tres"), *SCRIPTS.rglob("*.gd")]):
        shown |= _cjk(path.read_text(encoding="utf-8"))
    lacking = _lacking("NotoSansHK-subset.ttf", shown)
    assert not lacking, f"the 黑體 subset lacks {lacking} — re-run tools/make_fonts.py"


def test_the_brush_subsets_do_not_carry_the_reserved_name() -> None:
    # OFL 1.1 clause 3: "Bakudai" is reserved, and a subset is a Modified
    # Version. The name may stand only inside the copyright and licence
    # records, which the file must keep (clause 2).
    for font in ("TaxiAceBrush-Medium.ttf", "TaxiAceBrush-Bold.ttf"):
        data = (FONTS / font).read_bytes()
        for encoding in ("utf-16-be", "ascii"):
            for said in ("Bakudai Medium", "Bakudai Bold", "Bakudai-", "BakudaiM", "BakudaiB"):
                assert said.encode(encoding) not in data, f"{font} still names itself {said}"
