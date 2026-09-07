"""Author the DCC round-trip fixture with Blender's own glTF exporter (`P5-10`).

    blender --background --python tools/make_dcc_fixture.py -- \\
        game/assets/authored/fixtures/dcc_roundtrip.glb

Every other mesh in the repository — the city, and the three "authored" assets
under `game/assets/authored/` — was written by `etl/pipeline/gltf.py`. This is
the one that comes through a DCC tool: the Khronos exporter, an unapplied child
scale, a packed image, `doubleSided` materials, the ordinary shape of an
artist's export. `game/tools/verify_authored.gd` grades what the import does
with it, which is the contract `docs/ARCHITECTURE.md` states for a hand-made
`.glb`; `Q121` is why that contract had never been exercised.

Runs *inside* Blender, so `bpy` is its interpreter's and not a dependency of
the ETL. Output is committed: hand-authored, CC BY-SA 4.0 (`LICENSING.md`).
On first import Godot extracts the packed image beside the asset as
`dcc_roundtrip_kiosk_paint.png`; commit that and both `.import` sidecars.
"""

from __future__ import annotations

import os
import sys

import bpy

TEXTURE_PX = 64
BODY_M = (2.0, 2.0, 2.5)
ROOF_RADIUS_M = 1.6
ROOF_DEPTH_M = 0.8


def material(name: str, colour: tuple[float, float, float, float], image=None):
    """A Principled BSDF material, textured when `image` is given."""
    made = bpy.data.materials.new(name)
    made.use_nodes = True
    nodes = made.node_tree
    bsdf = nodes.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = colour
    bsdf.inputs["Roughness"].default_value = 0.7
    bsdf.inputs["Metallic"].default_value = 0.0
    if image is not None:
        texture = nodes.nodes.new("ShaderNodeTexImage")
        texture.image = image
        nodes.links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])
    return made


def build(out: str) -> int:
    """A textured kiosk body with a `-col` suffix and a child roof; returns the byte size."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0

    # A colour grid, packed into the .blend so the exporter embeds it.
    image = bpy.data.images.new("kiosk_paint", TEXTURE_PX, TEXTURE_PX)
    image.generated_type = "COLOR_GRID"
    image.pack()

    paint = material("KioskPaint", (1.0, 1.0, 1.0, 1.0), image)
    roof_paint = material("KioskRoofPaint", (0.2, 0.5, 0.3, 1.0))

    # Body: a box standing on the ground plane (Blender is z-up; the exporter
    # converts). The `-col` suffix is Godot's own collision hint.
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0.0, 0.0, BODY_M[2] / 2.0))
    body = bpy.context.object
    body.name = "KioskBody-col"
    body.scale = BODY_M
    body.data.materials.append(paint)

    # Roof: a child with its own material and an *unapplied* scale.
    bpy.ops.mesh.primitive_cone_add(
        vertices=6,
        radius1=ROOF_RADIUS_M,
        radius2=0.0,
        depth=ROOF_DEPTH_M,
        location=(0.0, 0.0, BODY_M[2] + ROOF_DEPTH_M / 2.0),
    )
    roof = bpy.context.object
    roof.name = "KioskRoof"
    roof.parent = body
    roof.matrix_parent_inverse = body.matrix_world.inverted()
    roof.data.materials.append(roof_paint)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(
        filepath=out,
        export_format="GLB",
        export_apply=True,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_yup=True,
        use_selection=True,
        export_animations=False,
        export_skins=False,
        export_lights=False,
        export_cameras=False,
    )
    return os.path.getsize(out)


def main(argv: list[str]) -> int:
    if "--" not in argv or argv.index("--") + 1 >= len(argv):
        print(__doc__, file=sys.stderr)
        return 2
    out = argv[argv.index("--") + 1]
    print(f"exported {out}: {build(out)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
