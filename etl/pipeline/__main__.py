"""The whole pipeline, in order (`P1-6`).

    python -m pipeline --region wan_chai

Runs each stage by calling its own `main`, with the same arguments the
documented per-stage command would pass. That is deliberate rather than
convenient: composing the stages any other way — importing `build_region`
directly, say — would create a second code path whose behaviour could drift
from the one people actually run, and the drift would show up as a full build
that quietly differs from a partial one.

Ordering is a real dependency chain, not a preference. `surface` reads the
graph `roads` writes, `clearance` measures the ribbon `surface` drew against the
tiles `buildings` wrote, `fares` snaps to the graph, `tramway` lies on the road
and the ground those two drew, and `export` reconciles them.
Only `buildings` is independent, and it runs early because it is by far the
longest stage — a mistake in it is worth hitting before the quick ones.

`fetch` is the only stage that touches the network, and it is a cache hit after
the first run. `--from` skips ahead when you already have what it would fetch.

`--jobs N` runs stages side by side, each as the process its own documented
command starts, a stage beginning the moment everything `NEEDS` names for it is
done. The output is the serial run's to the byte; `--jobs 1`, the default, IS
the serial run, in this process, as it always was.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait

from pipeline import (
    arrows,
    basemap,
    boxjunctions,
    buildings,
    carve,
    clearance,
    crossings,
    export,
    fares,
    fence,
    fetch,
    lamps,
    landmarks,
    parked,
    podiums,
    railings,
    region,
    roadmarks,
    roads,
    signs,
    surface,
    tramway,
)

log = logging.getLogger(__name__)

# Name to entry point. Order is the run order; see the module docstring.
# `podiums` sits before `buildings` because that is the dependency direction:
# the buildings stage consumes `podiums.json` when `R4` packs the boundary,
# so the order never has to move when it starts to.
STAGES: dict[str, Callable[[list[str]], int]] = {
    "fetch": fetch.main,
    "podiums": podiums.main,
    # Before `buildings`, and forced since the world's water (2026-09-25):
    # the tile stage sinks the ground under this stage's sea polygon
    # (`buildings.sink_sea`), so the document has to exist first. It reads
    # only the source sheets and the city file, no stage output, so nothing
    # upstream of it moves.
    "basemap": basemap.main,
    "buildings": buildings.main,
    "landmarks": landmarks.main,
    "roads": roads.main,
    # After `roads` because the prism is the `width_m` that stage surveys,
    # and that is forced rather than tidy. Before `clearance`, which re-reads
    # the LOD0 tiles this rewrites and is how a carve reaches `city.json` —
    # run it after and the bundle would publish clearances for structure that
    # is no longer there. ⚠️ Nothing upstream reads a carved tile: `roads`
    # samples deck heights from the source sheets (`read_sheet`), not from
    # tiles, so the chain stays acyclic and a re-run is deterministic.
    "carve": carve.main,
    # After `roads` for the graph and before `surface`, which reads it
    # (`P3-33c`). It reads no tile, so its place against `carve` is tidy rather
    # than forced. ⚠️ `export`'s inputs are an explicit list and
    # `carriageway_region.json` is not on it: it reaches the bundle only as what
    # `surface` draws from it.
    "region": region.main,
    "surface": surface.main,
    # After `surface` because it measures the ribbon that stage drew, and before
    # `export` because `city.json` carries the result. It reads the building
    # tiles too, which is why it cannot run any earlier than this.
    "clearance": clearance.main,
    # After `clearance`, and forced rather than tidy: the fenced set is read
    # off `clearance.json` against the car's own width, so this cannot run
    # before the measurement it fences on. Before `export`, which names the
    # document. ⚠️ It reads no tile and moves no geometry — the barrier is a
    # committed authored prop and this stage publishes only where it stands.
    "fence": fence.main,
    "fares": fares.main,
    # After `surface` and `buildings`, and forced: a rail lies on what is drawn
    # under it, so this reads the road chunks and the ground out of the tiles
    # (`Q58`, 2026-10-06). Before `export`, because `city.json` names the asset.
    "tramway": tramway.main,
    # After `surface`, and unlike `tramway` that is forced rather than tidy: it
    # reads `roadsurface.json` for the drawn half-width at each station, because
    # a published arrow is registered into the lane the ribbon actually has
    # rather than the one the config says it should. Before `export`, which
    # names the asset.
    "arrows": arrows.main,
    # After `roads` because every vertex takes its height from the nearest
    # level-0 centreline — `tramway`'s dependency, not `arrows`'s: it reads no
    # ribbon, since a surveyed polygon is drawn at its surveyed extent rather
    # than registered into a lane. Before `export`, which names the asset.
    "boxjunctions": boxjunctions.main,
    # After `surface`, for `roadsurface.json` — each stripe vertex takes the drawn
    # road's own height (`DrawnSurface`), as a box's does. Before `export`.
    "crossings": crossings.main,
    # After `roads` for the level-0 centrelines — the height under each vertex
    # and the host edge each bar is drawn **across** — and after `surface` for
    # `roadsurface.json`'s drawn half-width. ⚠️ **The second one is a dependency
    # of a counter, not of the geometry**: a published bar is drawn at its
    # surveyed extent and never registered into a lane, so `arrows`' ribbon
    # argument does not apply — but `underfill_m` measures a drawn bar against a
    # drawn kerb, and the graph publishes only the *authored* width. Reading the
    # graph there was an 18x error. Before `export`, which names the asset.
    "roadmarks": roadmarks.main,
    # After `surface`, and forced rather than tidy — `arrows`'s dependency plus
    # one of its own. It reads `roadsurface.json` for the drawn half-width, the
    # junction trims **and** `kerb_hidden_m`: a railing is drawn on the kerb the
    # ribbon actually has, and where that kerb is buried under the opposing
    # carriageway there is no kerb to put a fence on. Before `export`, which
    # names the asset.
    "railings": railings.main,
    # After `surface`, and forced rather than tidy — the same dependency `arrows`
    # and `railings` have. ⚠️ **It reads `roadsurface.json`**: a published sign
    # pole is registered onto the kerb the ribbon actually drew, because 77.3% of
    # them are surveyed inside the 1.6x ribbon and drawn where published three
    # quarters of the city's signs stand in the road. It needs `roads` too, for
    # the level-0 centrelines that give it a host edge, a height and the kerb side
    # that resolves its facing. Before `export`, which names the asset.
    "signs": signs.main,
    # After `surface` and `roads`, the dependency `arrows`, `railings` and
    # `signs` all have, and for `signs`' reason exactly: a published lamp
    # post is registered onto the kerb the ribbon actually drew, because 64.1% of
    # them are surveyed inside the 1.6x ribbon and drawn where published four
    # fifths of a kilometre of the region's columns stand in the carriageway. It
    # needs `roads` for the level-0 centrelines that give it a host edge, a deck
    # height and the kerb side its arm reaches away from. Before `export`, which
    # names the asset.
    "lamps": lamps.main,
    # After `fares`, `tramway`, `fence` and `surface` (`P3-71`): the stationary
    # vehicles stand at the kerb the ribbon drew, clear of the fare nodes, on
    # the tram beds the tramway laid, and off the fenced edges. Before
    # `export`, which names the document.
    "parked": parked.main,
    "export": export.main,
}


# What each stage reads of another's output, which is all `--jobs` needs to
# know. 🔴 **Measured, not read off the comments above**: every stage was run
# under an audit hook that logged each file it opened below `etl/out`, on both
# built regions, and this is that log — a stage needs the writer of every file
# it read. The run order above is one valid order of it; this is the rest.
#
# Three entries say more than the log did, each on purpose:
#   - `buildings` needs `podiums`. It opens no `podiums.json` today; `STAGES`
#     says it will the day `R4` packs the boundary, and the order must not have
#     to move then.
#   - `clearance` needs `carve` and not merely `buildings`: both write `tiles/`
#     and `buildings.json`, and the clearance is of the carved ones.
#   - everything needs `fetch`, which writes the sources tree and nothing here.
#
# ⚠️ No stage opened a file under ANOTHER region's directory, on either region,
# so two regions build side by side as two processes; `pipeline.join` is the
# stage that reads both and it is not on this list.
#
# `test_every_stage_is_scheduled` holds this to `STAGES`: a new stage with no
# entry here would otherwise start first and read whatever was on disk.
NEEDS: dict[str, tuple[str, ...]] = {
    "fetch": (),
    "podiums": ("fetch",),
    "basemap": ("fetch",),
    "buildings": ("podiums", "basemap"),
    "landmarks": ("fetch",),
    "roads": ("fetch",),
    "carve": ("buildings", "roads"),
    "region": ("roads",),
    "surface": ("region",),
    "clearance": ("carve", "landmarks", "surface"),
    "fence": ("clearance",),
    "fares": ("roads",),
    "tramway": ("buildings", "surface"),
    "arrows": ("surface",),
    "boxjunctions": ("surface",),
    "crossings": ("surface",),
    "roadmarks": ("surface",),
    "railings": ("surface",),
    "signs": ("surface",),
    "lamps": ("surface",),
    "parked": ("surface", "fares", "tramway", "fence"),
    "export": (
        "basemap",
        "landmarks",
        "carve",
        "clearance",
        "fence",
        "fares",
        "tramway",
        "arrows",
        "boxjunctions",
        "crossings",
        "roadmarks",
        "railings",
        "signs",
        "lamps",
        "parked",
    ),
}


def _stage_argv(name: str, region: str, force: bool) -> list[str]:
    stage_argv = ["--region", region]
    if name == "fetch" and force:
        stage_argv.append("--force")
    return stage_argv


def _run_stage(name: str, stage_argv: list[str]) -> tuple[int, str, float]:
    """One stage as its own process: its status, everything it printed, and how
    long it took. `python -m pipeline.<stage>` is the documented per-stage
    command, so this is the code path people run by hand and not a second one."""
    began = time.perf_counter()
    done = subprocess.run(
        [sys.executable, "-m", f"pipeline.{name}", *stage_argv],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return done.returncode, done.stdout, time.perf_counter() - began


def run_side_by_side(names: list[str], region: str, force: bool, jobs: int) -> int:
    """`names` with up to `jobs` running at once, each started when the stages
    it `NEEDS` are done. A stage `--from` skipped counts as done: its output is
    on disk, which is what skipping it meant.

    Each stage's log is held until it finishes and printed whole, in the serial
    order — so the log reads as the serial run's does, and a stage's lines are
    never threaded through another's. A failure starts nothing new: what is
    running finishes, and nothing that needed the failed stage ever starts.
    """
    waiting = list(names)
    finished: set[str] = set(STAGES) - set(names)
    results: dict[str, tuple[int, str, float]] = {}
    running: dict[Future[tuple[int, str, float]], str] = {}
    printed = 0
    status = 0

    def report(name: str, heading: str) -> None:
        code, text, took = results[name]
        log.info("")
        log.info("== %s ==", heading)
        if text.strip():
            log.info("%s", text.rstrip())
        if code != 0:
            log.error("%s failed (exit %d); stopping", name, code)
        else:
            log.info("   %s took %.1fs", name, took)

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        while waiting or running:
            if status == 0:
                ready = [name for name in waiting if finished.issuperset(NEEDS[name])]
                for name in ready[: jobs - len(running)]:
                    waiting.remove(name)
                    running[pool.submit(_run_stage, name, _stage_argv(name, region, force))] = name
            if not running:
                break
            for future in wait(running, return_when=FIRST_COMPLETED).done:
                name = running.pop(future)
                results[name] = future.result()
                if results[name][0] == 0:
                    finished.add(name)
                else:
                    status = status or results[name][0]
            while printed < len(names) and names[printed] in results:
                printed += 1
                report(names[printed - 1], f"[{printed}/{len(names)}] {names[printed - 1]}")
    # A stage that finished behind one that never ran: its log is the only
    # trace of work that happened, so it is printed and not dropped.
    for name in names[printed:]:
        if name in results:
            report(name, f"{name} (finished behind a stage that did not run)")
    if status == 0 and waiting:
        # Unreachable while `NEEDS` follows `STAGES`' order, which a test holds
        # it to — and the one way this could report a build it did not do.
        log.error("nothing left could start: %s", ", ".join(waiting))
        return 1
    return status


def run_in_order(names: list[str], region: str, force: bool) -> int:
    """`names` one after another, in this process."""
    for position, name in enumerate(names, start=1):
        log.info("")
        log.info("== [%d/%d] %s ==", position, len(names), name)
        began = time.perf_counter()
        status = STAGES[name](_stage_argv(name, region, force))
        if status != 0:
            # Stopped rather than carried on: every later stage reads what this
            # one writes, so continuing would build the rest of the region from
            # whatever happened to be on disk from the previous run.
            log.error("%s failed (exit %d); stopping", name, status)
            return status
        log.info("   %s took %.1fs", name, time.perf_counter() - began)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline", description=(__doc__ or "").splitlines()[0]
    )
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--from",
        dest="start",
        choices=list(STAGES),
        default=next(iter(STAGES)),
        help="start at this stage, skipping the ones before it",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="passed to fetch: take a fresh snapshot rather than reusing the cache",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="stages to run at once, each as its own process (default 1: the serial run)",
    )
    args = parser.parse_args(argv)
    if args.jobs < 1:
        parser.error("--jobs must be at least 1")

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    order = list(STAGES)
    names = order[order.index(args.start) :]
    if args.force and "fetch" not in names:
        # Refused rather than ignored. `--from roads --force` reads as "rebuild
        # everything from roads, forcefully" and would silently do nothing of
        # the kind — the flag belongs to a stage that is not going to run.
        parser.error(f"--force applies to fetch, which --from {args.start} skips")

    started = time.perf_counter()
    if args.jobs > 1:
        status = run_side_by_side(names, args.region, args.force, args.jobs)
    else:
        status = run_in_order(names, args.region, args.force)
    if status != 0:
        return status

    log.info("")
    log.info("%s complete in %.1fs", args.region, time.perf_counter() - started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
