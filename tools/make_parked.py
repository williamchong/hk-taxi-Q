"""Generate the parked roster's library (`P3-72`, `Q161`).

    python tools/make_parked.py
    python tools/make_parked.py --out-dir /tmp/vehicles --report

One `.glb`, `parked.glb`, holding one node per roster kind — `car_a`, `car_b`,
`taxi`, `minibus`, `bus`, `coach`, `van`, `tram`, `motorcycle` — which
`pipeline/parked.py` stands by a placements document, the shape every prop
library takes (`P5-2`). Each node is a MeshGroup of `vehicle_*` material parts
(`make_vehicle.material_parts`), so `generated_scene_import.gd` merges it into
one `vehicle_body` surface on `vehicle_body.tres`: the glass, the lamps and the
paint shade as the player's taxi does, and every lens stays dark because no
`vehicle_lamps.gd` drives a parked car.

**Real footprints, not toy proportions.** A parked car sits beside the
player's Crown Comfort, which has run on its real wheelbase since `Q153`, and
a toy beside it reads as a toy. The lengths and widths here are the ones
`hong_kong.yaml`'s `parked.vehicles:` places by, and `tests/test_make_parked.py`
pins the two tables to each other.

**Frame.** Nose at `-Z` (north, the library convention `placed_positions`
stands at a bearing), `+Y` up, the ground at `y = 0` — a placement's `pos` is
the road's own height. Wheels are baked in: a parked car's wheels never turn.

Output goes to `game/assets/authored/vehicles/`, which is **committed** — these
are hand-authored assets under CC BY-SA 4.0, not build output. See LICENSING.md.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from make_vehicle import (  # noqa: E402
    BODY_MATERIAL,
    DARK,
    GLASS,
    LAMP,
    RED,
    SILVER,
    _marked,
    _rake_run_m,
    _wheel,
    material_parts,
)
from pipeline.gltf import MeshData, MeshGroup, write_glb  # noqa: E402
from pipeline.mesh import merge  # noqa: E402
from primitives import Colour, box_at, loft, ring  # noqa: E402

LOG = logging.getLogger("make_parked")

DEFAULT_OUT_DIR = ROOT / "game" / "assets" / "authored" / "vehicles"
LIBRARY_FILE = "parked.glb"

# Liveries. Flat, three to five a vehicle (`ART_DESIGN.md`), each one a
# vehicle a Hong Kong street actually carries.
WHITE = (236, 236, 232)
NAVY = (38, 56, 104)
CREAM = (240, 232, 200)
MINIBUS_GREEN = (24, 122, 72)
CITYBUS_YELLOW = (238, 194, 44)
TRAM_GREEN = (22, 108, 60)
TRAM_CREAM = (232, 226, 196)
STEEL = (120, 122, 126)

# Fewer segments than the taxi's 18: a parked wheel is looked at from a car
# going past, and four of them a vehicle over nine kinds is where the triangles
# go.
WHEEL_SEGMENTS = 10


@dataclass(frozen=True)
class Shape:
    """One roster kind as proportions, in metres."""

    kind: str
    length_m: float
    width_m: float
    paint: Colour
    roof: Colour
    # The underside's clearance and the body's rings.
    sill_y_m: float
    belt_y_m: float
    roof_y_m: float
    # Where the glasshouse starts and ends along the body, from the nose.
    cabin_front_m: float
    cabin_rear_m: float
    windscreen_rake_deg: float
    backlight_rake_deg: float
    # Chamfer at the vertical corners, and how far the roof draws in.
    corner_cut_m: float
    roof_inset_m: float
    wheel_radius_m: float
    wheel_width_m: float
    # The axles, from the nose.
    axles_m: tuple[float, ...]
    # A second glasshouse over the first (a double-decker, a tram).
    upper_deck: bool = False
    # Wheels along the centreline (a motorcycle), not at the flanks.
    single_track: bool = False
    # A bar at the belt in a second colour (a tram's cream band).
    band: Colour | None = None

    @property
    def half_width_m(self) -> float:
        return self.width_m / 2.0

    @property
    def front_z_m(self) -> float:
        return -self.length_m / 2.0

    @property
    def rear_z_m(self) -> float:
        return self.length_m / 2.0


def _lower(shape: Shape) -> MeshData:
    """Sill to belt, lofted with a tucked sill and a chamfered corner."""
    front, rear = shape.front_z_m, shape.rear_z_m
    hw = shape.half_width_m
    cut = shape.corner_cut_m
    tuck = min(0.08, (shape.belt_y_m - shape.sill_y_m) / 3.0)
    rings = [
        ring(shape.sill_y_m, hw - tuck, front + tuck, rear - tuck, cut),
        ring(shape.sill_y_m + tuck, hw, front, rear, cut),
        ring(shape.belt_y_m, hw, front, rear, cut),
    ]
    return loft(
        rings,
        [shape.paint, shape.paint],
        bottom=DARK,
        top=None,
        name="lower",
    )


def _glasshouse(
    shape: Shape, belt_y: float, top_y: float, roof: Colour, *, name: str, cap: bool
) -> MeshData:
    """Belt to roof: a glass band under a painted cant rail, raked at both ends."""
    hw = shape.half_width_m
    rise = top_y - belt_y
    glass_rise = rise * 0.72
    front = shape.front_z_m + shape.cabin_front_m
    rear = shape.front_z_m + shape.cabin_rear_m
    front_run = _rake_run_m(shape.windscreen_rake_deg, glass_rise)
    rear_run = _rake_run_m(shape.backlight_rake_deg, glass_rise)
    cut = shape.corner_cut_m
    inset = shape.roof_inset_m
    rings = [
        ring(belt_y, hw, front, rear, cut),
        ring(belt_y + glass_rise, hw - inset * 0.6, front + front_run, rear - rear_run, cut),
        ring(
            top_y, hw - inset, front + front_run + inset * 0.5, rear - rear_run - inset * 0.5, cut
        ),
    ]
    return loft(rings, [GLASS, roof], bottom=None, top=roof if cap else None, name=name)


def _lamps(shape: Shape, y: float) -> list[MeshData]:
    """Head lamps and tail lamps, flush on the ends, marked as lenses by name."""
    hw = shape.half_width_m
    parts: list[MeshData] = []
    for tag, side in (("l", -1.0), ("r", 1.0)):
        x = side * (hw - 0.22)
        # Flush with the ends — the lens's outer face IS the body's end, so the
        # footprint `parked.vehicles:` places by stays the loft's own.
        parts.append(
            box_at(
                (x, y, shape.front_z_m + 0.012),
                (0.11, 0.05, 0.012),
                LAMP,
                name=f"headlamp_{tag}",
            )
        )
        parts.append(
            box_at(
                (x, y, shape.rear_z_m - 0.012),
                (0.08, 0.05, 0.012),
                RED,
                name=f"taillamp_{tag}",
            )
        )
    return parts


def _wheels(shape: Shape) -> list[MeshData]:
    wheel = _wheel(
        shape.wheel_radius_m, shape.wheel_width_m, WHEEL_SEGMENTS, rim_fraction=0.5, name="wheel"
    )
    parts: list[MeshData] = []
    xs = (
        (0.0,)
        if shape.single_track
        else (
            -(shape.half_width_m - shape.wheel_width_m / 2.0 - 0.02),
            shape.half_width_m - shape.wheel_width_m / 2.0 - 0.02,
        )
    )
    for index, axle in enumerate(shape.axles_m):
        z = shape.front_z_m + axle
        for x in xs:
            parts.append(
                replace(
                    wheel, name=f"wheel_{index}_{'l' if x < 0 else 'r' if x > 0 else 'c'}"
                ).translated((x, shape.wheel_radius_m, z))
            )
    return parts


def vehicle(shape: Shape) -> MeshData:
    """One kind as one marked mesh, ready for `material_parts`."""
    parts: list[MeshData] = [_lower(shape)]
    deck_top = shape.roof_y_m
    if shape.upper_deck:
        deck_top = shape.belt_y_m + (shape.roof_y_m - shape.belt_y_m) * 0.5
        parts.append(
            _glasshouse(shape, shape.belt_y_m, deck_top, shape.paint, name="lower_deck", cap=False)
        )
        parts.append(
            _glasshouse(shape, deck_top, shape.roof_y_m, shape.roof, name="upper_deck", cap=True)
        )
    else:
        parts.append(
            _glasshouse(
                shape, shape.belt_y_m, shape.roof_y_m, shape.roof, name="glasshouse", cap=True
            )
        )
    if shape.band is not None:
        parts.append(
            box_at(
                (0.0, shape.belt_y_m, 0.0),
                (shape.half_width_m - 0.005, 0.06, shape.length_m / 2.0 - shape.corner_cut_m),
                shape.band,
                name="band",
            )
        )
    parts.extend(_lamps(shape, shape.sill_y_m + (shape.belt_y_m - shape.sill_y_m) * 0.65))
    parts.extend(_wheels(shape))
    body = merge([_marked(part) for part in parts], name=shape.kind)
    return replace(body, material=BODY_MATERIAL)


def motorcycle(shape: Shape) -> MeshData:
    """Two wheels in line under a tank, a saddle and a bar — the one kind that
    is not a lofted body."""
    front, rear = shape.front_z_m, shape.rear_z_m
    r = shape.wheel_radius_m
    parts: list[MeshData] = [
        # The frame, from the headstock down to the rear axle.
        box_at((0.0, r + 0.18, 0.0), (0.07, 0.12, shape.length_m * 0.3), DARK, name="frame"),
        # Tank, in the livery.
        box_at((0.0, r + 0.42, front + 0.75), (0.17, 0.12, 0.28), shape.paint, name="tank"),
        # Saddle.
        box_at((0.0, r + 0.44, rear - 0.6), (0.16, 0.05, 0.34), DARK, name="saddle"),
        # Handlebar, across the headstock.
        box_at((0.0, r + 0.62, front + 0.42), (0.4, 0.02, 0.02), SILVER, name="bar"),
        # Fork and the headlamp on it.
        box_at((0.0, r + 0.3, front + 0.4), (0.03, 0.3, 0.03), SILVER, name="fork"),
        # Named with the taxi's lamp prefixes, so `_marked` reads them as lenses.
        box_at((0.0, r + 0.5, front + 0.33), (0.07, 0.07, 0.03), LAMP, name="headlamp_c"),
        box_at((0.0, r + 0.3, rear - 0.12), (0.05, 0.03, 0.02), RED, name="taillamp_c"),
        # Exhaust, low on the right.
        box_at((0.14, r - 0.05, rear - 0.55), (0.04, 0.04, 0.3), STEEL, name="exhaust"),
    ]
    parts.extend(_wheels(shape))
    body = merge([_marked(part) for part in parts], name=shape.kind)
    return replace(body, material=BODY_MATERIAL)


def _car(kind: str, paint: Colour, roof: Colour) -> Shape:
    return Shape(
        kind=kind,
        length_m=4.5,
        width_m=1.8,
        paint=paint,
        roof=roof,
        sill_y_m=0.22,
        belt_y_m=0.78,
        roof_y_m=1.42,
        cabin_front_m=1.25,
        cabin_rear_m=3.65,
        windscreen_rake_deg=32.0,
        backlight_rake_deg=30.0,
        corner_cut_m=0.16,
        roof_inset_m=0.14,
        wheel_radius_m=0.32,
        wheel_width_m=0.2,
        axles_m=(0.85, 3.55),
    )


SHAPES: tuple[Shape, ...] = (
    _car("car_a", WHITE, WHITE),
    _car("car_b", NAVY, NAVY),
    # The red urban taxi, parked: a Crown Comfort's footprint (`Q153`).
    Shape(
        kind="taxi",
        length_m=4.7,
        width_m=1.7,
        paint=RED,
        roof=SILVER,
        sill_y_m=0.22,
        belt_y_m=0.8,
        roof_y_m=1.46,
        cabin_front_m=1.45,
        cabin_rear_m=3.9,
        windscreen_rake_deg=35.0,
        backlight_rake_deg=30.0,
        corner_cut_m=0.16,
        roof_inset_m=0.13,
        wheel_radius_m=0.31,
        wheel_width_m=0.2,
        axles_m=(0.95, 3.75),
    ),
    # The green minibus: a Toyota Coaster, cream with the green roof.
    Shape(
        kind="minibus",
        length_m=7.0,
        width_m=2.1,
        paint=CREAM,
        roof=MINIBUS_GREEN,
        sill_y_m=0.35,
        belt_y_m=1.25,
        roof_y_m=2.6,
        cabin_front_m=0.35,
        cabin_rear_m=6.9,
        windscreen_rake_deg=14.0,
        backlight_rake_deg=6.0,
        corner_cut_m=0.14,
        roof_inset_m=0.12,
        wheel_radius_m=0.38,
        wheel_width_m=0.22,
        axles_m=(1.6, 5.3),
    ),
    # The double-decker, in Citybus yellow.
    Shape(
        kind="bus",
        length_m=12.0,
        width_m=2.5,
        paint=CITYBUS_YELLOW,
        roof=CITYBUS_YELLOW,
        sill_y_m=0.35,
        belt_y_m=1.3,
        roof_y_m=4.4,
        cabin_front_m=0.2,
        cabin_rear_m=11.9,
        windscreen_rake_deg=6.0,
        backlight_rake_deg=3.0,
        corner_cut_m=0.16,
        roof_inset_m=0.1,
        wheel_radius_m=0.5,
        wheel_width_m=0.3,
        axles_m=(2.6, 8.2, 9.8),
        upper_deck=True,
    ),
    # A tour coach: single deck, high floor, white.
    Shape(
        kind="coach",
        length_m=12.0,
        width_m=2.5,
        paint=WHITE,
        roof=WHITE,
        sill_y_m=0.4,
        belt_y_m=1.7,
        roof_y_m=3.6,
        cabin_front_m=0.3,
        cabin_rear_m=11.6,
        windscreen_rake_deg=10.0,
        backlight_rake_deg=4.0,
        corner_cut_m=0.18,
        roof_inset_m=0.14,
        wheel_radius_m=0.5,
        wheel_width_m=0.3,
        axles_m=(2.6, 8.6),
        band=NAVY,
    ),
    # The Hiace: a van's box, tall, short-nosed.
    Shape(
        kind="van",
        length_m=4.7,
        width_m=1.8,
        paint=WHITE,
        roof=WHITE,
        sill_y_m=0.25,
        belt_y_m=1.0,
        roof_y_m=1.95,
        cabin_front_m=0.45,
        cabin_rear_m=4.6,
        windscreen_rake_deg=22.0,
        backlight_rake_deg=4.0,
        corner_cut_m=0.12,
        roof_inset_m=0.1,
        wheel_radius_m=0.32,
        wheel_width_m=0.2,
        axles_m=(0.95, 3.55),
    ),
    # The tram: a tall, narrow double-decker with a cream band at the belt.
    Shape(
        kind="tram",
        length_m=8.6,
        width_m=2.0,
        paint=TRAM_GREEN,
        roof=TRAM_GREEN,
        sill_y_m=0.3,
        belt_y_m=1.3,
        roof_y_m=4.7,
        cabin_front_m=0.25,
        cabin_rear_m=8.35,
        windscreen_rake_deg=4.0,
        backlight_rake_deg=4.0,
        corner_cut_m=0.22,
        roof_inset_m=0.12,
        wheel_radius_m=0.3,
        wheel_width_m=0.12,
        axles_m=(1.6, 7.0),
        upper_deck=True,
        band=TRAM_CREAM,
    ),
    Shape(
        kind="motorcycle",
        length_m=2.1,
        width_m=0.8,
        paint=RED,
        roof=DARK,
        sill_y_m=0.0,
        belt_y_m=0.0,
        roof_y_m=0.0,
        cabin_front_m=0.0,
        cabin_rear_m=0.0,
        windscreen_rake_deg=0.0,
        backlight_rake_deg=0.0,
        corner_cut_m=0.0,
        roof_inset_m=0.0,
        wheel_radius_m=0.3,
        wheel_width_m=0.12,
        axles_m=(0.3, 1.8),
        single_track=True,
    ),
)


def build_roster(shapes: Sequence[Shape] = SHAPES) -> list[MeshData]:
    """Every kind as one marked mesh, in roster order."""
    return [motorcycle(shape) if shape.single_track else vehicle(shape) for shape in shapes]


def write_roster(
    out_dir: Path, shapes: Sequence[Shape] = SHAPES
) -> tuple[Path, int, list[MeshData]]:
    """The library, one node per kind; returns where it went and its bytes."""
    meshes = build_roster(shapes)
    path = out_dir / LIBRARY_FILE
    groups: list[MeshGroup] = [material_parts(mesh) for mesh in meshes]
    return path, write_glb(path, groups), meshes


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="output directory")
    parser.add_argument("--report", action="store_true", help="print the geometry it produced")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    path, written, meshes = write_roster(args.out_dir)
    LOG.info("wrote %s (%d bytes, %d kinds)", path, written, len(meshes))
    if args.report:
        for mesh in meshes:
            low, high = mesh.aabb()
            colours = len({tuple(int(v) for v in row[:3]) for row in mesh.colours})
            LOG.info(
                "  %-10s %5d triangles  %.2f x %.2f x %.2f m  %d colours",
                mesh.name,
                mesh.triangle_count,
                high[0] - low[0],
                high[1] - low[1],
                high[2] - low[2],
                colours,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
