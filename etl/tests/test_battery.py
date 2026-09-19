"""`tools/battery.py` — the grader battery as a table (`P3-35b`, `Q133`).

What can go wrong with a table of commands is dull and silent: a script renamed
under it, a flag a grader never took, two items writing one file. None of those
raises until the day someone needs the battery, so they are pinned here.
"""

from __future__ import annotations

import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import battery
import pytest
from battery import TRIGGERS, Report, Side, Tool, Trigger, run, run_item

TOOLS = Path(battery.__file__).resolve().parent


@pytest.fixture(scope="session")
def usage() -> dict[str, str]:
    """Every grader's `--help`, asked at once: each is an interpreter start that
    imports numpy and the pipeline, and sixteen of them in turn is most of this
    file's wall time."""

    def ask(script: str) -> tuple[str, str]:
        done = subprocess.run(
            [sys.executable, str(TOOLS / script), "--help"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert done.returncode == 0, f"{script} --help: {done.stderr}"
        return script, done.stdout

    with ThreadPoolExecutor() as pool:
        return dict(pool.map(ask, sorted({tool.script for tool in _tools()})))


def _tools() -> list[Tool]:
    seen: dict[tuple[str, tuple[str, ...]], Tool] = {}
    for trigger in TRIGGERS.values():
        for item in trigger.items:
            if isinstance(item, Tool):
                seen[(item.script, item.args)] = item
    return list(seen.values())


class TestTheTable:
    def test_every_script_is_a_tool_that_exists(self) -> None:
        missing = [tool.script for tool in _tools() if not (TOOLS / tool.script).is_file()]
        assert not missing

    def test_no_two_items_of_a_trigger_write_one_file(self) -> None:
        """`paint_clearance.py --layer arrows` and `--layer roadmarks` are two
        runs; labelled by script alone the second overwrites the first and the
        diff is of one layer against itself."""
        for name, trigger in TRIGGERS.items():
            labels = [item.label for item in trigger.items]
            assert len(labels) == len(set(labels)), name

    def test_a_label_names_the_literal_arguments_and_no_path(self) -> None:
        tool = Tool("paint_clearance.py", ("--generated", "{generated}", "--layer", "arrows"))
        assert tool.label == "paint_clearance.layer.arrows"

    def test_every_tool_is_pointed_at_its_own_side(self) -> None:
        """🔴 A grader handed `--region` alone reads THIS checkout's `etl/out` on
        both sides, so its diff is empty by construction and reads as "nothing
        moved". `narrowing.py` shipped in the first table that way — it had no
        `--out-root` to be handed — and only review caught it."""
        unpointed = [
            tool.label for tool in _tools() if not {"{generated}", "{out_root}"} & set(tool.args)
        ]
        assert not unpointed

    @pytest.mark.parametrize("script", sorted({tool.script for tool in _tools()}))
    def test_every_flag_is_one_the_grader_takes(self, script: str, usage: dict[str, str]) -> None:
        """Read off `--help` rather than by running the grader: a misspelt flag
        is argparse's exit 2, which the runner reports as *did not run* — on the
        day the battery is owed, not before."""
        shown = usage[script]
        flags = {
            arg
            for tool in _tools()
            if tool.script == script
            for arg in tool.args
            if arg.startswith("--")
        }
        assert not {flag for flag in flags if flag not in shown}


def _side(root: Path, name: str = "after") -> Side:
    return Side(name, root, root / "tools")


def _script(root: Path, body: str) -> Tool:
    (root / "tools").mkdir(parents=True, exist_ok=True)
    (root / "tools" / "fake.py").write_text(body, encoding="utf-8")
    return Tool("fake.py", ("--region", "{region}"))


class TestWhatCountsAsRan:
    def test_a_grader_that_gates_and_fails_still_ran(self, tmp_path: Path) -> None:
        """`carriageway_occupancy.py` exits 1 on today's bundle. That is its
        answer, not a failure to give one."""
        tool = _script(tmp_path, "import sys; print('table'); sys.exit(1)")
        outcome = run_item(tool, _side(tmp_path), "r", tmp_path, sys.executable)
        assert outcome.ran and outcome.code == 1 and "table" in outcome.text

    def test_a_crash_did_not_run(self, tmp_path: Path) -> None:
        tool = _script(tmp_path, "raise RuntimeError('no bundle')")
        assert not run_item(tool, _side(tmp_path), "r", tmp_path, sys.executable).ran

    def test_a_refused_flag_did_not_run(self, tmp_path: Path) -> None:
        tool = _script(tmp_path, "import argparse; argparse.ArgumentParser().parse_args()")
        assert not run_item(tool, _side(tmp_path), "r", tmp_path, sys.executable).ran

    def test_a_grader_killed_by_a_signal_did_not_run(self, tmp_path: Path) -> None:
        tool = _script(tmp_path, "import os, signal; os.kill(os.getpid(), signal.SIGKILL)")
        assert not run_item(tool, _side(tmp_path), "r", tmp_path, sys.executable).ran

    def test_a_literal_argument_with_a_brace_is_passed_through(self, tmp_path: Path) -> None:
        assert _side(tmp_path).fill("{not a field", "r", tmp_path) == "{not a field"

    def test_a_missing_script_did_not_run(self, tmp_path: Path) -> None:
        outcome = run_item(Tool("gone.py"), _side(tmp_path), "r", tmp_path, sys.executable)
        assert not outcome.ran

    def test_a_report_on_an_unbuilt_side_did_not_run(self, tmp_path: Path) -> None:
        item = Report("signs.json", ("drawn",))
        assert not run_item(item, _side(tmp_path), "r", tmp_path, sys.executable).ran


def _built(root: Path, region: str, document: str, body: dict) -> None:
    out = root / "etl" / "out" / region
    out.mkdir(parents=True, exist_ok=True)
    (out / document).write_text(json.dumps(body), encoding="utf-8")


class TestAReport:
    def test_a_key_one_side_lacks_is_printed_and_not_raised(self, tmp_path: Path) -> None:
        _built(tmp_path, "r", "signs.json", {"drawn": 3, "poles": [1, 2]})
        item = Report("signs.json", ("drawn", "len:poles", "facing_away", "len:gone"))
        picked = json.loads(run_item(item, _side(tmp_path), "r", tmp_path, sys.executable).text)
        assert picked == {"drawn": 3, "len:poles": 2, "facing_away": "—", "len:gone": "—"}


class TestTheDiff:
    def test_a_moved_counter_is_in_the_diff_and_a_root_path_is_not(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        before, after = tmp_path / "b", tmp_path / "a"
        _built(before, "r", "fence.json", {"fenced_edges": [1, 2], "where": str(before)})
        _built(after, "r", "fence.json", {"fenced_edges": [1], "where": str(after)})
        monkeypatch.setitem(
            TRIGGERS, "t", Trigger("test", (Report("fence.json", ("fenced_edges", "where")),))
        )
        # Named anything: the diff is first against second, never a lookup by name.
        sides = [_side(before, "old"), _side(after, "new")]
        assert run("t", ["r"], sides, tmp_path / "out", sys.executable, jobs=2) == 0
        diff = (tmp_path / "out" / "t" / "r" / "fence.report.diff").read_text(encoding="utf-8")
        moved = [line for line in diff.splitlines() if line[:1] in "+-"]
        assert any(line.strip() == "-    2" for line in moved)
        # The two roots differ and the line naming them does not: not a moved line.
        assert not [line for line in moved if "<root>" in line]

    def test_the_moment_a_bundle_was_built_is_not_a_moved_line(self, tmp_path: Path) -> None:
        """Every bundle grader prints `built <generated_utc>` in its header, so a
        before/after pair read "2 line(s) moved" on graders where nothing had."""
        from battery import _normalised

        first = _normalised("wan_chai, LOD 0, built 2026-09-19T12:40:29Z\n", _side(tmp_path))
        second = _normalised("wan_chai, LOD 0, built 2026-09-19T12:57:17Z\n", _side(tmp_path))
        assert first == second

    def test_the_exit_code_is_whether_it_ran_and_never_whether_it_moved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(
            TRIGGERS, "t", Trigger("test", (Report("fence.json", ("fenced_edges",)),))
        )
        assert run("t", ["r"], [_side(tmp_path)], tmp_path / "out", sys.executable) == 1
