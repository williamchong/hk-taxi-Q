"""Build the mesh-sourced hero landmarks: extract, slice, repaint, emit (`P3-6`).

    python -m pipeline.landmarks --region wan_chai

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
import io
import logging
import zipfile
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath

import numpy as np

from pipeline.buildings import COLLISION_SUFFIX, Placement, resolver, stem
from pipeline.colour import LUMA, srgb_to_linear
from pipeline.config import Config, Landmark, SourcePaint, load_config
from pipeline.crs import GameTransform
from pipeline.documents import write_document
from pipeline.fetch import source_dir
from pipeline.gltf import MeshData, normalise, read_scene, write_glb
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

# The sources-tree directory holding the individualised (`…A0`) sheet zips the
# photo reference reads — `sources/individualised/<sheet>.zip`. Named
# once for the same reason `buildings.SOURCE_ID` is: two spellings of a
# directory is how they come to disagree.
INDIVIDUALISED_SOURCE_ID = "individualised"


def asset_relpath(landmark: Landmark) -> str:
    """The manifest-form POSIX path of a mesh-sourced hero's model."""
    return f"{ASSET_DIR}/{landmark.id}.glb"


def landmark_in_region(
    landmark: Landmark, transform: GameTransform, high_x: float, high_z: float
) -> bool:
    """Whether the landmark's authored position stands inside the region.

    One definition on purpose: this stage decides which models to *build* and
    `export._landmarks_document` decides which entries to *place*, and the two
    disagreeing ships a model nothing places — the exact hole
    `_check_landmarks` exists to catch, manufactured in-house.
    """
    x, _, z = transform.to_game(landmark.easting, landmark.northing, landmark.elevation)
    return 0.0 <= x <= high_x and 0.0 <= z <= high_z


def build_assets(
    city: Config,
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
        spec = landmark.source_paint
        if spec is None:
            continue
        if not landmark_in_region(landmark, transform, high_x, high_z):
            continue
        stems = set(landmark.replaces_source_ids)
        pieces, matched_sheets = _source_meshes(place.sheets, stems, city)
        if not pieces:
            raise ValueError(
                f"landmark {landmark.id!r}: no source mesh matched stems "
                f"{sorted(stems)} in any sheet — check the "
                "stems against the sheet zips (fetch cache stale?)"
            )
        # `place.offset` is `game_offset(transform)`, so this is the authored
        # position subtracted in the sheet frame — the model lands back
        # exactly when `landmarks.json` places it.
        local = place.offset - np.asarray(
            transform.to_game(landmark.easting, landmark.northing, landmark.elevation),
            dtype=np.float64,
        )
        pieces = [piece.translated(local) for piece in pieces]

        reference = None
        if spec.reference_texture:
            directory = source_dir(INDIVIDUALISED_SOURCE_ID, root=sources_root)
            reference = _load_reference(directory, matched_sheets, stems, pieces, local)
            tagged, cursor = [], 0
            for piece in pieces:
                piece, cursor = _tag_parents(piece, cursor)
                tagged.append(piece)
            pieces = tagged

        read_count = sum(piece.triangle_count for piece in pieces)
        pieces = [slice_horizontal(piece, _band_planes(spec)) for piece in pieces]
        pieces = [paint(piece, spec, reference) for piece in pieces]

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
    sheets: list[tuple[str, Path]], stems: set[str], city: Config
) -> tuple[list[MeshData], set[str]]:
    """Every non-terrain mesh in the sheets whose stem is in `stems`, and the
    ids of the sheets that matched — the same sheets the photo reference must
    come from.

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
            for member in _matched_members(archive, stems, prefixes):
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
    return meshes, matched_sheets


def _matched_members(
    archive: zipfile.ZipFile, stems: set[str], prefixes: tuple[str, ...] = ()
) -> list[str]:
    """The archive's `.gltf` members whose directory stem is in `stems`.

    Sorted, the same load-bearing rule as `buildings.read_sheet`: member order
    decides vertex order, and an unstable order makes every output look
    changed. One helper so the C0 and A0 walks cannot drift on the filter.
    """
    return sorted(
        name
        for name in archive.namelist()
        if (not prefixes or name.startswith(prefixes))
        and name.lower().endswith(".gltf")
        and stem(PurePosixPath(name).parent.name) in stems
    )


def _band_planes(spec: SourcePaint) -> list[float]:
    """Every elevation the paint changes at: ribbon edges and the base line."""
    planes = [spec.base_below_m]
    for index in range(spec.ribbon_count):
        low = spec.ribbon_first_m + index * spec.ribbon_pitch_m
        planes.extend((low, low + spec.ribbon_thickness_m))
    return planes


@dataclass(frozen=True)
class Reference:
    """The photo half of the paint: each source triangle's place in the
    individualised (`…A0`) texture atlas.

    Indexed by the parent-triangle ids `_tag_parents` threads through the
    slicer, so a sliced fragment can be sampled at its own position inside
    the parent it came from. `image` is -1 where the A0 variant had no match
    or no texture — those triangles keep the procedural verdict.
    """

    corners: np.ndarray  # (t, 3, 3) parent corners, landmark local frame
    uvs: np.ndarray  # (t, 3, 2) the A0 atlas coordinates at those corners
    image: np.ndarray  # (t,) int32 index into `luminance`, -1 = no photo
    luminance: tuple[np.ndarray, ...]  # decoded atlases as linear luminance


def _tag_parents(mesh: MeshData, start: int) -> tuple[MeshData, int]:
    """Write each triangle's global id into a scratch UV channel.

    The id is constant across a triangle's three corners, so
    `slice_horizontal`'s lerp reproduces it exactly on every fragment — the
    one per-triangle payload that survives slicing without bookkeeping.
    `paint` strips the channel; nothing shipped carries it.
    """
    if mesh.uvs is not None:
        raise ValueError(f"mesh '{mesh.name}' already carries UVs; refusing to overwrite")
    ids = np.arange(start, start + mesh.triangle_count, dtype=np.float32)
    uvs = np.zeros((len(mesh.positions), 2), dtype=np.float32)
    uvs[mesh.triangles.reshape(-1), 0] = np.repeat(ids, 3)
    return replace(mesh, uvs=uvs), start + mesh.triangle_count


def _corner_keys(mesh: MeshData) -> list[tuple]:
    """One order-independent key per triangle, from its mm-rounded corners.

    The A0 and C0 variants carry the same geometry ("not one triangle of
    extra shape" — DATA_SOURCES.md), but nothing promises the same triangle
    order or winding, so identity is the sorted corner set.
    """
    corners = np.round(mesh.positions[mesh.triangles], 3)
    return [tuple(sorted(map(tuple, triangle))) for triangle in corners.tolist()]


def _load_reference(
    directory: Path,
    sheet_ids: set[str],
    stems: set[str],
    pieces: list[MeshData],
    offset: np.ndarray,
) -> Reference:
    """Match every source triangle to its photo, via the A0 variant.

    Imports Pillow lazily: image decoding stays off the pipeline's critical
    path for every city that never opts into `reference_texture`, which keeps
    the letter of the pyproject note that put Pillow in the dev extras.
    """
    try:
        from PIL import Image
    except ImportError as error:  # pragma: no cover - environment-dependent
        raise ValueError(
            "reference_texture needs Pillow to decode the photo atlases — "
            "install the dev extras (pip install -e 'etl/[dev]')"
        ) from error

    # `colour.luminance` per pixel, as a 256-entry table: the atlases arrive
    # as uint8, and evaluating the sRGB curve over 50M floats per 4096² atlas
    # was measured at ~70% of the whole stage (both `np.where` branches run).
    # The table is the same curve at the only 256 inputs that exist, so the
    # result is exact, and CIE weights keep this the one definition of
    # luminance the repo has (`colour.py` claims exactly that ownership).
    lut = srgb_to_linear(np.arange(256, dtype=np.float64)).astype(np.float32)

    lookup: dict[tuple, tuple[int, int]] = {}
    images: list[np.ndarray] = []
    a0_pieces: list[MeshData] = []
    for sheet_id in sorted(sheet_ids):
        path = directory / f"{sheet_id}.zip"
        if not path.exists():
            raise ValueError(
                f"reference_texture needs {path}, which is not on disk — the "
                "individualised sheet download is documented in DATA_SOURCES.md"
            )
        with zipfile.ZipFile(path) as archive:
            for member in _matched_members(archive, stems):
                member_dir = str(PurePosixPath(member).parent)
                for piece in read_scene(archive.read(member), resolver(archive, member_dir)):
                    if piece.texture is None or piece.uvs is None:
                        continue
                    decoded = np.asarray(Image.open(io.BytesIO(piece.texture.data)).convert("RGB"))
                    image_id = len(images)
                    images.append(
                        lut[decoded[..., 0]] * np.float32(LUMA[0])
                        + lut[decoded[..., 1]] * np.float32(LUMA[1])
                        + lut[decoded[..., 2]] * np.float32(LUMA[2])
                    )
                    local = piece.translated(offset)
                    a0_pieces.append(local)
                    for index, key in enumerate(_corner_keys(local)):
                        lookup[key] = (image_id, index)

    total = sum(piece.triangle_count for piece in pieces)
    corners = np.zeros((total, 3, 3), dtype=np.float64)
    uvs = np.zeros((total, 3, 2), dtype=np.float32)
    image = np.full(total, -1, dtype=np.int32)
    cursor = 0
    matched = 0
    for piece in pieces:
        for index, key in enumerate(_corner_keys(piece)):
            hit = lookup.get(key)
            if hit is None:
                continue
            image_id, a0_index = hit
            a0 = a0_pieces[image_id]
            corners[cursor + index] = a0.positions[a0.triangles[a0_index]]
            uvs[cursor + index] = a0.uvs[a0.triangles[a0_index]]
            image[cursor + index] = image_id
            matched += 1
        cursor += piece.triangle_count

    share = matched / total if total else 0.0
    if share < 0.9:
        raise ValueError(
            f"reference_texture matched only {share:.1%} of source triangles to the "
            "A0 variant — the two variants should share their geometry, so this is "
            "a stale or mismatched individualised sheet"
        )
    if share < 1.0:
        log.warning("  reference: %.2f%% of triangles carry no photo", 100 * (1 - share))
    return Reference(corners=corners, uvs=uvs, image=image, luminance=tuple(images))


def _sample_reference(
    mesh: MeshData, reference: Reference, lift_m: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """Median linear luminance of each sliced triangle's photo, and whether
    the samples were usable.

    Four sample points (centroid and edge midpoints), each mapped into the
    parent triangle's barycentric frame and through its A0 atlas coordinates.
    Median rather than mean so one sample landing on a window frame or an
    atlas seam cannot drag the verdict.

    `lift_m` shifts every sample vertically before mapping — how the caller
    reads the wall *next to* a band rather than the band itself. Walls are
    planar, so a vertical shift stays on the surface; a shifted sample that
    leaves its parent triangle is discarded rather than clamped, because a
    clamped coordinate would silently read some other storey's pixels. A
    triangle is usable when it has a photo and at least one sample survived.
    """
    parent = np.rint(mesh.uvs[mesh.triangles[:, 0], 0]).astype(np.int64)
    image = reference.image[parent]

    corners = mesh.positions[mesh.triangles]
    samples = np.concatenate(
        [
            corners.mean(axis=1, keepdims=True),
            (corners + np.roll(corners, -1, axis=1)) / 2.0,
        ],
        axis=1,
    )  # (m, 4, 3)
    if lift_m:
        samples = samples + np.asarray([0.0, lift_m, 0.0])

    parent_corners = reference.corners[parent]  # (m, 3, 3)
    a = parent_corners[:, 0][:, None, :]
    edge1 = (parent_corners[:, 1] - parent_corners[:, 0])[:, None, :]
    edge2 = (parent_corners[:, 2] - parent_corners[:, 0])[:, None, :]
    to_sample = samples - a
    d11 = (edge1 * edge1).sum(axis=2)
    d12 = (edge1 * edge2).sum(axis=2)
    d22 = (edge2 * edge2).sum(axis=2)
    dp1 = (to_sample * edge1).sum(axis=2)
    dp2 = (to_sample * edge2).sum(axis=2)
    denominator = d11 * d22 - d12 * d12
    denominator[denominator == 0] = 1.0
    v = (d22 * dp1 - d12 * dp2) / denominator
    w = (d11 * dp2 - d12 * dp1) / denominator
    u = 1.0 - v - w
    inside = (
        (u > -0.02) & (v > -0.02) & (w > -0.02) & (u < 1.02) & (v < 1.02) & (w < 1.02)
    )  # (m, 4)

    parent_uvs = reference.uvs[parent]  # (m, 3, 2)
    uv = (
        u[..., None] * parent_uvs[:, 0][:, None, :]
        + v[..., None] * parent_uvs[:, 1][:, None, :]
        + w[..., None] * parent_uvs[:, 2][:, None, :]
    ).clip(0.0, 1.0)  # (m, 4, 2)

    luminance = np.zeros(len(corners), dtype=np.float32)
    usable = (image >= 0) & inside.any(axis=1)
    for image_id, atlas in enumerate(reference.luminance):
        rows = np.nonzero(usable & (image == image_id))[0]
        if not len(rows):
            continue
        height, width = atlas.shape
        columns = np.rint(uv[rows, :, 0] * (width - 1)).astype(np.int64)
        lines = np.rint(uv[rows, :, 1] * (height - 1)).astype(np.int64)
        values = np.ma.masked_array(atlas[lines, columns], mask=~inside[rows])
        luminance[rows] = np.ma.median(values, axis=1).filled(0.0)
    return luminance, usable


def _adjacency(mesh: MeshData) -> tuple[list[list[int]], np.ndarray]:
    """Edge-sharing neighbours per triangle, and unit face normals.

    Shared by region growth and strip components. Edges are keyed on rounded
    corner positions, so the unshared vertices the slicer emits still count
    as the same edge on both sides.
    """
    corners = np.round(mesh.positions, 4)[mesh.triangles]
    normals = normalise(mesh.normals[mesh.triangles].mean(axis=1).astype(np.float64))

    first: dict[tuple, int] = {}
    neighbours: list[list[int]] = [[] for _ in range(len(corners))]
    for index, triangle in enumerate(corners):
        rows = [tuple(row) for row in triangle.tolist()]
        for edge in ((0, 1), (1, 2), (2, 0)):
            key = tuple(sorted((rows[edge[0]], rows[edge[1]])))
            other = first.setdefault(key, index)
            if other != index:
                neighbours[index].append(other)
                neighbours[other].append(index)
    return neighbours, normals


def _grown(
    seeds: np.ndarray, neighbours: list[list[int]], normals: np.ndarray, crease_deg: float
) -> np.ndarray:
    """Every triangle a seed reaches without crossing a crease.

    A surface is what it is everywhere it stays smooth: the wing roof rolls
    from flat to near-vertical without a crease, so a normal threshold cannot
    follow it, but adjacency can. Growth crosses an edge only where the two
    faces meet at less than `crease_deg` — the eave where roof actually
    becomes wall is a crease, and growth stops there. Slicing only adds
    coplanar edges, so it never blocks or leaks growth.
    """
    if not seeds.any():
        return seeds.copy()
    limit = float(np.cos(np.radians(crease_deg)))
    grown = seeds.copy()
    stack = list(np.nonzero(seeds)[0])
    while stack:
        current = stack.pop()
        for neighbour in neighbours[current]:
            if not grown[neighbour] and float(normals[current] @ normals[neighbour]) >= limit:
                grown[neighbour] = True
                stack.append(neighbour)
    return grown


def _components(mask: np.ndarray, neighbours: list[list[int]]) -> np.ndarray:
    """Connected-component label per masked triangle, -1 outside the mask.

    No crease limit: within one wall the hull curves gently and the slicer's
    cuts are coplanar, while the surfaces that must not join a wall — the
    grown roofs and soffits — are excluded by the mask itself, so their
    creases never even come up.
    """
    labels = np.full(len(mask), -1, dtype=np.int64)
    label = 0
    for start in np.nonzero(mask)[0]:
        if labels[start] != -1:
            continue
        stack = [int(start)]
        labels[start] = label
        while stack:
            current = stack.pop()
            for neighbour in neighbours[current]:
                if mask[neighbour] and labels[neighbour] == -1:
                    labels[neighbour] = label
                    stack.append(neighbour)
        label += 1
    return labels


def paint(mesh: MeshData, spec: SourcePaint, reference: Reference | None = None) -> MeshData:
    """Colour every triangle by surface, elevation, and — when referenced —
    the building's own photo.

    Per-triangle rather than per-vertex, which is only expressible because the
    mesh arrives unshared from `slice_horizontal` — and only crisp because it
    arrives sliced: no triangle spans a band edge, so a centroid test cannot
    disagree with any part of the triangle it colours.

    Roof and soffit are *grown* from their normal-threshold seeds across
    smooth adjacency (`_grown`), so the curved sweeps stay one surface to
    their edges instead of turning into banded wall past the threshold — the
    defect the first repaint shipped. With a `Reference`, a ribbon strip
    additionally survives only where the photo confirms glazing, one whole
    band level per connected wall at a time — the strip logic below carries
    the argument; strips the photo cannot decide keep the procedural verdict.

    The source's own COLOR_0 (a uniform grey on every LandsD vertex) is
    overwritten, not blended: the repaint is the entire treatment.
    """
    if reference is not None and mesh.uvs is None:
        # `_sample_reference` reads parent ids out of the scratch UV channel;
        # real texture coordinates in it would silently sample the wrong
        # photo triangles, so their absence is checked, loudly, here.
        raise ValueError(
            f"mesh '{mesh.name}': reference paint needs the parent-id channel — "
            "_tag_parents before slice_horizontal"
        )
    centroid_y = mesh.triangle_centroids()[:, 1]
    # Facing comes from the authored normals, not the winding: they are what
    # the renderer shades with, so they are the facing the paint must agree
    # with. Source normals are face-constant and the slicer lerps them
    # exactly, so `_adjacency`'s per-triangle mean *is* the face normal.
    neighbours, normals = _adjacency(mesh)
    face_y = normals[:, 1]

    roof = _grown(face_y >= spec.roof_normal_y, neighbours, normals, spec.crease_deg)
    soffit = _grown(face_y <= -spec.soffit_normal_y, neighbours, normals, spec.crease_deg)

    ribbon = np.zeros(len(centroid_y), dtype=bool)
    level = np.zeros(len(centroid_y), dtype=np.int64)
    if spec.ribbon_count > 0:
        level = np.floor((centroid_y - spec.ribbon_first_m) / spec.ribbon_pitch_m).astype(np.int64)
        offset = centroid_y - (spec.ribbon_first_m + level * spec.ribbon_pitch_m)
        ribbon = (level >= 0) & (level < spec.ribbon_count) & (offset < spec.ribbon_thickness_m)
    ribbon &= ~(roof | soffit)

    if reference is not None and ribbon.any():
        # The verdict is per *strip*, not per triangle: a ribbon is a
        # continuous storey line, so one band level on one connected wall is
        # one decision, taken on the median photo contrast of its triangles.
        # Per-triangle verdicts turned photo noise into broken dashes.
        #
        # The contrast itself is local and vertical, not an absolute darkness
        # cut: the aerial bakes sun and shade at many times the glazing's own
        # contrast (wall luminance spans ~0.03-0.66 across facings), so the
        # only fair comparison for a band sample is the wall half a pitch
        # above and below it — same plan position, same lighting, glazing the
        # only difference. Uniform surfaces (the sweeps, the fasciae)
        # contrast at ~1.0 and lose their strips; real glazing reads darker
        # and keeps them. Strips the photo cannot decide — no coverage, or
        # parents too short for a neighbour sample — keep the procedural
        # verdict.
        luminance, sampled = _sample_reference(mesh, reference)
        above, has_above = _sample_reference(mesh, reference, spec.ribbon_pitch_m / 2.0)
        below, has_below = _sample_reference(mesh, reference, -spec.ribbon_pitch_m / 2.0)
        beside = np.ma.masked_array(
            np.stack([above, below]), mask=~np.stack([has_above, has_below])
        )
        neighbour = np.ma.mean(beside, axis=0).filled(0.0)
        decidable = ribbon & sampled & (has_above | has_below) & (neighbour > 0)

        wall_component = _components(~roof & ~soffit, neighbours)
        contrast = np.ones(len(centroid_y))
        contrast[decidable] = luminance[decidable] / neighbour[decidable]
        strips: dict[tuple[int, int], list[int]] = {}
        for index in np.nonzero(ribbon)[0]:
            strips.setdefault((int(wall_component[index]), int(level[index])), []).append(
                int(index)
            )
        for members in strips.values():
            rows = np.asarray(members)
            decided = rows[decidable[rows]]
            if len(decided) < 5:
                # An evidence floor, not a tuning value: fewer samples than
                # this is one parent triangle's worth, where a single seam or
                # window frame decides the whole strip. The measured layout
                # outranks that little photo.
                continue
            if float(np.median(contrast[decided])) >= spec.veto_ratio:
                ribbon[rows] = False

    surface = np.full(len(centroid_y), 0, dtype=np.uint8)  # wall
    surface[ribbon] = 1
    surface[roof] = 2
    surface[soffit] = 3
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
    return replace(mesh, colours=colours, uvs=None)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--region", required=True)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_config()
    region = city.region(args.region)
    log.info("%s / %s", city.name, region.name)

    document = build_assets(city, args.region)
    if not document["assets"]:
        log.info("  no mesh-sourced landmarks in this city; wrote an empty document")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
