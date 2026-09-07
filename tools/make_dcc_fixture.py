"""Author the DCC round-trip fixture with Blender's own glTF exporter (`P5-10`).

    blender --background --python tools/make_dcc_fixture.py -- \\
        game/assets/authored/fixtures/dcc_roundtrip.glb
    blender --background --python tools/make_dcc_fixture.py -- \\
        --vehicle game/assets/authored/fixtures/dcc_vehicle.glb

Every other mesh in the repository — the city, and the three "authored" assets
under `game/assets/authored/` — was written by `etl/pipeline/gltf.py`. These two
come through a DCC tool. The kiosk is the Khronos exporter, an unapplied child
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


def _export(out: str) -> int:
    """Export the selection as a binary glTF, as an artist would; returns the byte size."""
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
    return _export(out)


# The vehicle door's fixture (`P5-23`): four boxes joined into ONE object with
# four material slots named from `generated_scene_import.gd`'s `VEHICLE`
# table, no vertex colours, so the hook has to stamp the payload from the
# names and bake the colour from each slot's base colour. Metres, Blender
# z-up and y-forward; the exporter turns that into y-up with the nose at -z,
# which is the way the taxi faces. Boxes are (x, y, z) sizes and centres.
CAR_BODY = ((1.8, 4.0, 0.9), (0.0, 0.0, 0.65))
CAR_CABIN = ((1.6, 1.8, 0.6), (0.0, -0.2, 1.4))
CAR_BRAKE = ((0.3, 0.2, 0.15), (0.6, -2.1, 0.8))
CAR_HEADLAMP = ((0.3, 0.2, 0.15), (0.6, 2.1, 0.8))
CAR_MATERIALS = {
    "vehicle_paint": (0.7, 0.05, 0.05, 1.0),
    "vehicle_glass": (0.05, 0.05, 0.08, 1.0),
    "vehicle_lamp_brake": (0.8, 0.05, 0.05, 1.0),
    "vehicle_lamp_headlamp": (0.95, 0.9, 0.7, 1.0),
}


def _box(name: str, size, centre, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=centre)
    made = bpy.context.object
    made.name = name
    made.scale = size
    made.data.materials.append(mat)
    return made


def build_vehicle(out: str, misspell: str | None = None) -> int:
    """One object, four material slots from the vehicle vocabulary; returns the byte size.

    `misspell` renames one slot to a name the hook does not know, which is the
    mutation `verify_authored.gd`'s vehicle check is proven against: the hook
    must refuse the body rather than guess.
    """
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    materials = {name: material(name, colour) for name, colour in CAR_MATERIALS.items()}
    if misspell is not None:
        materials["vehicle_lamp_brake"].name = misspell
    body = _box("FixtureCar", *CAR_BODY, materials["vehicle_paint"])
    parts = [
        _box("cabin", *CAR_CABIN, materials["vehicle_glass"]),
        _box("brake", *CAR_BRAKE, materials["vehicle_lamp_brake"]),
        _box("headlamp", *CAR_HEADLAMP, materials["vehicle_lamp_headlamp"]),
    ]
    bpy.ops.object.select_all(action="DESELECT")
    for part in parts:
        part.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    # Origin at the ground centre, the convention the landmark door states
    # (footprint-centred, y = 0 at the base); a joined object otherwise keeps
    # the first cube's origin and every vertex sits below it in local space.
    bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
    bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
    # Scale applied: the exporter's `export_apply` applies modifiers, not the
    # object transform, and an unapplied scale ships as a node transform over
    # unit-cube vertices. The kiosk keeps one on purpose, as the importer test;
    # a car is handed over clean, which is what the recipe asks an artist for.
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.select_all(action="SELECT")
    return _export(out)


def main(argv: list[str]) -> int:
    if "--" not in argv or argv.index("--") + 1 >= len(argv):
        print(__doc__, file=sys.stderr)
        return 2
    args = argv[argv.index("--") + 1 :]
    if args[0] == "--vehicle":
        misspell = args[2] if len(args) > 2 else None
        print(f"exported {args[1]}: {build_vehicle(args[1], misspell)} bytes")
        return 0
    print(f"exported {args[0]}: {build(args[0])} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
