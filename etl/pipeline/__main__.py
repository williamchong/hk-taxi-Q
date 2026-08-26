"""The whole pipeline, in order (`P1-6`).

    python -m pipeline --city hong_kong --region wan_chai

Runs each stage by calling its own `main`, with the same arguments the
documented per-stage command would pass. That is deliberate rather than
convenient: composing the stages any other way — importing `build_region`
directly, say — would create a second code path whose behaviour could drift
from the one people actually run, and the drift would show up as a full build
that quietly differs from a partial one.

Ordering is a real dependency chain, not a preference. `surface` reads the
graph `roads` writes, `clearance` measures the ribbon `surface` drew against the
tiles `buildings` wrote, `fares` snaps to the graph, `tramway` takes its heights
from it, and `export` reconciles them.
Only `buildings` is independent, and it runs early because it is by far the
longest stage — a mistake in it is worth hitting before the quick ones.

`fetch` is the only stage that touches the network, and it is a cache hit after
the first run. `--from` skips ahead when you already have what it would fetch.
"""

from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Callable

from pipeline import (
    arrows,
    boxjunctions,
    buildings,
    clearance,
    export,
    fares,
    fetch,
    lamps,
    landmarks,
    podiums,
    railings,
    roadmarks,
    roads,
    signals,
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
    "buildings": buildings.main,
    "landmarks": landmarks.main,
    "roads": roads.main,
    "surface": surface.main,
    # After `surface` because it measures the ribbon that stage drew, and before
    # `export` because `city.json` carries the result. It reads the building
    # tiles too, which is why it cannot run any earlier than this.
    "clearance": clearance.main,
    "fares": fares.main,
    # After `roads` because every rail takes its height from the nearest level-0
    # centreline that stage published, and before `export` because `city.json`
    # names the asset. It reads no tile and measures no ribbon, so it could sit
    # anywhere between those two; it is here because that is where its output is
    # wanted rather than because anything forces it.
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
    # `signs` all have, and for `signs`' reason exactly: a published signal head
    # is registered onto the kerb the ribbon actually drew, because 72.7% of them
    # are surveyed inside the 1.6x ribbon and drawn where published nearly three
    # quarters of the city's signals stand in the road. It needs `roads` for the
    # level-0 centrelines that give it a host edge, a height and the kerb side
    # that resolves its facing. Before `export`, which names the asset.
    "signals": signals.main,
    # After `surface` and `roads`, the dependency `arrows`, `railings`, `signs`
    # and `signals` all have, and for `signs`' reason exactly: a published lamp
    # post is registered onto the kerb the ribbon actually drew, because 64.1% of
    # them are surveyed inside the 1.6x ribbon and drawn where published four
    # fifths of a kilometre of the region's columns stand in the carriageway. It
    # needs `roads` for the level-0 centrelines that give it a host edge, a deck
    # height and the kerb side its arm reaches away from. Before `export`, which
    # names the asset.
    "lamps": lamps.main,
    "export": export.main,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m pipeline", description=(__doc__ or "").splitlines()[0]
    )
    parser.add_argument("--city", required=True)
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
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    order = list(STAGES)
    names = order[order.index(args.start) :]
    if args.force and "fetch" not in names:
        # Refused rather than ignored. `--from roads --force` reads as "rebuild
        # everything from roads, forcefully" and would silently do nothing of
        # the kind — the flag belongs to a stage that is not going to run.
        parser.error(f"--force applies to fetch, which --from {args.start} skips")

    started = time.perf_counter()
    for position, name in enumerate(names, start=1):
        stage_argv = ["--city", args.city, "--region", args.region]
        if name == "fetch" and args.force:
            stage_argv.append("--force")

        log.info("")
        log.info("== [%d/%d] %s ==", position, len(names), name)
        began = time.perf_counter()
        status = STAGES[name](stage_argv)
        if status != 0:
            # Stopped rather than carried on: every later stage reads what this
            # one writes, so continuing would build the rest of the region from
            # whatever happened to be on disk from the previous run.
            log.error("%s failed (exit %d); stopping", name, status)
            return status
        log.info("   %s took %.1fs", name, time.perf_counter() - began)

    log.info("")
    log.info("%s / %s complete in %.1fs", args.city, args.region, time.perf_counter() - started)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
