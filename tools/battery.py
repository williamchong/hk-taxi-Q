"""Run the grader battery a change owes, on two bundles, and diff the tables.

    tools/battery.py railings --region wan_chai --before ../wt-before
    tools/battery.py --list

`CLAUDE.md`'s "before marking work done" — in `.claude/rules/` since it outgrew
the root file — is some forty bullets of the shape
*"X changes: also `tools/y.py`, before and after, both regions, and paste its
table"*, and until `P3-35b` (`Q133`) every one was run by hand. This is the
table those bullets name, as data, and the loop that runs it.

A **side** is a checkout root — this repo, or a detached worktree holding the
before build. From it come the two things every grader is pointed at:
`<root>/game/assets/generated/<region>` (the synced bundle, `--generated`) and
`<root>/etl/out` (`--out-root`). `etl/sources/` is gitignored and a worktree has
none, so `--sources-root` is always this checkout's.

⚠️ **Both sides are graded by THIS checkout's tools.** A before/after diff holds
the instrument still and varies the bundle; grading the before side with its own
older grader varies both. `--tools-from side` is there for the case where the
bundle's schema moved under the grader and the old one is the only reader.

🚫 **It adds no gate.** The graders grade and exit 0, or gate and exit 1 on a
bundle that fails today (`carriageway_occupancy.py` does), and neither is this
tool's business: its exit code says whether every item **ran**, never whether a
number moved. A diff is a finding to go and read.

⚠️ **The table carries commands and never reasons.** Why a trigger owes what it
owes — and which column of the output is the finding — stays in the rule files,
which each trigger cites by its bullet's opening words.
"""

from __future__ import annotations

import argparse
import difflib
import itertools
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Tool:
    """One grader run. `args` may name `{region}`, `{generated}`, `{out_root}`
    and `{sources_root}`; each is filled per side."""

    script: str
    args: tuple[str, ...] = ()

    @property
    def label(self) -> str:
        # The literal arguments only — `--layer arrows`, `--sweep` — and never a
        # flag whose value is a per-side path, so both sides share one name.
        literal = [
            arg.lstrip("-")
            for index, arg in enumerate(self.args)
            if "{" not in arg and "{" not in "".join(self.args[index + 1 : index + 2])
        ]
        stem = Path(self.script).stem
        return ".".join([stem, *literal])


@dataclass(frozen=True)
class Report:
    """Chosen keys out of a stage's own JSON report under `etl/out/<region>/`.

    For the bullets that say *"paste `railings.json`'s `shift_m`, …"*: the stage
    grades itself and there is no tool to run. A missing key prints as `—`
    rather than raising, so a counter a side's schema does not have shows up in
    the diff instead of stopping the battery. `len:<key>` prints a list's length
    where the bullet wants a count and the rows would bury it."""

    document: str
    keys: tuple[str, ...]

    @property
    def label(self) -> str:
        return Path(self.document).stem + ".report"


Item = Tool | Report


@dataclass(frozen=True)
class Trigger:
    """What one kind of change owes. `cites` is the opening of the `CLAUDE.md`
    bullet that says why, so the two can be read side by side."""

    cites: str
    items: tuple[Item, ...]


_GENERATED = ("--generated", "{generated}")
_REGION = ("--region", "{region}")
_OUT = ("--out-root", "{out_root}")
_SOURCES = ("--sources-root", "{sources_root}")

# `Q19`'s battery, which four triggers below owe whole.
_Q19: tuple[Item, ...] = (
    Tool("carriageway_occupancy.py", _GENERATED),
    Tool("deck_error.py", _GENERATED),
    Tool("overhang.py", _GENERATED),
    Tool("ground_clearance.py", _GENERATED),
    Tool("clearance_reconcile.py", _GENERATED),
    Tool("narrowing.py", (*_REGION, *_OUT)),
)

TRIGGERS: dict[str, Trigger] = {
    "railings": Trigger(
        "`pipeline/railings.py`, the `railings` config block, or any railing change",
        (
            Report(
                "railings.json",
                (
                    "classes",
                    "refused_m",
                ),
            ),
            Tool("railing_error.py", (*_REGION, *_SOURCES, *_OUT)),
        ),
    ),
    "signs": Trigger(
        "`signs.outset_m`, `max_shift_m`, or `signs._register`",
        (
            Report(
                "signs.json",
                (
                    "drawn",
                    "poles_drawn",
                    "posts_kept_as_surveyed",
                    "posts_over_shift",
                    "posts_in_carriageway",
                    "posts_merged_after_shift",
                    "shift_m",
                    "plates_turned",
                    "no_entry_against_flow",
                    "no_entry_on_two_way",
                    "facing_away",
                ),
            ),
        ),
    ),
    "lamps": Trigger(
        "`pipeline/lamps.py`, the `lamps` config block, or any lamp-post change",
        (
            Report(
                "lamps.json",
                (
                    "features",
                    "drawn",
                    "min_kerb_clearance_m",
                    "shift_m",
                    "lantern_overhang_m",
                    "lanterns_past_centreline",
                    "spacing_surveyed_m",
                    "spacing_drawn_m",
                    "gaps_over_report_m",
                    "facing_away",
                ),
            ),
        ),
    ),
    "arrows": Trigger(
        "`pipeline/arrows.py`, the `arrows` config block, or any turn-arrow change",
        (
            Report(
                "arrows.json",
                (
                    "symbols",
                    "candidates",
                    "axis_residual_deg",
                    "offset_m",
                    "against_one_way",
                    "stacked_pairs",
                    "stacked_disagreeing",
                    "outside_carriageway",
                    "inverted",
                ),
            ),
            Tool("paint_clearance.py", (*_GENERATED, "--layer", "arrows")),
        ),
    ),
    "crossings": Trigger(
        "`pipeline/crossings.py`, the `crossings` config block, or any crossing stripe",
        (
            Report(
                "crossings.json",
                (
                    "features",
                    "candidates",
                    "drawn",
                    "too_far",
                    "no_face",
                    "drawn_by_kind",
                    "stripes_by_kind",
                    "area_m2_by_kind",
                    "refused_m_by_type",
                    "zigzag_gap_m",
                    "faces",
                    "too_wide",
                    "not_convex",
                    "faces_touching",
                    "unclosed_m",
                    "stripe_width_m",
                    "vertices_drawn",
                    "vertices_over_cap",
                    "vertices_over_void",
                    "slivers_dropped",
                    "inverted",
                ),
            ),
            Tool("paint_clearance.py", (*_GENERATED, "--layer", "crossings")),
        ),
    ),
    "roadmarks": Trigger(
        "`pipeline/roadmarks.py`, the `road_marks` config block, or any stop / give-way",
        (
            Report(
                "roadmarks.json",
                (
                    "drawn",
                    "drawn_by_id",
                    "drawn_m_by_id",
                    "host_disagreement",
                    "host_considered",
                    "host_off_carriageway",
                    "no_host_on_axis",
                    "axis_residual_deg",
                    "underfill_m",
                    "join",
                    "slivers_dropped",
                    "stations_on_drawn_structure",
                    "on_drawn_structure_m",
                    "inverted",
                ),
            ),
            Tool("paint_clearance.py", (*_GENERATED, "--layer", "roadmarks")),
        ),
    ),
    "boxjunctions": Trigger(
        "`pipeline/boxjunctions.py`, the `boxjunctions` block, or the ribbon's EXTENT",
        (
            Tool("box_extent.py", (*_GENERATED, "--sweep", *_SOURCES, *_OUT)),
            Tool("paint_clearance.py", (*_GENERATED, "--layer", "boxjunctions")),
        ),
    ),
    "fence": Trigger(
        "`pipeline/fence.py`, the `clearance` or `fence` blocks, or `RoadGraph`'s car bar",
        (
            Report(
                "fence.json",
                (
                    "fenced_edges",
                    "components",
                    "mouths",
                    "ends_behind_another_fence",
                    "ends_with_no_way_in",
                    "clipped_edges",
                    "clipped_ends",
                    "barriers",
                ),
            ),
        ),
    ),
    "lanes": Trigger(
        "Anything that moves `lanes`, `lanes_source`, `LANE_FLOOR`, `_ROW_MIN`",
        (Tool("lane_paint.py", (*_GENERATED, "--sweep")),),
    ),
    "width": Trigger(
        "`pipeline/carriageway.py`, the `carriageway_survey` block, or what moves `width_m`",
        (
            Tool("carriageway_margin.py", (*_REGION, *_SOURCES, *_OUT)),
            Tool("width_evidence.py", (*_REGION, *_SOURCES, *_OUT)),
            *_Q19,
        ),
    ),
    "region": Trigger(
        "`tools/carriageway_region.py`, or what builds the level-0 carriageway as a REGION",
        (Tool("carriageway_region.py", (*_REGION, *_SOURCES, *_OUT)),),
    ),
    "surface-region": Trigger(
        "`surface_region.py`, `_with_territory_stations`, `_stations_kept`, `_clamped_rails`",
        (
            Report(
                "roadsurface.json",
                (
                    "triangles",
                    "vertices",
                    "cut_vertices",
                    "len:caps",
                    "len:areas",
                    "clusters",
                ),
            ),
            Tool("lane_paint.py", (*_GENERATED, "--sweep")),
            Tool("box_extent.py", (*_GENERATED, *_SOURCES, *_OUT)),
            Tool("paint_clearance.py", _GENERATED),
            Report("fence.json", ("fenced_edges",)),
            Report("roadmarks.json", ("drawn_by_id", "drawn_m_by_id")),
        ),
    ),
    "off-grade": Trigger(
        "Anything that moves an OFF-GRADE ribbon",
        (
            Tool("deck_margin.py", _GENERATED),
            Tool("overhang.py", _GENERATED),
            Tool("touchdown_error.py", _GENERATED),
        ),
    ),
    "q19": Trigger("`Q19`'s battery: road-surface, deck-height or ground changes", _Q19),
    "carve": Trigger(
        "`pipeline/carve.py`, the `carve` config block, or which edges are carved",
        (Report("carve.json", ("edges", "tiles_written", "facing_away")), *_Q19),
    ),
    "collider": Trigger(
        "Collider changes — `buildings.collision_cell_m`, `class_collision_cell_m`",
        (Tool("collider_offset.py", (*_GENERATED, "--sweep", "1,2,4")),),
    ),
}


@dataclass(frozen=True)
class Side:
    name: str
    root: Path
    tools: Path

    def fill(self, template: str, region: str, sources_root: Path) -> str:
        """The four placeholders by name and nothing else — not `str.format`,
        which would read a brace in a literal argument as a field."""
        values = {
            "{region}": region,
            "{generated}": self.root / "game" / "assets" / "generated" / region,
            "{out_root}": self.root / "etl" / "out",
            "{sources_root}": sources_root,
        }
        for placeholder, value in values.items():
            template = template.replace(placeholder, str(value))
        return template


@dataclass(frozen=True)
class Outcome:
    text: str
    ran: bool
    code: int | None = None


def _value(body: dict, key: str) -> object:
    if key.startswith("len:"):
        rows = body.get(key[4:])
        return len(rows) if isinstance(rows, list | dict) else "—"
    return body.get(key, "—")


def _picked(document: Path, keys: tuple[str, ...]) -> Outcome:
    try:
        body = json.loads(document.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return Outcome(f"{document}: {error} — has this side been built?\n", ran=False)
    chosen = {key: _value(body, key) for key in keys}
    return Outcome(
        json.dumps(chosen, indent=2, sort_keys=True, ensure_ascii=False) + "\n", ran=True
    )


def run_item(item: Item, side: Side, region: str, sources_root: Path, python: str) -> Outcome:
    if isinstance(item, Report):
        return _picked(side.root / "etl" / "out" / region / item.document, item.keys)
    script = side.tools / item.script
    if not script.is_file():
        # Checked rather than left to the interpreter, whose "can't open file"
        # is an exit 2 indistinguishable from argparse refusing a flag.
        return Outcome(f"{script} is not there\n", ran=False)
    command = [python, str(script), *(side.fill(a, region, sources_root) for a in item.args)]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    # Graders log to stderr and print tables to stdout, and which is which varies
    # by tool, so both are kept — stdout first, because that is the table.
    text = done.stdout + done.stderr
    # A grader exits 1 when it gates and the bundle fails; that is its answer.
    # What means "did not run" is a crash, argparse's 2, and a signal's negative.
    crashed = done.returncode not in (0, 1) or "Traceback (most recent call last)" in done.stderr
    return Outcome(text + f"\n[exit {done.returncode}]\n", ran=not crashed, code=done.returncode)


# `city.json`'s `generated_utc`, which every bundle grader prints in its header.
_BUILT_AT = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")


def _normalised(text: str, side: Side) -> list[str]:
    """What differs between two sides without being a finding, rewritten away:
    the side's own root, and the moment its bundle was built."""
    text = text.replace(str(side.root.resolve()), "<root>").replace(str(side.root), "<root>")
    return _BUILT_AT.sub("<built>", text).splitlines(keepends=True)


def run(
    trigger: str, regions: list[str], sides: list[Side], out: Path, python: str, jobs: int = 1
) -> int:
    """Every item of `trigger`, per region and side; 1 if any did not run.

    With two sides the first is diffed against the second, whatever they are
    called. `jobs` runs graders side by side — they are separate processes that
    write nothing (`--json` is never passed) — and the table below is printed
    from the work list's own order afterwards, so it reads the same at any `jobs`.
    """
    owed = TRIGGERS[trigger]
    sources_root = ROOT / "etl" / "sources"
    print(f"battery: {trigger} — {owed.cites}")
    work = list(itertools.product(regions, owed.items, sides))
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        outcomes = list(
            pool.map(lambda unit: run_item(unit[1], unit[2], unit[0], sources_root, python), work)
        )

    failed = 0
    texts: dict[tuple[str, str], list[list[str]]] = {}
    for (region, item, side), outcome in zip(work, outcomes, strict=True):
        target = out / trigger / region / side.name / f"{item.label}.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(outcome.text, encoding="utf-8")
        texts.setdefault((region, item.label), []).append(_normalised(outcome.text, side))
        failed += not outcome.ran
        code = "" if outcome.code is None else f" exit {outcome.code}"
        state = "ran" if outcome.ran else "DID NOT RUN"
        print(f"  {region:<14} {item.label:<40} {side.name:<7} {state}{code}")

    if len(sides) == 2:
        names = [side.name for side in sides]
        for (region, label), (first, second) in texts.items():
            diff = list(difflib.unified_diff(first, second, *names))
            target = out / trigger / region / f"{label}.diff"
            target.write_text("".join(diff), encoding="utf-8")
            moved = sum(line[:1] in "+-" and line[:3] not in ("+++", "---") for line in diff)
            print(f"  {region:<14} {label:<40} {'diff':<7} {moved} line(s) moved → {target}")
    if failed:
        print(f"battery: {failed} item(s) did not run")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("trigger", nargs="?", choices=sorted(TRIGGERS))
    parser.add_argument("--list", action="store_true", help="print the table and exit")
    parser.add_argument("--region", action="append", help="repeatable; default wan_chai")
    parser.add_argument("--before", type=Path, help="checkout root of the before build")
    parser.add_argument("--after", type=Path, default=ROOT, help="default: this checkout")
    parser.add_argument(
        "--tools-from",
        choices=("self", "side"),
        default="self",
        help="grade each side with this checkout's tools (default) or with its own",
    )
    parser.add_argument("--out", type=Path, default=ROOT / "build" / "battery")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="graders to run at once; 2 is the two sides of one item, and each "
        "holds a bundle in memory (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    if args.list:
        for name in sorted(TRIGGERS):
            print(f"{name}\n    {TRIGGERS[name].cites}")
            for item in TRIGGERS[name].items:
                print(f"      {item.label}")
        return 0
    if args.trigger is None:
        parser.error("name a trigger, or --list")

    def side(name: str, root: Path) -> Side:
        root = root.resolve()
        tools = (root if args.tools_from == "side" else ROOT) / "tools"
        return Side(name, root, tools)

    sides = [side("after", args.after)]
    if args.before is not None:
        sides.insert(0, side("before", args.before))
    return run(args.trigger, args.region or ["wan_chai"], sides, args.out, args.python, args.jobs)


if __name__ == "__main__":
    sys.exit(main())
