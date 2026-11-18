"""A grader and the code it grades are two implementations, and stay two.

Each pair below measures the same thing twice on purpose: the grader is the
instrument, and an instrument that calls the code under test agrees with it by
construction, so a bug in one would grade itself correct. A change to the rule
both encode is made twice, by hand, and the grader's own diff against the stage
is the check on the pair. This holds each grader to that by reading its source.

- `tools/carriageway_margin.py` re-surveys the carriageway width `Q95` publishes
  (two independent implementations on the user's instruction).
- `tools/carriageway_region.py` rebuilds the level-0 territory `pipeline/region.py`
  ships and diffs it per territory (`against_stage`, `Q129`).
- `pipeline/arrows.py` reads a row of arrows into a lane count the way
  `pipeline/carriageway.py` does, and `lanes_row_disagreement` /
  `lanes_split_disagreement` are their diff (`Q126`). The other direction is an
  import cycle already (carriageway ← roads ← arrows).
- `tools/skidpad_ablation.gd` measures slip off the body's own velocity beside
  the game's `SlipAngle.deg_of`, the one `FareSystem` scores (`Q84`, `Q145`).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

PYTHON_BANS: dict[str, frozenset[str]] = {
    "tools/carriageway_margin.py": frozenset({"pipeline.carriageway", "pipeline.carriageway_area"}),
    "tools/carriageway_region.py": frozenset(
        {"pipeline.region", "pipeline.carriageway", "pipeline.carriageway_area"}
    ),
    "etl/pipeline/arrows.py": frozenset({"pipeline.carriageway"}),
}
GDSCRIPT_BANS: dict[str, tuple[str, ...]] = {
    "tools/skidpad_ablation.gd": ("SlipAngle", "slip_deg_of"),
}


def _imported(path: Path) -> set[str]:
    """Every module `path` names in an import, spelt in full."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
            # `from pipeline import carriageway` names the module as an alias.
            names.update(f"{node.module}.{alias.name}" for alias in node.names)
    return names


@pytest.mark.parametrize("grader", sorted(PYTHON_BANS))
def test_a_python_grader_imports_nothing_it_grades(grader: str) -> None:
    shared = _imported(ROOT / grader) & PYTHON_BANS[grader]
    assert not shared, f"{grader} imports {sorted(shared)}, the code it grades"


@pytest.mark.parametrize("grader", sorted(GDSCRIPT_BANS))
def test_a_gdscript_grader_calls_nothing_it_grades(grader: str) -> None:
    code = "\n".join(line.split("#", 1)[0] for line in (ROOT / grader).read_text().splitlines())
    named = [name for name in GDSCRIPT_BANS[grader] if re.search(rf"\b{name}\b", code)]
    assert not named, f"{grader} calls {named}, the code it grades"
