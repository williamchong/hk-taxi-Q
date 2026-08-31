"""Generate the authored road-closure barrier (`P3-29`).

    python tools/make_barrier.py
    python tools/make_barrier.py --out-dir /tmp/barriers --report

`Q19` ends with a fence: 14 drivable level-0 edges keep less than the car's own
1.80 m clear, and `RoadGraph.fits_car` refuses them. 🔴 **A refusal the player
cannot see is the defect it was meant to fix.** Round 0 of `P3-9a` ended with
three HK drivers stopping at geometry they could not read, and an invisible
predicate repeats that with different plumbing — so the fence is dressed, and
this is what stands at its mouths.

**Why authored and not generated.** Nothing is published about where a closure
should be: the government draws the carriageway, not the works. So the prop is
this project's own — the first hand-authored street furniture in a tree that
holds fonts, vehicles and one landmark — and it ships committed under CC BY-SA
4.0 (`LICENSING.md`; hard rule 7's authored lane). Generated rather than
modelled on `tools/make_landmark.py`'s argument, which is the one the
byte-comparison test enforces: a committed generator is reproducible from a
fresh clone and reviewable in a diff.

⚠️ **It carries a collider, and it is the only thing in this family that
does.** Every generated railing class is deliberately collider-free — see
`game/tuning/barriers.tres`, whose "no collider, like every class in this
layer" paragraph is about the *generated* `barriers` class and stays true. This
is a different layer, and here the collision is the whole point: `Q19` forbids
an invisible refusal, and a barrier you drive through is one. The collider is
the `-col` node-name suffix, acted on at import.

⚠️ **The material name is NOT `barriers`.** That name already dispatches the
generated railing class to `tuning/barriers.tres` in
`game/tools/generated_scene_import.gd`, and `verify_railings.gd` asserts that
class has no collision — so sharing the name would hand this prop a fence's
shader and fail that tool. Like the authored landmark's `landmark_vertex`, this
name is absent from `SHADERS` on purpose and takes the vertex-colour fallback.

Authored at the origin: centred on x, `y = 0` at the road surface, spanning x
and thin in z. `fence.json` carries a position and a **direction vector** — not
`landmarks.json`'s compass bearing, which `pipeline/fence.py` records at length
as the convention this layer exists to avoid — and the runtime turns it into a
basis with `RoadSpawn.basis_facing`.

🔴 **The prop is mirror-symmetric about `z = 0`, and that is load-bearing rather
than incidental.** `Basis.looking_at` puts a model's **-Z** on the target, which
is Godot's forward; a prop with a front would therefore have to be authored
facing -Z, and one authored facing +Z would stand backwards at every mouth in
the region while rendering perfectly (`Q62`). This one has no front, so the
question does not arise — and `test_the_prop_has_no_front_so_the_facing_cannot
_be_backwards` is what fails the moment someone adds a chevron, a plate or a
lamp and inherits the trap.

Output goes to `game/assets/authored/barriers/`, which is **committed**.
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

from pipeline.buildings import COLLISION_SUFFIX  # noqa: E402
from pipeline.config import Material, check_material_exposure, load_config  # noqa: E402
from pipeline.gltf import MeshData, write_glb  # noqa: E402
from pipeline.mesh import merge  # noqa: E402
from primitives import box_at  # noqa: E402

LOG = logging.getLogger("make_barrier")

DEFAULT_OUT_DIR = ROOT / "game" / "assets" / "authored" / "barriers"

BARRIER_FILE = "barrier.glb"

# ⚠️ **Not `barriers`** — see the module docstring. Absent from
# `generated_scene_import.gd`'s `SHADERS`, so it takes the vertex-colour
# fallback exactly as `landmark_vertex` does.
MATERIAL = "barrier_vertex"

# `hong_kong.yaml:materials` in miniature, on the config's own `Material`
# dataclass, for the reason `make_landmark.py` gives: that table colours what
# the ETL draws, and a committed `.glb` never passes through the ETL. The same
# rule still binds (`Q33`) — every colour is `reflectance x exposure_anchor`,
# checked by `check_palette` against the anchor read live from the city config
# (`Q38`), so moving the anchor stops this generator loudly rather than
# shipping a prop lit for the wrong exposure. Colours are sRGB (`Q27`).
RAIL_WHITE = Material(
    "barrier_white",
    (156, 154, 148),
    62.0,
    "painted white steel on a works barrier, 55-70% — never pure white",
)
RAIL_RED = Material(
    "barrier_red",
    (161, 63, 54),
    22.0,
    "the red band of the same paint scheme, 18-28%",
)
POST_GREY = Material(
    "barrier_post",
    (113, 113, 116),
    32.0,
    "galvanised post, weathered, 28-38%",
)

PALETTE = (RAIL_WHITE, RAIL_RED, POST_GREY)


def check_palette(anchor: float) -> None:
    """`_check_exposure` for the colours the ETL never sees — same shared body."""
    for surface in PALETTE:
        check_material_exposure(surface, anchor, surface.name)


@dataclass(frozen=True)
class Barrier:
    """One closure barrier, in metres, authored rather than surveyed.

    ⚠️ Every number here is **authored** — nothing publishes a road closure, so
    there is no sheet to cite and no measurement to defend. What they answer to
    instead is the acceptance criterion: *legible before it is hit at driving
    speed from every approach*. That makes the height and the banding the
    load-bearing values, and it is why they are here in a diff rather than
    inside a mesh.
    """

    # Chest height on the driver's eye line at the moment it matters. Taller
    # reads as a wall and hides what is behind it, which is the thing the
    # player needs in order to believe the closure.
    height_m: float = 1.05
    # Depth of the rail, front to back. Thin enough to read as a barrier rather
    # than a plinth, thick enough to catch the light at a grazing angle.
    rail_depth_m: float = 0.14
    # The two rails and the gap between them. A single bar reads as a kerb from
    # the seat; two with air between them reads as a barrier.
    rail_height_m: float = 0.26
    rail_gap_m: float = 0.19
    # ⚠️ The banding is what makes it legible at speed, not the colour alone: a
    # flat red bar and a flat white bar are the same object at 60 kph. Bands are
    # counted rather than pitched so the pattern survives every width the fence
    # asks for — an odd count keeps a white band at both ends.
    bands: int = 7
    # Posts stand inboard of the ends so the rail overhangs them, which is what
    # a real barrier does and what stops the ends reading as cut.
    post_half_m: float = 0.055
    post_inset_m: float = 0.42
    # How far the posts continue below the road, so ±0.1 m of disagreement with
    # the ribbon reads as a barrier standing on tarmac rather than floating.
    # `make_landmark.py`'s plinth, at the scale of a post.
    foot_depth_m: float = 0.35


def build_barrier(width_m: float, spec: Barrier | None = None) -> MeshData:
    """One barrier `width_m` across, centred on x, facing +z, `y = 0` at the road."""
    spec = spec or Barrier()
    if width_m <= 2.0 * spec.post_inset_m:
        # Refused rather than clamped: a barrier narrower than its own posts
        # would emit them crossed, and a mesh that renders as a knot is exactly
        # the class of defect this layer exists to stop being invisible.
        raise ValueError(
            f"a barrier {width_m:.2f} m wide cannot carry posts inset "
            f"{spec.post_inset_m:.2f} m from each end"
        )

    parts: list[MeshData] = []
    band_m = width_m / spec.bands
    tops = (
        spec.height_m - spec.rail_height_m,
        spec.height_m - 2.0 * spec.rail_height_m - spec.rail_gap_m,
    )
    for course, low in enumerate(tops):
        for index in range(spec.bands):
            # Alternating from white at both ends, which needs `bands` odd; an
            # even count is legal and simply starts and ends on opposite
            # colours, so this reads the index rather than asserting the parity.
            colour = RAIL_WHITE.colour if index % 2 == 0 else RAIL_RED.colour
            centre_x = -0.5 * width_m + (index + 0.5) * band_m
            parts.append(
                box_at(
                    (centre_x, low + 0.5 * spec.rail_height_m, 0.0),
                    (0.5 * band_m, 0.5 * spec.rail_height_m, 0.5 * spec.rail_depth_m),
                    colour,
                    name=f"barrier_rail_{course}_{index}",
                )
            )

    for side, sign in enumerate((-1.0, 1.0)):
        post_x = sign * (0.5 * width_m - spec.post_inset_m)
        # From below the road to the top rail, so the post carries the rail
        # rather than stopping under it.
        low_y = -spec.foot_depth_m
        parts.append(
            box_at(
                (post_x, 0.5 * (low_y + spec.height_m), 0.0),
                (spec.post_half_m, 0.5 * (spec.height_m - low_y), spec.post_half_m),
                POST_GREY.colour,
                name=f"barrier_post_{side}",
            )
        )

    # `-col` is the whole of the collision, applied to the merged node name
    # because `write_glb` writes the mesh name as the node name and that is
    # where the importer looks. ⚠️ Hyphen, never `_col`: the underscore
    # suffixes are the ones Godot converts into other physics nodes.
    return replace(
        merge(parts, name=f"barrier{COLLISION_SUFFIX}"),
        material=MATERIAL,
    )


# One standard unit, placed in a row to span whatever mouth the fence asks for.
#
# 🔴 **A row of units, never one barrier scaled to the width.** A closure on a
# real street is assembled from standard lengths, and the alternative here is
# worse than merely unfaithful: an x-scale that took a 2 m prop to a 10 m mouth
# would stretch the posts to 0.55 m across with it, so the wider the street the
# more obviously wrong the prop. `fence.json` carries one placement per unit and
# the runtime instances the same mesh at each — which is also why this stays a
# committed authored asset instead of geometry the ETL emits per edge, the thing
# `LICENSING.md` forbids in this tree.
UNIT_WIDTH_M = 2.0


def build_barriers() -> list[tuple[str, MeshData]]:
    """The shipped prop set — one standard unit."""
    return [(BARRIER_FILE, build_barrier(UNIT_WIDTH_M))]


def write_barriers(out_dir: Path) -> list[tuple[Path, int, MeshData]]:
    """Check the palette against the live anchor, then write one `.glb` each."""
    check_palette(load_config().exposure_anchor)
    written = []
    for filename, mesh in build_barriers():
        path = out_dir / filename
        written.append((path, write_glb(path, [mesh]), mesh))
    return written


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="output directory")
    parser.add_argument("--report", action="store_true", help="print the geometry it produced")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    written = write_barriers(args.out_dir)
    for path, size, mesh in written:
        LOG.info("%s — %d bytes, %d triangles", path, size, mesh.triangle_count)
    if args.report:
        for _, _, mesh in written:
            (low, high) = mesh.aabb()
            LOG.info(
                "  %-20s x %+.2f..%+.2f  y %+.2f..%+.2f  z %+.2f..%+.2f",
                mesh.name,
                low[0],
                high[0],
                low[1],
                high[1],
                low[2],
                high[2],
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
