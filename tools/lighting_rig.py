"""The exposure the lighting rig multiplies every city albedo by (`Q38`).

🔴 **One home for one number, and this module is the *reader* rather than the
home.** `P5-28c` un-baked `exposure_anchor` out of `hong_kong.yaml`, where it was
applied at load and shipped multiplied into `COLOR_0` on every vertex of every
tile. It is a Godot global shader parameter now, declared in `game/project.godot`
and set from an `@export` on the rig scene by `scripts/world/lighting_rig.gd` —
so a time of day is one number in one scene instead of a full region rebuild.

⚠️ **It must NOT come back into `etl/`.** A grader that wants the rendered
palette has to reach across to the game, and reaching across is the honest shape:
the ETL publishes a material's reflectance and knows nothing about the hour. A
copy under `pipeline/` would re-couple the two halves the un-bake separated, and
the copy is the one nobody remembers to move.

Two graders read it, for different reasons and to different depths:

- `facade_chroma.py` applies it to every figure it prints, because **chroma does
  not survive a linear-light scale**. In CIELAB's cubic regime a uniform scale of
  the luminance multiplies `a*` and `b*` — and so `C*` — by `anchor ** (1/3)`
  exactly: **0.804** at 0.520, verified to four places on the shipped bands
  (`C*` 2.18-17.19 unexposed against 1.76-13.83 rendered). So an unexposed table
  reads **1.24x MORE saturated** than the screen, not less.
- `frame_stats.py` applies it to `--albedo-l` alone, and there it moves **`gain`
  only**. `additive share` is built on a *ratio* of linear luminances, and a
  uniform scale cancels exactly in a ratio; `gain` divides by an `L*` difference,
  and `L*` is not linear in luminance, so that denominator does move.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The rig graders work under by default. `ART_DESIGN.md` judges façades under
# both; this is the neutral one — `golden_hour` is a look and `clean_daylight` is
# the control.
DEFAULT_RIG = ROOT / "game" / "scenes" / "world" / "clean_daylight.tscn"

# The `@export` the rig scene sets on `lighting_rig.gd`. ⚠️ **Matched rather than
# parsed**: a `.tscn` is Godot's to write (`Q119`), so anything here that looked
# like a scene parser would be a second reader of a format this repo does not own
# and would go stale the first time the writer changed its mind about quoting.
# ⚠️ **The character class is `kerbside_error.py`'s `_PARAMETER`, deliberately** —
# that tool pulls scalars out of a `.tres` the same way, and two spellings of "a
# Godot float" in one tree would eventually disagree about one.
_ANCHOR_LINE = re.compile(r"^exposure_anchor\s*=\s*([-\d.eE]+)\s*$", re.MULTILINE)

# The bar `lighting_rig.gd`'s `@export_range` sets, restated rather than read.
# ⚠️ **A grader that accepted what the editor refuses would report a palette the
# game cannot render**, and the scene file is plain text a hand edit reaches.
_ANCHOR_MIN, _ANCHOR_MAX = 0.001, 2.0


def rig_exposure(rig: Path = DEFAULT_RIG) -> float:
    """The rig's `exposure_anchor`.

    🔴 **Exactly one line, refused otherwise, because the engine and this reader
    would otherwise disagree about which.** `lighting_rig.gd` warns that two rigs
    alive at once fight over the process-wide global and *the last one readied
    wins*; a `.search` here takes the **first** match. On the one file shape that
    warning is about, the two answers are opposite and both are silent. So this
    finds them all and refuses anything but one.

    ⚠️ **Absent is an error and never a default.** A rig with no line renders at
    the *script's* default — `1.0` today, and `project.godot`'s `[shader_globals]`
    carries the same 1.0, which is why the two are easy to confuse. 🔴 **They are
    not interchangeable and the difference is a trap**: Godot's writer omits any
    value equal to the script default (`Q119`), so tidying that default to 0.520
    would drop the line from **both** `.tscn`s and leave this reader failing on
    two perfectly correct rigs. Move the script default and this refusal has to
    move with it.
    """
    found = _ANCHOR_LINE.findall(rig.read_text(encoding="utf-8"))
    if len(found) != 1:
        raise ValueError(
            f"{rig} sets exposure_anchor {len(found)} times, wanted exactly one "
            "— see scripts/world/lighting_rig.gd"
        )
    anchor = float(found[0])
    if not _ANCHOR_MIN <= anchor <= _ANCHOR_MAX:
        raise ValueError(
            f"{rig} sets exposure_anchor {anchor}, outside the "
            f"[{_ANCHOR_MIN}, {_ANCHOR_MAX}] its own @export_range allows"
        )
    return anchor
