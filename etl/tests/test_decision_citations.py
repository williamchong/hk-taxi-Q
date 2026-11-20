"""Every `Qnnn` cited in backticks names a heading in docs/DECISIONS.md.

A comment or rule carries the claim and cites its decision for the evidence
(CONTRIBUTING.md). A citation that resolves to nothing sends the reader to no
evidence at all, and a typo reads exactly like a real one. This cannot tell a
citation of the wrong decision (`Q59` for the winding signs, `Q259`) from the
right one; it holds that the decision exists.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / "docs" / "DECISIONS.md"
CITATION = re.compile(r"`(Q\d+)`")
TEXT = (".py", ".gd", ".md", ".gdshader", ".gdshaderinc", ".sh", ".yaml", ".toml", ".cfg")


def _decided() -> set[str]:
    """The ids DECISIONS.md heads an entry with; one heading can carry several."""
    headings = re.findall(r"^## (.*)$", DECISIONS.read_text(), re.MULTILINE)
    return {q for heading in headings for q in CITATION.findall(heading.split(" — ")[0])}


def _tracked() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True, text=True
    ).stdout
    return [ROOT / name for name in listed.split("\0") if name.endswith(TEXT)]


def test_every_cited_decision_exists() -> None:
    decided = _decided()
    assert len(decided) > 200, f"read only {len(decided)} decisions out of {DECISIONS}"
    dangling = []
    for path in _tracked():
        text = path.read_text(errors="replace")
        for match in CITATION.finditer(text):
            if match.group(1) not in decided:
                line = text.count("\n", 0, match.start()) + 1
                dangling.append(f"{path.relative_to(ROOT)}:{line} {match.group(1)}")
    assert not dangling, "cites a decision DECISIONS.md has no heading for:\n" + "\n".join(dangling)
