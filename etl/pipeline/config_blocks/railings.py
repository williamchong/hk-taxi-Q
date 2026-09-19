"""`railings:`.

One of `pipeline.config`'s blocks (`P3-35f`, `Q133`) — moved whole, and imported
through `pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import LayerSpec, _measures, _require, _spec_header


@dataclass(frozen=True)
class RailingClass:
    """One kind of street furniture in the railing layer (`P3-19`, `Q61`).

    ⚠️ **A class is a claim about *what a code is*, and it is the only kind of
    claim this layer supports.** `Q60` established that `LINETYPE` has no
    published domain, and the symbology correction closed the last door: the
    layer's other 40 columns are cartography — `SYMBOL_SIZE_*` is the spec's own
    *"symbol size of marker symbol"* in inches on paper, `COLOR` is an undomained
    pen index, `LINE_WIDTH_*` is null throughout. So nothing published says what
    any of these things look like.

    What follows is the shape of this table. It splits the layer by **class of
    object** — a fence, a post, a vehicle restraint — on the strength of the code
    strings, which is the argument `drawn_line_types` was already making for one
    class and is now making for three. It does **not** split within a class: all
    five fence codes draw one fence, because nothing says `CRAIL1` differs from
    `HCAIL2` and `Q54` debits exactly that invention.

    ⚠️ **Every dimension here is authored, and the run parameters are per class
    because the region forces it, not for symmetry.** Bollard features have a
    median published length of **1.00 m** and 84% are under 4 m; the fence's
    `min_run_m` of 4.0 would refuse essentially all of them and report it as a
    clean run of short-run refusals. A shared value would have been a silent
    decision to draw no bollards.
    """

    # The class's own name, and the mesh and glTF material name it draws into.
    # One string for all three, because they are the same identity: the engine
    # dispatches a material by name (`tools/generated_scene_import.gd`) and the
    # graders find a class's geometry by mesh name.
    id: str
    # Which published `LINETYPE` values this class admits. ⚠️ Still a whitelist
    # and **not** a type map — see the class docstring. Disjoint across classes,
    # checked at load: a code in two classes would be drawn twice, in two
    # places, and both would look right.
    line_types: tuple[str, ...]
    # `kerbside`'s run parameters, per class. A break shorter than this is not a
    # break and a run shorter than `min_run_m` is not a fence — but what counts
    # as "shorter" depends on what is being drawn, which is the warning above.
    bridge_gap_m: float
    min_run_m: float
    # Pitch the drawn geometry is stationed at along the kerb. Every station
    # takes its height from the ribbon, so this is what lets a run follow the
    # camber of a street instead of chording across it.
    station_m: float
    # ⚠️ **Authored**, like everything else here. A pedestrian railing stands
    # about waist-to-chest; a bollard is shorter; a vehicle barrier is lower
    # again and heavier.
    height_m: float
    # How far the foot is sunk below the ribbon it stands on. The kerb is
    # flattened for mountability (`GAME_DESIGN.md`) and the ground beside it is
    # a separate decimated surface, so anything planted exactly at the road's
    # own height shows daylight under it.
    base_sink_m: float
    # How far outside the drawn carriageway edge this class stands. The kerb
    # strip `roads.surface.kerb_width_m` draws is what it stands behind.
    outset_m: float
    # 🔴 **The width of the one panel this class is tiled from (`P5-5`,
    # `Q115`).** A run is `n` rigid copies of a unit `panel_m` long, stood end
    # to end along the fence line, and never a panel stretched — so a run's
    # ends snap to a panel multiple and the residual is published as
    # `metres_snapped`. ⚠️ **This is the post pitch in the class's `.tres`**:
    # the shader draws a post at `u = 0` and `u = panel_m`, so a joint between
    # two panels falls under a post and the baluster rhythm restarts behind it.
    # `tests/test_railings.py` binds the two, because a joint that landed
    # between posts would show as a seam in every picket in the region.
    panel_m: float
    # ⚠️ **AUTHORED, like every other dimension here, and it exists because a
    # driver refuted the alternative** (`Q112`). The layer shipped one quad per
    # station on the argument that two would be "twice the triangles for a
    # surface 40 mm thick, which buys nothing a driver can see" — and seen along
    # its own length a zero-thickness sheet covers less than a pixel, the
    # coverage shader dissolves the balusters into a uniform alpha, and the
    # fence is simply not there. `Q58`'s failure-to-nothing on the layer whose
    # whole job is to be a visible edge.
    #
    # ⚠️ **Extruded OUTWARD only**, away from the carriageway, so the road-side
    # face keeps the exact position `_station` registered: `outset_m` still
    # means what it says and no thickness can push steel toward the traffic.
    # `Q78`'s one-way-correction rule, at a second layer.
    thickness_m: float


@dataclass(frozen=True)
class Railings(LayerSpec):
    """Published pedestrian railings, drawn by `pipeline/railings.py` (`P3-19`).

    ⚠️ **This block asserts more than any other in this file, and the reason is
    that the publisher asserts less.** `DTAD_RAILING_LINE`'s `LINETYPE` domain
    is **not published**: the fgdb data specification gives the column only the
    description "Line Type", and the index-plan set that defines every `RM`
    marking code and every `TS` sign — including both "Miscellaneous Details"
    sheets — carries no railing sheet at all. So there is no `Q59` transcription
    available here, and every dimension below is **authored**, declared as
    authored, rather than read.

    What follows from that is the shape of `classes`: the layer is split by
    **class of object** — fence, bollard, vehicle restraint — on the strength of
    the code strings, and **never within a class**. All five fence codes draw
    one fence: this block does not claim that `CRAIL1` is a different railing
    from `HCAIL2`, because nothing published says so and `Q54` debits exactly
    that kind of invention. `drawn_line_types` is derived from the table rather
    than authored beside it, so a code cannot be admitted and then belong to no
    class.

    ⚠️ **The join is shared and everything below it is not.** `sample_m`,
    `max_offset_m` and `max_shift_m` are one join onto one set of kerbs, so they
    live here. The run parameters and every dimension live on the class, and
    that is measured rather than tidy: bollard features have a median published
    length of **1.00 m** and 84% are under 4 m, so the fence's `min_run_m` of
    4.0 refuses all but a handful of them. Shared, it would have been a silent
    decision to draw no bollards at all.

    ⚠️ **The position is registered, not read, and that is this block's real
    debt.** `Q59`'s widening puts the drawn kerb a median 0.9 m *outside* the
    surveyed railing line, so **67.9% of the region's railing metres fall inside
    the drawn ribbon** — drawn where surveyed, the signature Hong Kong railing
    is a picket fence down the middle of the drivable surface. So the
    longitudinal extent is read and never stretched, and the lateral offset is
    a rigid move onto the kerb the ETL itself drew. `max_shift_m` is the bar on
    that move and `railings.json` publishes the whole distribution, because a
    move nobody measures is an invention nobody can see.

    ⚠️ **There is no material here, and its absence is the decision** — the
    paragraph `Arrows` and `BoxJunctions` both carry. The colours are authored
    in `game/tuning/railings.tres`, `bollards.tres` and `barriers.tres`; what
    travels from here is each class's `id`, which is also its mesh name and the
    glTF material name the engine dispatches on.
    """

    # Pitch the source lines are sampled at before being assigned to an edge and
    # a side. `kerbside.resample`'s parameter, and the cell size the same
    # stage's dedupe works in: two features drawn along one kerb collapse into
    # one run rather than counting twice, which this layer needs more than
    # `NSR` did — the region publishes 1,763 parts with a median length of
    # 4.6 m for what a driver sees as a few dozen fences.
    sample_m: float
    # Furthest a sample may sit from a level-0 centreline and still be assigned
    # to it. Beyond it the sample is unassigned and counted: a railing round a
    # plaza or along a footbridge belongs to no kerb, and putting it on the
    # nearest one is how a fence ends up across a street it was never on.
    max_offset_m: float
    # ⚠️ **The bar on the registration, and the number this stage exists to be
    # honest about.** How far a run may be moved sideways to reach the drawn
    # kerb before it is refused instead. Measured over the region before it was
    # chosen: half the railing metres move under 2 m, two-thirds under 3 m, and
    # 18% would move more than 5 m — those are railings that are not kerb
    # railings at all, and drawing them would be inventing a fence rather than
    # relocating one.
    max_shift_m: float
    # 🔴 **Two stations closer together than this are one place, not a panel**
    # (`Q112`). `railings._station` interpolates in the *centreline's*
    # parameter, so a duplicated ribbon vertex puts two stations at one point
    # carrying two different facings; as a sheet that quad had no area and the
    # collapse bar deleted it, and as a slab the two facings pull its far rail
    # apart and it becomes a panel across the fence. Measured over the region:
    # 19 steps at exactly zero, **27 under a millimetre and the same 27 under a
    # centimetre**, then 28 at 5 cm — so the value below sits on a plateau
    # rather than on a slope.
    min_station_gap_m: float
    # ⚠️ **A joint between two panels whose axes differ by more than this is a
    # BEND, counted per class as `bends` (`P5-5`).** A rigid panel cannot follow
    # a curve, so at every joint the two far faces open a wedge of
    # `2 x thickness x tan(angle / 2)` — published whole as `joint_gap_m` — and
    # this names the joints where that wedge is a gap rather than a seam. A bar
    # on reporting, never on drawing: no panel is stretched or turned to close
    # one, because that would be a fence the survey did not publish (`Q54`).
    bend_report_deg: float
    # 🔴 **Where the offset rail has doubled back on its own centreline**
    # (`Q112`), as the angle between a step on the fence line and the centreline
    # chord over the same parameter span. On the inside of a tight bend the two
    # part company: `e530`'s CRAIL2 steps 0.44 m along the rail while spanning
    # 1.97 m of centreline at **78 degrees** to it, and there the direction to
    # the centreline runs *along* the fence rather than across it.
    #
    # ⚠️ **Deliberately not a squareness bar.** Squareness is `facing_away`'s own
    # predicate, and a repair keyed on it makes that counter read 0 by
    # construction — `Q58`'s trap, and the reason `Q112` refused two cheaper
    # fixes. This is a property of the two published lines instead, and the two
    # orderings genuinely differ.
    #
    # Measured over the region: p50 **0.00**, p99 2.65, max 78.19 degrees, with
    # 4 steps of 5,532 over 30 degrees and 3 over 45-60. A plateau, which is
    # what `Q72` asked of a rule with one free value.
    fold_tolerance_deg: float
    # ⚠️ **What this layer is split into, and the only claim it supports.** One
    # entry per class of object — see `RailingClass`. The join above is shared
    # because it is one join onto one set of kerbs; everything below the join is
    # per class, because a bollard is not a short fence.
    classes: tuple[RailingClass, ...]

    @property
    def drawn_line_types(self) -> tuple[str, ...]:
        """Every `LINETYPE` any class admits.

        Derived rather than authored, so a code cannot be admitted by the
        whitelist and then belong to no class — which would read as a feature
        that was drawn and then silently vanished.
        """
        return tuple(code for klass in self.classes for code in klass.line_types)

    def class_of(self, line_type: str) -> RailingClass | None:
        """The class admitting `line_type`, or None where none does.

        Linear over three entries. An index would be faster and would have to be
        kept in step with `classes`, which is a second source of truth for no
        measurable gain at this size.
        """
        for klass in self.classes:
            if line_type in klass.line_types:
                return klass
        return None


_RAILING_ROLES = ("line_type", "level")


def _railings(body: Any, where: str) -> Railings | None:
    """The optional published-railing block (`P3-19`, `Q60`).

    Absent, the region ships no `railings.glb` and the manifest names none —
    the shape `tramway`, `arrows` and `boxjunctions` all take. What is *not*
    offered is a fallback that runs a fence down every kerb: this region's
    published railings cover 20.3 km against 57.1 km of *drawn* kerb (90.2 km
    of kerb line, less the 33.1 km buried under a neighbouring ribbon), and a
    derived railing would be a wall along streets that have none.
    """
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    measures = _measures(
        body,
        where,
        (
            "sample_m",
            "max_offset_m",
            "max_shift_m",
            "min_station_gap_m",
            "fold_tolerance_deg",
            "bend_report_deg",
        ),
        positive=True,
    )
    if measures["bend_report_deg"] >= 90.0:
        # Two panels square to each other are a corner, not a bend; a bar at or
        # past it would count no joint in any region and read as a clean sweep.
        raise ValueError(
            f"{where}:bend_report_deg is {measures['bend_report_deg']}; at 90 or more no joint "
            f"can be a bend, and the counter reads 0 by construction"
        )
    if measures["fold_tolerance_deg"] >= 90.0:
        # At 90 a step running square across its own centreline is inside the
        # bar, which is exactly the state the bar exists to name; past it the
        # rule admits a rail running backwards. `road_marks`'s
        # `bearing_tolerance_deg` refuses its own degenerate value for the same
        # shape of reason.
        raise ValueError(
            f"{where}:fold_tolerance_deg is {measures['fold_tolerance_deg']}; at 90 or more a step "
            f"square across its own centreline is admitted, which is the fold it must catch"
        )

    raw_classes = _require(body, "classes", where)
    if isinstance(raw_classes, str) or not isinstance(raw_classes, (list, tuple)):
        raise ValueError(f"{where}:classes must be a list, got {raw_classes!r}")
    if not raw_classes:
        # A table with no entries admits nothing, which is what omitting the
        # block already does — refused so the difference is a decision, not a
        # typo.
        raise ValueError(f"{where}:classes is empty; a block that draws nothing is a mistake")
    classes = tuple(
        _railing_class(entry, f"{where}:classes[{index}]", sample_m=measures["sample_m"])
        for index, entry in enumerate(raw_classes)
    )

    ids = [klass.id for klass in classes]
    if len(set(ids)) != len(ids):
        # An id is a mesh name and a glTF material name, so two classes sharing
        # one would collide inside a single file and the second would win
        # silently.
        raise ValueError(f"{where}:classes repeats an id: {ids}")

    admitted: dict[str, str] = {}
    for klass in classes:
        for code in klass.line_types:
            if code in admitted:
                # ⚠️ Not a tidiness check. A code in two classes is drawn twice,
                # in two places, at two heights — and every one of those renders
                # as a perfectly good piece of street furniture.
                raise ValueError(
                    f"{where}:classes admits {code!r} in both {admitted[code]!r} and "
                    f"{klass.id!r}; it would be drawn twice and both would look right"
                )
            admitted[code] = klass.id

    return Railings(
        **_spec_header(body, where, _RAILING_ROLES),
        sample_m=measures["sample_m"],
        max_offset_m=measures["max_offset_m"],
        max_shift_m=measures["max_shift_m"],
        min_station_gap_m=measures["min_station_gap_m"],
        fold_tolerance_deg=measures["fold_tolerance_deg"],
        bend_report_deg=measures["bend_report_deg"],
        classes=classes,
    )


def _railing_class(body: Any, where: str, *, sample_m: float) -> RailingClass:
    """One entry of the railing block's `classes` table (`Q61`)."""
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    klass_id = str(_require(body, "id", where))
    if not klass_id:
        raise ValueError(f"{where}:id is empty; it names a mesh and a glTF material")
    if klass_id.endswith("-col"):
        # ⚠️ **The collider guard, and it lives here because the mesh name now
        # comes from config.** `GAME_DESIGN.md` puts railings under "omit or
        # make breakable" — a solid one turns a narrow street into a corridor —
        # and Godot's importer builds a static body from exactly this suffix. It
        # was one string in `pipeline/railings.py` until the classes arrived;
        # unguarded here, a city config could hand the region 9 km of wall.
        raise ValueError(
            f"{where}:id {klass_id!r} ends in '-col', which Godot's importer turns into "
            f"collision. Railings ship as scenery (GAME_DESIGN.md); breakaway is a B3 question"
        )

    raw_types = _require(body, "line_types", where)
    if isinstance(raw_types, str) or not isinstance(raw_types, (list, tuple)):
        raise ValueError(f"{where}:line_types must be a list, got {raw_types!r}")
    line_types = tuple(str(value) for value in raw_types)
    if not line_types:
        raise ValueError(f"{where}:line_types is empty; a class that admits nothing is a mistake")
    if len(set(line_types)) != len(line_types):
        # A repeat would double a code's metres in the refusal accounting and
        # nothing else, which is exactly the kind of quiet wrong this stage's
        # counters exist to prevent.
        raise ValueError(f"{where}:line_types repeats a code: {line_types}")

    measures = _measures(
        body,
        where,
        ("bridge_gap_m", "min_run_m", "station_m", "height_m", "thickness_m", "panel_m"),
        positive=True,
    )
    if measures["min_run_m"] < sample_m:
        # A minimum shorter than the sampling pitch cannot refuse anything: the
        # shortest run the sampler can produce is one cell.
        raise ValueError(
            f"{where}:min_run_m {measures['min_run_m']} is shorter than the block's sample_m "
            f"{sample_m}, so it would refuse nothing"
        )

    # `positive=False`: a class may legitimately sit flush on the kerb line with
    # no sink and no outset, which is zero rather than absent.
    lifts = _measures(body, where, ("base_sink_m", "outset_m"))

    return RailingClass(id=klass_id, line_types=line_types, **measures, **lifts)
