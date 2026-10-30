"""Generate the signal-head library (`P3-3e`, `Q173`).

    python tools/make_signal_heads.py
    python tools/make_signal_heads.py --out-dir /tmp/signals --report

One `.glb`, `heads.glb`, holding one node, `head`: a post and a three-aspect
head, which `pipeline/signals.py` stands at every bound post by a placements
document (`signal_heads_placements.json`), the shape every prop library takes
(`P5-2`). One head for every admitted code, because nothing published says a
`P` from an `S` or how many aspects a head carries (`Q76`).

**The geometry is `P3-17`'s, ported** (`_draw_post` / `_draw_head` at
`2415688^`), with its two recorded defects kept fixed: the post ring is
REVERSED (`signs._draw_pole`'s inward-wound prism), and the head stands IN
FRONT of the post, its back face on the post's surface, not 0.24 m behind it.

**The lens circuit rides `TEXCOORD_0`**: `UV.x` is 0 on the housing and `k + 1`
on lens `k` of `HEAD_LENSES` (red, amber, green), which `signal_head.gdshader`
decodes against the light `SignalController` writes into `INSTANCE_CUSTOM` —
`make_vehicle.py`'s lamp circuits on `UV.x`, the precedent that renders on both
renderers. ⚠️ **Not `COLOR_0` alpha**, which `lamps.py`'s lantern uses (`Q160`):
measured 2026-10-30, the Compatibility renderer (the web build) reads alpha 0 on
every vertex of this mesh, so every lens went dark there while Mobile lit them.
`COLOR_0` alpha ships 255. The vertex colour is the UNLIT glass; the lit colour
is `signal_heads.tres`'s.

**Frame.** The head faces `-Z` (north, the library convention
`placed_positions` stands at a bearing), `+Y` up, the post's foot at the
origin — a placement's `pos` is the footway's height and its `rot_y_deg` the
way the head looks.

Output goes to `game/assets/authored/signals/`, which is **committed** — a
hand-authored asset under CC BY-SA 4.0, not build output. See LICENSING.md.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))

from pipeline.config import load_config  # noqa: E402
from pipeline.config_blocks.signals import HEAD_LENSES, HeadDrawing  # noqa: E402
from pipeline.gltf import MeshData, write_glb  # noqa: E402
from pipeline.meshbuild import ColouredBuilder  # noqa: E402
from pipeline.signals import SIGNAL_HEAD_MESH  # noqa: E402
from pipeline.signs import disc, plate_frame  # noqa: E402

LOG = logging.getLogger("make_signal_heads")

DEFAULT_OUT_DIR = ROOT / "game" / "assets" / "authored" / "signals"
LIBRARY_FILE = "heads.glb"
# `generated_scene_import.gd`'s `SHADERS` row: the name is the contract.
MATERIAL = "signal_heads"
# `UV.x` on the housing: no circuit.
BODY_CIRCUIT = 0


def lens_circuit(index: int) -> int:
    """The `UV.x` lens `index` of `HEAD_LENSES` ships."""
    return index + 1


def _draw_post(builder: ColouredBuilder, drawing: HeadDrawing, top_y: float) -> None:
    """The post, a closed prism with a cap, from the footway up to `top_y`.

    No bottom cap: the post meets the footway and nothing sees under it.
    ⚠️ **The ring is REVERSED** — `disc` winds counter-clockwise in `(u, v)`,
    which here are world `X` and `Z`, so unreversed every side would face in.
    """
    ring = disc(drawing.post_radius_m, drawing.post_sides)[::-1]
    body = drawing.colours["body"]
    for index in range(drawing.post_sides):
        u0 = ring[index]
        u1 = ring[(index + 1) % drawing.post_sides]
        quad = np.array(
            [
                [u0[0], 0.0, u0[1]],
                [u1[0], 0.0, u1[1]],
                [u1[0], top_y, u1[1]],
                [u0[0], top_y, u0[1]],
            ]
        )
        outward = np.array([u0[0] + u1[0], 0.0, u0[1] + u1[1]])
        builder.polygon(quad, outward / np.linalg.norm(outward), body, BODY_CIRCUIT)
    cap = np.column_stack([ring[:, 0], np.full(len(ring), top_y), ring[:, 1]])
    builder.polygon(cap, np.array([0.0, 1.0, 0.0]), body, BODY_CIRCUIT)


def _draw_head(builder: ColouredBuilder, drawing: HeadDrawing, front: np.ndarray) -> None:
    """The head, a closed box running back from `front` — the centre of the face
    the traffic sees — with its lenses on that face.

    All six faces: a head hangs at eye level and above, so the underside is the
    face a driver stopped at the line looks straight at. The frame is
    `signs.plate_frame`'s, which fixes the winding (`u x up == n`).
    """
    normal, right = plate_frame(0.0)
    up = np.array([0.0, 1.0, 0.0])
    body = drawing.colours["body"]
    half_w = 0.5 * drawing.head_width_m
    half_h = 0.5 * drawing.head_height_m
    back = front - drawing.head_depth_m * normal

    fl = front - half_w * right - half_h * up
    fr = front + half_w * right - half_h * up
    fru = front + half_w * right + half_h * up
    flu = front - half_w * right + half_h * up
    bl = back - half_w * right - half_h * up
    blu = back - half_w * right + half_h * up
    bru = back + half_w * right + half_h * up
    br = back + half_w * right - half_h * up
    # Each face wound so its own outward normal is the one it is given.
    for corners, facing in (
        ((fl, fr, fru, flu), normal),
        ((bl, blu, bru, br), -normal),
        ((fr, br, bru, fru), right),
        ((fl, flu, blu, bl), -right),
        ((flu, fru, bru, blu), up),
        ((fl, bl, br, fr), -up),
    ):
        builder.polygon(np.vstack(corners), facing, body, BODY_CIRCUIT)

    # Down the face top to bottom, lifted clear of it: coplanar faces z-fight.
    lens_face = front + drawing.lens_lift_m * normal
    pitch = drawing.head_height_m / len(HEAD_LENSES)
    ring = disc(0.5 * drawing.lens_diameter_m, drawing.lens_segments)
    for index, name in enumerate(HEAD_LENSES):
        offset = half_h - pitch * (index + 0.5)
        lens = np.vstack([lens_face + u * right + (offset + v) * up for u, v in ring])
        builder.polygon(lens, normal, drawing.colours[name], lens_circuit(index))


def head_mesh(drawing: HeadDrawing) -> MeshData:
    """The library's one mesh: the post, and the head in front of it."""
    builder = ColouredBuilder(MATERIAL)
    head_top = drawing.mount_height_m + drawing.head_height_m
    _draw_post(builder, drawing, head_top + drawing.post_headroom_m)
    normal, _ = plate_frame(0.0)
    centre_y = drawing.mount_height_m + 0.5 * drawing.head_height_m
    front = np.array([0.0, centre_y, 0.0]) + (drawing.post_radius_m + drawing.head_depth_m) * normal
    _draw_head(builder, drawing, front)
    mesh = builder.build(SIGNAL_HEAD_MESH)
    assert mesh is not None and mesh.colours is not None
    # The builder carries each polygon's circuit in its alpha byte; it ships on
    # `UV.x`, and alpha goes back to "nothing to say".
    circuit = mesh.colours[:, 3].astype(np.float32)
    colours = mesh.colours.copy()
    colours[:, 3] = 255
    uvs = np.column_stack([circuit, np.zeros_like(circuit)])
    return replace(mesh, colours=colours, uvs=uvs)


def write_library(out_dir: Path) -> tuple[Path, int, MeshData]:
    """Write `heads.glb` from `hong_kong.yaml`'s `signals.heads.drawing`."""
    signals = load_config().signals
    if signals is None or signals.heads is None:
        raise SystemExit("hong_kong.yaml declares no signals.heads block to draw")
    mesh = head_mesh(signals.heads.drawing)
    path = out_dir / LIBRARY_FILE
    return path, write_glb(path, [mesh]), mesh


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="output directory")
    parser.add_argument("--report", action="store_true", help="print the geometry it produced")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    path, written, mesh = write_library(args.out_dir)
    LOG.info("wrote %s (%d bytes)", path, written)
    if args.report:
        low, high = mesh.aabb()
        LOG.info(
            "  %s %d triangles  %.2f x %.2f x %.2f m",
            mesh.name,
            mesh.triangle_count,
            high[0] - low[0],
            high[1] - low[1],
            high[2] - low[2],
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
