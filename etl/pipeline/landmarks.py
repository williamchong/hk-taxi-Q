"""Build the mesh-sourced hero landmarks: extract, slice, repaint, emit (`P3-6`).

    python -m pipeline.landmarks --city hong_kong --region wan_chai

A landmark with `source_paint` in the city config ships the building's own
source mesh rather than an authored model: the P3-6 review rounds converged the
generated HKCEC massing onto the source mesh by measurement, and the source
carries the silhouette natively. This stage reads exactly that mesh out of the
sheet zips, moves it to the landmark's local frame, cuts it along the ribbon
elevations (`mesh.slice_horizontal`) so vertex colour can hold a crisp band,
paints each triangle by facing and elevation, and writes the result into the
region out tree under `landmarks/`, alongside `landmark_assets.json` for
`export.py` to reconcile and name in the manifest.

The output is **generated city data**: derived from government geometry, it
stays under the publisher's terms, is gitignored with the rest of the bundle,
and must never land in `game/assets/authored/` (LICENSING.md). The committed
heroes keep their own generator, `tools/make_landmark.py`.

Heroes still never pass *through* `buildings.py` (`P2-1`): that stage only
removes the replaced source meshes, and this one rebuilds its replacements from
the same sheets — a stage of its own, so neither can smuggle policy into the
other. The two meet only at `export.py --check`'s set-equality.
"""

from __future__ import annotations

import argparse
import logging
import zipfile
from dataclasses import replace
from pathlib import Path, PurePosixPath

import numpy as np

from pipeline.buildings import COLLISION_SUFFIX, Placement, resolver, stem
from pipeline.config import CityConfig, Landmark, SourcePaint, load_city
from pipeline.documents import write_document
from pipeline.gltf import MeshData, read_scene, write_glb
from pipeline.mesh import merge, slice_horizontal, weld

log = logging.getLogger(__name__)

# The glTF material name that keeps a hero on the vertex-colour
# `BaseMaterial3D` import path. ≠ `city_facade`, deliberately:
# `generated_scene_import.gd` swaps that name for the tile shader, whose
# `TEXCOORD_0`/`TEXCOORD_1` payloads these models do not author. Shared with
# `tools/make_landmark.py`, which imports it from here so the two emitters
# cannot drift on the one name the engine dispatches on.
LANDMARK_MATERIAL = "landmark_vertex"

ASSETS_NAME = "landmark_assets.json"
ASSETS_SCHEMA = 1
# Under the region out dir, and mirrored under `res://assets/generated/` once
# `sync_generated.sh` copies the bundle — which is what makes the config's
# `LANDMARK_GENERATED_ROOT` asset paths true in the game tree.
ASSET_DIR = "landmarks"


def asset_relpath(landmark: Landmark) -> str:
    """The manifest-form POSIX path of a mesh-sourced hero's model."""
    return f"{ASSET_DIR}/{landmark.id}.glb"


def build_assets(
    city: CityConfig,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> dict:
    """Write every mesh-sourced hero and the document naming them.

    The document is written even when the city has no mesh-sourced landmark,
    so `export.py`'s input read is unconditional — a missing file means the
    stage never ran, not that there was nothing to do.
    """
    place = Placement.resolve(city, region_id, sources_root, out_root)
    transform = city.game_transform(region_id)
    high_x, high_z = city.region_high(region_id)

    assets = []
    for landmark in sorted(city.landmarks, key=lambda entry: entry.id):
        if landmark.source_paint is None:
            continue
        # Same rectangle filter as `export._landmarks_document`: a hero
        # belongs to the region that contains it, and building its asset into
        # another region's out tree would ship a model nothing places.
        x, _, z = transform.to_game(landmark.easting, landmark.northing, landmark.elevation)
        if not (0.0 <= x <= high_x and 0.0 <= z <= high_z):
            continue
        pieces = _source_meshes(place.sheets, set(landmark.replaces_source_ids), city)
        if not pieces:
            raise ValueError(
                f"landmark {landmark.id!r}: no source mesh matched stems "
                f"{sorted(landmark.replaces_source_ids)} in any sheet — check the "
                "stems against the sheet zips (fetch cache stale?)"
            )
        local = -np.asarray(
            transform.to_game(landmark.easting, landmark.northing, landmark.elevation),
            dtype=np.float64,
        ) + np.asarray(transform.to_game(0.0, 0.0, 0.0), dtype=np.float64)
        pieces = [piece.translated(local) for piece in pieces]

        read_count = sum(piece.triangle_count for piece in pieces)
        pieces = [slice_horizontal(piece, _band_planes(landmark.source_paint)) for piece in pieces]
        pieces = [paint(piece, landmark.source_paint) for piece in pieces]

        # Welded last: the paint needed unshared vertices, and carrying them
        # into the file would triple the vertex buffer for no visible change.
        mesh = replace(
            weld(merge(pieces, name=f"{landmark.id}{COLLISION_SUFFIX}")),
            material=LANDMARK_MATERIAL,
        )
        if mesh.triangle_count > landmark.triangle_budget:
            raise ValueError(
                f"landmark {landmark.id!r}: {mesh.triangle_count} triangles against a "
                f"budget of {landmark.triangle_budget} — measure, then re-pin "
                "triangle_budget in the city config rather than trimming here"
            )
        relative = asset_relpath(landmark)
        size = write_glb(place.out_dir / relative, [mesh])
        log.info(
            "  %s: %d source triangles, %d after slicing (budget %d), %.1f KB",
            landmark.id,
            read_count,
            mesh.triangle_count,
            landmark.triangle_budget,
            size / 1024,
        )
        assets.append(
            {
                "id": landmark.id,
                "path": relative,
                "triangles": mesh.triangle_count,
                "bytes": size,
                "stems": sorted(landmark.replaces_source_ids),
            }
        )

    document = {
        "schema_version": ASSETS_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        "assets": assets,
    }
    write_document(place.out_dir / ASSETS_NAME, document)
    return document


def _source_meshes(
    sheets: list[tuple[str, Path]], stems: set[str], city: CityConfig
) -> list[MeshData]:
    """Every non-terrain mesh in the sheets whose stem is in `stems`.

    The terrain class is skipped for the same reason `buildings.py` never
    excludes it: ground sharing a building's stem is ground, not building.
    Reads only the members it matched — a sheet unpacks to ~65 MB and a
    landmark needs one directory of it.
    """
    classes = tuple(name for name in city.buildings.classes if name != city.buildings.terrain_class)
    prefixes = tuple(f"{name}/" for name in classes)
    meshes: list[MeshData] = []
    matched_sheets: set[str] = set()
    for sheet_id, sheet_path in sheets:
        with zipfile.ZipFile(sheet_path) as archive:
            members = sorted(
                name
                for name in archive.namelist()
                if name.startswith(prefixes)
                and name.lower().endswith(".gltf")
                and stem(PurePosixPath(name).parent.name) in stems
            )
            for member in members:
                directory = str(PurePosixPath(member).parent)
                meshes.extend(read_scene(archive.read(member), resolver(archive, directory)))
                matched_sheets.add(sheet_id)
    if len(matched_sheets) > 1:
        # A stem matched on both sides of a sheet edge would ship its geometry
        # twice, coincident — z-fighting the exclusion was meant to end.
        log.warning(
            "  stems %s matched in %d sheets (%s): sheet-edge duplicate suspected",
            sorted(stems),
            len(matched_sheets),
            ", ".join(sorted(matched_sheets)),
        )
    return meshes


def _band_planes(spec: SourcePaint) -> list[float]:
    """Every elevation the paint changes at: ribbon edges and the base line."""
    planes = [spec.base_below_m]
    for index in range(spec.ribbon_count):
        low = spec.ribbon_first_m + index * spec.ribbon_pitch_m
        planes.extend((low, low + spec.ribbon_thickness_m))
    return planes


def paint(mesh: MeshData, spec: SourcePaint) -> MeshData:
    """Colour every triangle by facing and elevation, per `SourcePaint`.

    Per-triangle rather than per-vertex, which is only expressible because the
    mesh arrives unshared from `slice_horizontal` — and only crisp because it
    arrives sliced: no triangle spans a band edge, so a centroid test cannot
    disagree with any part of the triangle it colours.

    The source's own COLOR_0 (a uniform grey on every LandsD vertex) is
    overwritten, not blended: the repaint is the entire treatment.
    """
    # Facing comes from the authored normals, not the winding: they are what
    # the renderer shades with, so they are the facing the paint must agree
    # with. Source normals are face-constant and the slicer lerps them
    # exactly, so the per-triangle mean *is* the face normal.
    face_y = mesh.normals[mesh.triangles].mean(axis=1)[:, 1]
    centroid_y = mesh.triangle_centroids()[:, 1]

    ribbon = np.zeros(len(centroid_y), dtype=bool)
    if spec.ribbon_count > 0:
        level = np.floor((centroid_y - spec.ribbon_first_m) / spec.ribbon_pitch_m)
        offset = centroid_y - (spec.ribbon_first_m + level * spec.ribbon_pitch_m)
        ribbon = (level >= 0) & (level < spec.ribbon_count) & (offset < spec.ribbon_thickness_m)

    surface = np.full(len(centroid_y), 0, dtype=np.uint8)  # wall
    surface[ribbon] = 1
    surface[face_y >= spec.roof_normal_y] = 2
    surface[face_y <= -spec.soffit_normal_y] = 3
    surface[centroid_y < spec.base_below_m] = 3

    palette = np.array(
        [
            (*spec.wall.colour, 255),
            (*spec.ribbon.colour, 255),
            (*spec.roof.colour, 255),
            (*spec.base.colour, 255),
        ],
        dtype=np.uint8,
    )
    colours = np.zeros((len(mesh.positions), 4), dtype=np.uint8)
    colours[mesh.triangles.reshape(-1)] = np.repeat(palette[surface], 3, axis=0)
    return replace(mesh, colours=colours)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_city(args.city)
    region = city.region(args.region)
    log.info("%s / %s", city.name, region.name)

    document = build_assets(city, args.region)
    if not document["assets"]:
        log.info("  no mesh-sourced landmarks in this city; wrote an empty document")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
