"""The tramway as lines a tram can run (`P3-4`, `Q176`).

`tramway.py` publishes a bed per run of joined rails: undirected, in the order
the sheets happened to list them, and broken at every junction diamond. This
turns them into directed tracks with successors, the tram stops each one serves
and the stop lines it obeys, so the game's `TramSystem` reads where a tram goes
rather than deriving it. Nothing here is authored by street: the route is the
join's, as `GAME_DESIGN.md` asks.

🔴 **Which way a bed runs is read, never assumed, and a bed nothing speaks for is
refused and counted.** A bed's stored order means nothing — Wan Chai's two longest
parallel beds run the same way. Three witnesses, asked in order, and
`by_witness` says how many each carried:

1. **The other track.** Trams run on the left, so travel has its neighbour on the
   right. This is the double track of the whole main line.
2. **The road beside it.** A single line (Morrison Hill, Wong Nai Chung) has no
   neighbour, and takes the flow of the one-way street it runs down.
3. **The bed it touches.** A fragment through a diamond has neither, and takes the
   way of whichever directed bed it continues.

`against_flow_m` grades the first against the second: a tram on a double track
beside a one-way street runs with that street, so a real flip reads here.

🔴 **A join is a chord the tram crosses, and a jump over a nearer bed is not one.**
Two beds join where one's end stands within `join_m` of the other's start, ahead
of it and within `join_heading_deg` of both. The transitive reduction then drops
every join a shorter chain of joins already makes: a bed's end sees the next bed
and the one past it, and a tram taking the second would skip the first.

🔴 **A line ends only where the region does.** A bed with no way on and an end
inside the rectangle is a stub at a junction's turnout, and a tram sent down it
would vanish in the street; such beds are pruned until every kept end joins or
leaves the region, and `pruned_m` counts what that cost.

The partition closes: `beds` = `kept` + `refused_no_direction` + `pruned`.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import shapely

from pipeline.config import Config, TramLines, load_config
from pipeline.documents import read_document, write_document
from pipeline.fares import FARES_NAME, FARES_SCHEMA
from pipeline.polyline import plan_lengths, plan_projections, plan_steps
from pipeline.roads import ROADGRAPH_NAME, read_graph, resample
from pipeline.signals import (
    SIGNALS_MANIFEST_NAME,
    SIGNALS_MANIFEST_SCHEMA,
    SIGNALS_PLAN_SCHEMA,
)
from pipeline.tramway import TRAMWAY_MANIFEST_NAME, TRAMWAY_MANIFEST_SCHEMA

log = logging.getLogger(__name__)

TRAMLINES_MANIFEST_NAME = "tramlines.json"
TRAMLINES_MANIFEST_SCHEMA = 1
TRAM_LINES_NAME = "tram_lines.json"
TRAM_LINES_SCHEMA = 1

# `fares.json`'s kind a tram stop is published as.
_FARE_TRAM_STOP = "poi"

# The placement layers `in_tram_path` grades, by the document each is read from.
_PATH_LAYERS = {
    "lamps": "lamps_placements.json",
    "railings": "railings_placements.json",
    "signs": "signs_placements.json",
    "trees": "trees_placements.json",
    "signal_heads": "signal_heads_placements.json",
}

# The witnesses, in the order they are asked.
WITNESS_TRACK = "other_track"
WITNESS_ROAD = "one_way_road"
WITNESS_TOUCH = "touching_bed"

# How far a neighbouring station may stand along the track and still be abeam.
_ABEAM_M = 2.5
# How many of a witness's votes must agree: a bed through a diamond sees the other
# track on both sides.
_AGREEMENT = 0.75
# The share of its stations a bed must have the other track abeam at. A single
# line beside a turnout has it for a few metres only.
_ABEAM_SHARE = 0.5
_VOTE_STEP_M = 1.0
# Under this a join is the same point, and has no direction of its own to test.
_SAME_POINT_M = 0.5
# Stations a heading is read across, near either end of a bed.
_HEADING_SPAN_M = 6.0


@dataclass
class TramLinesReport:
    """What the stage read, directed, joined and kept."""

    beds: int = 0
    beds_m: float = 0.0
    kept: int = 0
    kept_m: float = 0.0
    refused_no_direction: int = 0
    refused_m: float = 0.0
    pruned: int = 0
    pruned_m: float = 0.0
    by_witness: dict[str, int] = field(default_factory=dict)
    # Metres of track running against the one-way street nearest it.
    against_flow_m: float = 0.0
    with_flow_m: float = 0.0
    joins: int = 0
    # Joins the reduction dropped, because a chain of shorter ones makes them.
    joins_reduced: int = 0
    forks: int = 0
    longest_join_m: float = 0.0
    open_starts: int = 0
    open_ends: int = 0
    stops_read: int = 0
    stops_bound: int = 0
    stops_no_track: int = 0
    # Stops on the tram's right: a platform is at its door, on the left, so
    # these read as a stop bound to the far track.
    stops_offside: int = 0
    signals_bound: int = 0
    # Staged junctions a kept track passes with no approach its way.
    junctions_unbound: int = 0
    # 🔴 What each placement layer stands inside a tram's swept plan, by layer: a
    # tram draws through them. Reported, not moved: each layer is the publisher's.
    in_tram_path: dict[str, int] = field(default_factory=dict)


@dataclass
class _Track:
    """One bed, in the direction a tram runs it."""

    points: np.ndarray
    source: int
    witness: str
    length_m: float = 0.0
    next: list[int] = field(default_factory=list)
    previous: list[int] = field(default_factory=list)
    open_start: bool = False
    open_end: bool = False
    stops: list[dict[str, Any]] = field(default_factory=list)
    signals: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.length_m = float(plan_steps(self.points).sum())


def end_heading(points: np.ndarray, at_end: bool) -> np.ndarray:
    """The plan unit vector of travel at a line's start or end, across a few
    metres: a bed's last step can be a digitising jitter."""
    plan = points[:, [0, 2]]
    along = plan_lengths(points)
    if at_end:
        row = int(np.searchsorted(along, along[-1] - _HEADING_SPAN_M, side="right")) - 1
        vector = plan[-1] - plan[max(row, 0)]
    else:
        row = int(np.searchsorted(along, _HEADING_SPAN_M))
        vector = plan[min(row, len(plan) - 1)] - plan[0]
    length = float(np.hypot(*vector))
    return vector / length if length > 0.0 else np.array([1.0, 0.0])


def _tangents(plan: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Each station that starts a usable step, its unit vector and its length."""
    steps = np.diff(plan, axis=0)
    lengths = np.hypot(*steps.T)
    usable = lengths > 1e-6
    return plan[:-1][usable], steps[usable] / lengths[usable, None], lengths[usable]


def other_track_votes(beds: list[np.ndarray], spec: TramLines) -> list[tuple[int, int, int]]:
    """For each bed in its stored order, how many stations had another track
    abeam on the left, how many on the right, and how many there were.

    Every metre, not the beds' own stations: `_follow` leaves a flat span its two
    ends, so abeam would otherwise read how the ground lay."""
    plans = [resample(bed[:, [0, 2]], _VOTE_STEP_M) for bed in beds]
    everything = np.concatenate(plans)
    owners = np.concatenate([np.full(len(plan), row) for row, plan in enumerate(plans)])
    votes = []
    for row, plan in enumerate(plans):
        left = right = 0
        stations, units, _ = _tangents(plan)
        for station, unit in zip(stations, units, strict=True):
            offset = everything - station
            distance = np.hypot(*offset.T)
            near = (
                (owners != row)
                & (distance >= spec.separation_min_m)
                & (distance <= spec.separation_max_m)
            )
            if not near.any():
                continue
            found = offset[near]
            along = found @ unit
            abeam = np.abs(along) < _ABEAM_M
            if not abeam.any():
                continue
            # Left of travel in plan, x east and z south.
            leftward = np.array([unit[1], -unit[0]])
            if float((found[abeam] @ leftward).mean()) > 0.0:
                left += 1
            else:
                right += 1
        votes.append((left, right, len(stations)))
    return votes


class _Flow:
    """The level-0 roads, for which way the nearest runs where it runs one way."""

    def __init__(self, edges: list[dict[str, Any]]) -> None:
        starts, units, lengths, one_way = [], [], [], []
        for edge in edges:
            plan = np.asarray(edge["polyline"], dtype=np.float64)[:, [0, 2]]
            if len(plan) < 2:
                continue
            at, unit, length = _tangents(plan)
            starts.append(at)
            units.append(unit)
            lengths.append(length)
            one_way.append(np.full(len(at), edge["direction"] != "both"))
        self.starts = np.concatenate(starts) if starts else np.empty((0, 2))
        self.units = np.concatenate(units) if units else np.empty((0, 2))
        self.lengths = np.concatenate(lengths) if lengths else np.empty(0)
        self.one_way = np.concatenate(one_way) if one_way else np.empty(0, dtype=bool)

    def at(self, station: np.ndarray, reach_m: float) -> np.ndarray | None:
        """The flow of the road nearest `station`, or None where the nearest is
        two-way or further than `reach_m`."""
        if not len(self.starts):
            return None
        offset = station - self.starts
        along = np.clip((offset * self.units).sum(axis=1), 0.0, self.lengths)
        feet = self.starts + self.units * along[:, None]
        distance = np.hypot(*(station - feet).T)
        nearest = int(np.argmin(distance))
        if distance[nearest] > reach_m or not self.one_way[nearest]:
            return None
        return self.units[nearest]


def flow_votes(plan: np.ndarray, flow: _Flow, reach_m: float) -> tuple[float, float]:
    """Metres of `plan`, in its stored order, with and against the road beside."""
    stations, units, steps = _tangents(plan)
    with_flow = against = 0.0
    for station, unit, step in zip(stations, units, steps, strict=True):
        road = flow.at(station, reach_m)
        if road is None:
            continue
        if float(road @ unit) >= 0.0:
            with_flow += float(step)
        else:
            against += float(step)
    return with_flow, against


def _decided(votes: tuple[float, float], at_least: float) -> int:
    """+1 where the first count carries it, -1 the second, 0 where neither does."""
    first, second = votes
    total = first + second
    if total <= 0.0 or total < at_least or max(first, second) < _AGREEMENT * total:
        return 0
    return 1 if first > second else -1


def _continues(first: np.ndarray, second: np.ndarray, limit: float, reach_m: float) -> float | None:
    """The chord from the end of `first` to the start of `second`, where one runs
    on into the other: within `reach_m`, ahead of the one and behind the other, the
    three headings within `limit` (a cosine). The chord's own heading is what keeps
    the other track out: its bed's end stands 2.6 m off, abeam, and parallel."""
    chord = second[0, [0, 2]] - first[-1, [0, 2]]
    gap = float(np.hypot(*chord))
    if gap > reach_m:
        return None
    leaving = end_heading(first, True)
    entering = end_heading(second, False)
    if float(leaving @ entering) <= limit:
        return None
    if gap > _SAME_POINT_M:
        unit = chord / gap
        if float(unit @ leaving) <= limit or float(unit @ entering) <= limit:
            return None
    return gap


def _way_from_touch(
    row: int, beds: list[np.ndarray], ways: list[int], limit: float, touch_m: float
) -> int:
    """The way bed `row` runs on from the nearest bed already decided, or 0."""
    best: tuple[float, int] | None = None
    for way in (1, -1):
        mine = _oriented(beds[row], way)
        for other, other_way in enumerate(ways):
            if not other_way:
                continue
            theirs = _oriented(beds[other], other_way)
            for first, second in ((mine, theirs), (theirs, mine)):
                gap = _continues(first, second, limit, touch_m)
                if gap is not None and (best is None or gap < best[0]):
                    best = (gap, way)
    return 0 if best is None else best[1]


def _oriented(bed: np.ndarray, way: int) -> np.ndarray:
    return bed if way > 0 else bed[::-1]


def direct_beds(
    beds: list[np.ndarray], flow: _Flow, spec: TramLines, report: TramLinesReport
) -> list[_Track]:
    """Every bed a witness speaks for, as a track in its running direction."""
    ways = [0] * len(beds)
    witnesses = [""] * len(beds)
    for row, (left, right, stations) in enumerate(other_track_votes(beds, spec)):
        # 🔴 A fragment is not asked: a turnout's curve has the main line beside it
        # on the wrong side, and read as double track it ran into its own junction
        # and cost the Happy Valley branch. It takes its way from what it continues.
        if float(plan_steps(beds[row]).sum()) < spec.min_flow_m:
            continue
        # Trams run on the left: the other track is on the right of travel.
        way = _decided((right, left), _ABEAM_SHARE * stations)
        if way:
            ways[row] = way
            witnesses[row] = WITNESS_TRACK
    for row, bed in enumerate(beds):
        if ways[row]:
            continue
        way = _decided(flow_votes(bed[:, [0, 2]], flow, spec.flow_reach_m), spec.min_flow_m)
        if way:
            ways[row] = way
            witnesses[row] = WITNESS_ROAD

    limit = math.cos(math.radians(spec.join_heading_deg))
    changed = True
    while changed:
        changed = False
        for row in range(len(beds)):
            if ways[row]:
                continue
            ways[row] = _way_from_touch(row, beds, ways, limit, spec.touch_m)
            if ways[row]:
                witnesses[row] = WITNESS_TOUCH
                changed = True

    tracks = []
    for row, way in enumerate(ways):
        if not way:
            report.refused_no_direction += 1
            report.refused_m += float(plan_steps(beds[row]).sum())
            continue
        report.by_witness[witnesses[row]] = report.by_witness.get(witnesses[row], 0) + 1
        tracks.append(_Track(_oriented(beds[row], way), row, witnesses[row]))
    return tracks


def join_tracks(tracks: list[_Track], spec: TramLines, report: TramLinesReport) -> None:
    """Fill every track's `next` and `previous`: the chords a tram may cross."""
    limit = math.cos(math.radians(spec.join_heading_deg))
    candidates: dict[int, list[tuple[float, int]]] = {row: [] for row in range(len(tracks))}
    for row, track in enumerate(tracks):
        for other, into in enumerate(tracks):
            if other == row:
                continue
            gap = _continues(track.points, into.points, limit, spec.join_m)
            if gap is not None:
                candidates[row].append((gap, other))

    def chained(start: int, goal: int) -> bool:
        """Whether `goal` is reached from `start` other than by its direct join."""
        seen = {start}
        frontier = [other for _, other in candidates[start] if other != goal]
        while frontier:
            at = frontier.pop()
            if at == goal:
                return True
            if at in seen:
                continue
            seen.add(at)
            frontier.extend(other for _, other in candidates[at])
        return False

    for row, joins in candidates.items():
        for _gap, other in sorted(joins):
            if chained(row, other):
                report.joins_reduced += 1
                continue
            tracks[row].next.append(other)
            tracks[other].previous.append(row)


def _is_open(point: np.ndarray, high: tuple[float, float], open_end_m: float) -> bool:
    """Whether a plan point stands on the region's rectangle."""
    x, z = float(point[0]), float(point[1])
    return (
        x <= open_end_m or z <= open_end_m or x >= high[0] - open_end_m or z >= high[1] - open_end_m
    )


def prune_stubs(
    tracks: list[_Track], high: tuple[float, float], spec: TramLines, report: TramLinesReport
) -> list[_Track]:
    """The tracks left once every end joins on or leaves the region, renumbered."""
    alive = set(range(len(tracks)))
    changed = True
    while changed:
        changed = False
        for row in sorted(alive):
            track = tracks[row]
            leaves = _is_open(track.points[-1, [0, 2]], high, spec.open_end_m) or any(
                other in alive for other in track.next
            )
            enters = _is_open(track.points[0, [0, 2]], high, spec.open_end_m) or any(
                other in alive for other in track.previous
            )
            if not (leaves and enters):
                alive.discard(row)
                report.pruned += 1
                report.pruned_m += track.length_m
                changed = True
    numbering = {old: new for new, old in enumerate(sorted(alive))}
    kept = []
    for old in sorted(alive):
        track = tracks[old]
        track.next = [numbering[other] for other in track.next if other in alive]
        track.previous = [numbering[other] for other in track.previous if other in alive]
        # 🔴 Open only with nothing to run on to: a bed near the line that joins the
        # next one is not leaving, and would be a tram vanishing 10 m in.
        track.open_end = not track.next
        track.open_start = not track.previous
        kept.append(track)
    return kept


def _foot_on(plan: np.ndarray, along: np.ndarray, point: np.ndarray) -> tuple[float, float, float]:
    """The nearest place on a polyline to `point`: metres off it, metres along
    it, and the signed side (+ left of travel)."""
    steps = np.diff(plan, axis=0)
    fraction, distance = plan_projections(point, plan[:-1], steps)
    row = int(np.argmin(distance))
    length = float(np.hypot(*steps[row]))
    t = float(np.clip(fraction[row], 0.0, 1.0))
    offset = point - (plan[row] + steps[row] * t)
    side = (
        0.0
        if length <= 0.0
        else float(offset[0] * steps[row, 1] - offset[1] * steps[row, 0]) / length
    )
    return float(distance[row]), float(along[row]) + t * length, side


def bind_stops(
    tracks: list[_Track],
    stops: list[dict[str, Any]],
    spec: TramLines,
    report: TramLinesReport,
) -> None:
    """Each published tram stop onto the track nearest it, the one it serves."""
    frames = [(track.points[:, [0, 2]], plan_lengths(track.points)) for track in tracks]
    for stop in stops:
        report.stops_read += 1
        x, _, z = stop["pos"]
        point = np.array([float(x), float(z)])
        best: tuple[float, int, float, float] | None = None
        for row, (plan, along) in enumerate(frames):
            distance, at_m, side = _foot_on(plan, along, point)
            if best is None or distance < best[0]:
                best = (distance, row, at_m, side)
        if best is None or best[0] > spec.stop_max_track_m:
            report.stops_no_track += 1
            continue
        report.stops_bound += 1
        if best[3] < 0.0:
            report.stops_offside += 1
        tracks[best[1]].stops.append({"id": stop["id"], "s_m": round(best[2], 3)})
    for track in tracks:
        track.stops.sort(key=lambda stop: stop["s_m"])


def _approach_stop(edge: dict[str, Any], approach: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    """An approach's stop point in plan and its unit vector of travel."""
    points = np.asarray(edge["polyline"], dtype=np.float64)
    along = plan_lengths(points)
    stop_m = float(approach["stop_m"])
    x = float(np.interp(stop_m, along, points[:, 0]))
    z = float(np.interp(stop_m, along, points[:, 2]))
    heading = math.radians(float(approach["heading_deg"]))
    return np.array([x, z]), np.array([math.sin(heading), -math.cos(heading)])


def _paths_of(track: _Track, tracks: list[_Track]) -> list[tuple[float, np.ndarray]]:
    """The track's plan, then a chord to each track it joins, each with the metres
    along the track it starts at: a stop line can stand in the gap a diamond leaves
    between two beds."""
    plan = track.points[:, [0, 2]]
    chords = (np.vstack([plan[-1], tracks[row].points[0, [0, 2]]]) for row in track.next)
    return [(0.0, plan), *((track.length_m, chord) for chord in chords)]


def _crossing(
    paths: list[tuple[float, np.ndarray]],
    stop: np.ndarray,
    travel: np.ndarray,
    limit: float,
    reach_m: float,
) -> tuple[float, float] | None:
    """Metres off the stop point and along the track of the nearest place `paths`
    cross the stop line's plane going its way, or None."""
    best: tuple[float, float] | None = None
    for start_m, path in paths:
        ahead = (path - stop) @ travel
        steps = np.diff(path, axis=0)
        lengths = np.hypot(*steps.T)
        for row in np.flatnonzero((ahead[:-1] < 0.0) & (ahead[1:] >= 0.0)):
            if lengths[row] < 1e-6 or float(steps[row] @ travel) / lengths[row] < limit:
                continue
            u = -float(ahead[row]) / float(ahead[row + 1] - ahead[row])
            lateral = float(np.hypot(*(path[row] + steps[row] * u - stop)))
            if lateral <= reach_m and (best is None or lateral < best[0]):
                best = (lateral, start_m + float(lengths[:row].sum()) + u * float(lengths[row]))
    return best


def bind_signals(
    tracks: list[_Track],
    plan_document: dict[str, Any],
    edges: dict[int, dict[str, Any]],
    spec: TramLines,
    report: TramLinesReport,
) -> None:
    """Where each track crosses a stop line its way.

    🔴 **The line is wider than the road's own** (`StopLine.half_m` is the
    published width): `Q58`'s reserve runs between two carriageways, so a rail
    sits a median 3.26 m past the drawn kerb and the car's line would miss it. A
    track crosses the plane through the stop point, within `signal_reach_m` of it,
    within `signal_heading_deg` of the approach's travel.
    """
    limit = math.cos(math.radians(spec.signal_heading_deg))
    paths = [_paths_of(track, tracks) for track in tracks]
    for junction in plan_document.get("junctions", ()):
        centre = np.asarray(junction["pos"], dtype=np.float64)[[0, 2]]
        lines = [
            (approach, *_approach_stop(edges[int(approach["edge"])], approach))
            for approach in junction["approaches"]
            if int(approach["edge"]) in edges
        ]
        passed = False
        bound = False
        for track, track_paths in zip(tracks, paths, strict=True):
            if not any(
                float(np.hypot(*(path - centre).T).min()) <= spec.signal_reach_m
                for _, path in track_paths
            ):
                continue
            passed = True
            best: tuple[float, float, dict[str, Any]] | None = None
            for approach, stop, travel in lines:
                hit = _crossing(track_paths, stop, travel, limit, spec.signal_reach_m)
                if hit is not None and (best is None or hit[0] < best[0]):
                    best = (*hit, approach)
            if best is None:
                continue
            bound = True
            report.signals_bound += 1
            track.signals.append(
                {
                    "edge": int(best[2]["edge"]),
                    "along": bool(best[2]["along"]),
                    "s_m": round(best[1], 3),
                }
            )
        if passed and not bound:
            report.junctions_unbound += 1
    for track in tracks:
        track.signals.sort(key=lambda signal: signal["s_m"])


def build_lines(
    beds: list[np.ndarray],
    edges: list[dict[str, Any]],
    stops: list[dict[str, Any]],
    plan_document: dict[str, Any],
    high: tuple[float, float],
    spec: TramLines,
    report: TramLinesReport,
) -> list[_Track]:
    """The kept tracks of a region's beds: the stage without its files."""
    report.beds = len(beds)
    report.beds_m = float(sum(plan_steps(bed).sum() for bed in beds))
    level0 = [edge for edge in edges if int(edge["elevation_level"]) == 0]
    flow = _Flow(level0)
    tracks = direct_beds(beds, flow, spec, report)
    join_tracks(tracks, spec, report)
    tracks = prune_stubs(tracks, high, spec, report)
    report.kept = len(tracks)
    report.kept_m = float(sum(track.length_m for track in tracks))
    for track in tracks:
        with_flow, against = flow_votes(track.points[:, [0, 2]], flow, spec.flow_reach_m)
        report.with_flow_m += with_flow
        report.against_flow_m += against
        report.joins += len(track.next)
        report.forks += len(track.next) > 1
        report.open_starts += track.open_start
        report.open_ends += track.open_end
        for row in track.next:
            gap = float(np.hypot(*(track.points[-1, [0, 2]] - tracks[row].points[0, [0, 2]])))
            report.longest_join_m = max(report.longest_join_m, gap)
    bind_stops(tracks, stops, spec, report)
    bind_signals(tracks, plan_document, {int(edge["id"]): edge for edge in edges}, spec, report)
    return tracks


def tram_path(plans: list[np.ndarray], half_width_m: float) -> shapely.Geometry:
    """The prepared plan a tram sweeps down these `(x, z)` lines."""
    path = shapely.union_all([shapely.LineString(plan).buffer(half_width_m) for plan in plans])
    shapely.prepare(path)
    return path


def count_in_path(
    tracks: list[_Track], half_width_m: float, out_dir: Path, report: TramLinesReport
) -> None:
    """Fill `in_tram_path` from whichever placement documents the region built."""
    if not tracks:
        return
    path = tram_path([track.points[:, [0, 2]] for track in tracks], half_width_m)
    for layer, name in _PATH_LAYERS.items():
        document = out_dir / name
        if not document.exists():
            continue
        placements = json.loads(document.read_text()).get("placements", ())
        at = np.array([entry["transform"]["pos"] for entry in placements]).reshape(-1, 3)
        report.in_tram_path[layer] = int(shapely.contains_xy(path, at[:, 0], at[:, 2]).sum())


def build_region(
    city: Config,
    region_id: str,
    *,
    out_root: Path | None = None,
) -> TramLinesReport:
    """Read the region's beds and write its `tram_lines.json`."""
    report = TramLinesReport()
    out_dir = city.out_dir(region_id, out_root)
    tracks: list[_Track] = []
    if city.tramway is not None:
        rebuild = f"python -m pipeline --region {region_id}"
        tramway = read_document(
            out_dir / TRAMWAY_MANIFEST_NAME, TRAMWAY_MANIFEST_SCHEMA, "python -m pipeline.tramway"
        )
        fares = read_document(out_dir / FARES_NAME, FARES_SCHEMA, rebuild)
        signals = read_document(out_dir / SIGNALS_MANIFEST_NAME, SIGNALS_MANIFEST_SCHEMA, rebuild)
        plan_document: dict[str, Any] = {}
        if signals.get("plan_document"):
            plan_document = read_document(
                out_dir / str(signals["plan_document"]), SIGNALS_PLAN_SCHEMA, rebuild
            )
        graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
        tracks = build_lines(
            [np.asarray(line, dtype=np.float64) for line in tramway.get("track_lines", ())],
            list(graph["edges"]),
            [node for node in fares.get("nodes", ()) if node["kind"] == _FARE_TRAM_STOP],
            plan_document,
            city.region_high(region_id),
            city.tramway.lines,
            report,
        )
        count_in_path(tracks, city.tramway.lines.tram_path_m, out_dir, report)
    if tracks:
        write_document(
            out_dir / TRAM_LINES_NAME,
            {
                "schema_version": TRAM_LINES_SCHEMA,
                "city_id": city.id,
                "region_id": region_id,
                "tracks": [
                    {
                        "id": row,
                        "points": [[round(float(v), 3) for v in point] for point in track.points],
                        "next": track.next,
                        "open_start": track.open_start,
                        "open_end": track.open_end,
                        "stops": track.stops,
                        "signals": track.signals,
                    }
                    for row, track in enumerate(tracks)
                ],
            },
        )
    _write_manifest(out_dir, city, region_id, report, bool(tracks))
    return report


def _write_manifest(
    out_dir: Path, city: Config, region_id: str, report: TramLinesReport, wrote: bool
) -> None:
    write_document(
        out_dir / TRAMLINES_MANIFEST_NAME,
        {
            "schema_version": TRAMLINES_MANIFEST_SCHEMA,
            "city_id": city.id,
            "region_id": region_id,
            "document": TRAM_LINES_NAME if wrote else None,
            "beds": report.beds,
            "beds_m": round(report.beds_m, 3),
            "kept": report.kept,
            "kept_m": round(report.kept_m, 3),
            "refused_no_direction": report.refused_no_direction,
            "refused_m": round(report.refused_m, 3),
            "pruned": report.pruned,
            "pruned_m": round(report.pruned_m, 3),
            "by_witness": report.by_witness,
            "with_flow_m": round(report.with_flow_m, 3),
            "against_flow_m": round(report.against_flow_m, 3),
            "joins": report.joins,
            "joins_reduced": report.joins_reduced,
            "forks": report.forks,
            "longest_join_m": round(report.longest_join_m, 3),
            "open_starts": report.open_starts,
            "open_ends": report.open_ends,
            "stops_read": report.stops_read,
            "stops_bound": report.stops_bound,
            "stops_no_track": report.stops_no_track,
            "stops_offside": report.stops_offside,
            "signals_bound": report.signals_bound,
            "junctions_unbound": report.junctions_unbound,
            "in_tram_path": report.in_tram_path,
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_config()
    report = build_region(city, args.region, out_root=args.out_root)
    log.info(
        "tramlines: %d beds -> %d kept (%.0f m), %d refused, %d pruned (%.0f m); by %s; "
        "%.0f m with the street, %.0f against; %d joins (%d forks, longest %.1f m, %d reduced); "
        "%d open starts, %d open ends; stops %d of %d (%d offside); "
        "%d signals, %d junctions unbound; in a tram's path %s",
        report.beds,
        report.kept,
        report.kept_m,
        report.refused_no_direction,
        report.pruned,
        report.pruned_m,
        report.by_witness,
        report.with_flow_m,
        report.against_flow_m,
        report.joins,
        report.forks,
        report.longest_join_m,
        report.joins_reduced,
        report.open_starts,
        report.open_ends,
        report.stops_bound,
        report.stops_read,
        report.stops_offside,
        report.signals_bound,
        report.junctions_unbound,
        report.in_tram_path,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
