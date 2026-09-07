"""The collider's node name has a copy on each side of the engine boundary (`P5-12`).

`etl/pipeline/buildings.py` names a tile's collider `<tile>_collision-colonly` and
`etl/pipeline/surface.py` a chunk's `road_surface_collision-colonly`; Godot's
importer strips the suffix and keeps the rest as the `StaticBody3D`'s name, which
is what `game/tools/verify_tiles.gd` and `game/tools/verify_road_surface.gd` look
the body up by. A suffix moved on one side is a collider every check calls missing
— or, worse, one it stops looking for — so each copy is parsed off its own file
and held to the pipeline's, the way `test_marking_codec_copies.py` holds the
marking codec.
"""

from __future__ import annotations

import re
from pathlib import Path

from pipeline.buildings import COLLIDER_NAME_SUFFIX, collider_name
from pipeline.gltf import COLLISION_ONLY_SUFFIX
from pipeline.surface import SURFACE_COLLIDER_NAME

ROOT = Path(__file__).resolve().parents[2]
VERIFY_TILES = ROOT / "game" / "tools" / "verify_tiles.gd"
VERIFY_ROAD = ROOT / "game" / "tools" / "verify_road_surface.gd"


def _declared(path: Path, name: str) -> str:
    match = re.search(rf'^const {name}: String = "([^"]+)"$', path.read_text(), re.M)
    assert match, f"{path} no longer declares {name} — did the spelling move?"
    return match.group(1)


def test_the_tile_body_suffix_is_the_pipeline_s() -> None:
    assert _declared(VERIFY_TILES, "COLLIDER_BODY_SUFFIX") == COLLIDER_NAME_SUFFIX
    assert collider_name("t_00_00") == "t_00_00" + COLLIDER_NAME_SUFFIX + COLLISION_ONLY_SUFFIX


def test_the_road_body_is_the_pipeline_s_name_less_its_suffix() -> None:
    assert SURFACE_COLLIDER_NAME.endswith(COLLISION_ONLY_SUFFIX)
    assert _declared(VERIFY_ROAD, "COLLIDER_BODY") == SURFACE_COLLIDER_NAME.removesuffix(
        COLLISION_ONLY_SUFFIX
    )
