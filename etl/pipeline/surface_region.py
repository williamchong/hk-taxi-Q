"""What `surface.py` takes from `carriageway_region.json` (`Q129`, `P3-33c`).

Two things, and the split is the design:

* **Rails.** A level-0 ribbon's two rails at every station are its territory's
  own left and right extents, not `± width_m / 2` — `Q107`'s per-station,
  per-side clamp, generalised from decks to the street. The ribbon keeps
  everything it carried: the lane coordinate, the restriction alpha, the
  markings codec, the rails `DrawnSurface` reads. `stations` is that half.
* **Areas.** Everything else of R — the junctions, the flares, a territory
  wider than any cross-section sees — is `R - (every ribbon)`, cut per owner,
  triangulated, and stood at its owner's centreline height. It is drawn as
  `MARKING_CLASS_CAP`, because it is no length of lane, and it replaces the hull
  caps, the through corridors and the paint flanks at level 0: a union cannot
  overlap itself, leave a gap inside a junction, or bury a kerb. `areas` is
  that half.

🔴 **The seam (`Q116`), restated from `P3-33b`'s first reading of it.** A run's
RIBBON is its owner's, whole — territory rails inside the owner's rectangle and
the plain `width_m` ribbon past it, where this build knows none of the
centrelines it would compete with. Every other square metre of R is drawn by
the region whose rectangle holds it. So the neighbour's runs reaching in are
SUBTRACTED here as ribbons — `surface.py` already shapes them from the identical
record, which is what makes the two builds' polygons agree — and the rest of
their territory is this region's to draw as area. No hole, no double-draw, and
the owner's `DrawnSurface` still covers its far half for the paint layers.

⚠️ Kept out of `surface.py` so that stage does not import `shapely` for the
levels and the cities that never build a region.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from itertools import pairwise
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry

from pipeline.polyline import true_runs
from pipeline.region import KERB, REGION_NAME, read_region

# Every overlay here runs on a millimetre grid. The ribbons' rails and R's rings
# were computed apart, so without one a rail that lies ON a kerb by construction
# misses it by 1e-13 and the difference is a ribbon-long sliver a micron wide.
_GRID_M = 0.001
# An area piece under this is an overlay crumb, not asphalt.
_MIN_PIECE_M2 = 0.01

Key = tuple[bool, int]


@dataclass
class Stations:
    """One territory's extents, by distance along the PUBLISHED polyline."""

    along_m: np.ndarray
    left_m: np.ndarray
    right_m: np.ndarray
    # 1.0 where that side ended at R's own boundary — a kerb — and 0.0 where it
    # ended in another territory, which is asphalt and takes no kerb.
    kerb_left: np.ndarray
    kerb_right: np.ndarray
    # Kerb to kerb, through every share: the corridor, where the two above are
    # this centreline's share of it.
    left_kerb_m: np.ndarray
    right_kerb_m: np.ndarray
    vertex_station: np.ndarray


def bridged(stations: Stations) -> Stations:
    """The extents with every OPENING bridged along the kerb line either side of it.

    🔴 **A territory bulges into every side-street mouth, and a rail that follows
    it makes a straight road broaden and shrink** — found from the driving seat.
    The main road's Voronoi cell reaches into the opening as far as the bisector
    with the side street, so at the mouth its extent runs metres past the kerb
    line: 80 openings on 58 Wan Chai edges by more than 0.5 m, FLEMING ROAD
    `e264` by 11.63 m, and the lane coordinate stretches with it.

    So where a run of stations ending in a SHARE stands between two that end at a
    KERB, the rail may not pass the straight line between those two kerbs. It only
    ever narrows — `min` with the measured extent — and nothing is lost: the
    areas are `R - ribbons`, so the mouth is drawn as the junction asphalt it is.
    ⚠️ A share run that reaches an END of the edge is left alone: that is a
    carriageway shared with another centreline (GLOUCESTER ROAD), or a junction
    the trim already covers, and there is no second kerb to draw the line to.
    ⚠️ The published extents are untouched — `carriageway_region.json` is the
    measurement, and this is `surface.py`'s reading of it.
    """
    sides = {}
    for name, extent, kerb in (
        ("left_m", stations.left_m, stations.kerb_left),
        ("right_m", stations.right_m, stations.kerb_right),
    ):
        out = extent.copy()
        at_kerb = np.flatnonzero(kerb >= 0.5)
        for low, high in pairwise(at_kerb):
            if high - low < 2:
                continue
            inner = np.arange(low + 1, high)
            line = np.interp(
                stations.along_m[inner],
                stations.along_m[[low, high]],
                extent[[low, high]],
            )
            out[inner] = np.minimum(extent[inner], line)
        sides[name] = out
    return replace(stations, **sides)


# How far a rail may be let go of its kerb before that kerb stops being drawn
# along it. Above the document's millimetre rounding, below anything a kerb is.
_OFF_KERB_M = 0.05


def opened(stations: Stations, window_m: float, bump_m: float) -> Stations:
    """The extents with every outward bump SHORTER than `window_m` taken off.

    🔴 **A ribbon carries the lane coordinate, so its rail has to be the road's
    running kerb line and not everything the territory reaches.** After
    `bridged`, 467 mid-block sides on Wan Chai still stood more than 0.75 m off
    their own 20 m median, and two classes of it are outward: a cross-section
    that ends at a KERB further away — a lay-by, a bus bay, the mouth of a road
    with no centreline (164 sides, ~958 m) — and a SHARE that bulges where
    `bridged` has no second kerb to draw a line to (141 sides, ~872 m).

    A morphological OPENING of each side along the road: the running minimum
    over `window_m`, then the running maximum of that. Three properties, and
    they are why it is this and not a smoother:

    * it **never widens** — the result is `<=` the measured extent everywhere, so
      a ribbon cannot be drawn over an island or over a neighbour's ribbon;
    * it **leaves a monotone taper exactly alone**, so a road that really widens
      keeps its shape, and so does the wedge a territory pinches to at its node;
    * a bump of `window_m` or longer survives whole — that is a carriageway, not
      a bay.

    Nothing is lost: the areas are `R - ribbons`, so what the rail lets go of is
    drawn as the asphalt it is. ⚠️ The INWARD classes — a traffic island (90
    sides), a short link's territory intruding (72) — are deliberately not
    touched: closing them would be the widening the first property refuses.

    🔴 **A side let go of its kerb stops being a kerb.** The flag drives the kerb
    strip, which is drawn ALONG THE RAIL: left set, a riser would stand across
    the mouth of every bay this straightens past.
    """
    if window_m <= 0.0 or len(stations.along_m) < 3:
        return stations
    # 🔴 **Only the stations clear of the two MOUTHS take part.** A territory
    # pinches to a wedge at each node, so an edge shorter than the window is, end
    # to end, one bump — and the first build collapsed HENNESSY ROAD `e0`, 11 m
    # long, to its wedge width with the lane centre on the centreline. Inside
    # half a median span of either node the extent is the junction's business and
    # the trim's, and it is left exactly as measured.
    reach = 0.5 * float(np.median(stations.left_m + stations.right_m))
    inner = np.flatnonzero(
        (stations.along_m >= reach) & (stations.along_m <= stations.along_m[-1] - reach)
    )
    if len(inner) < 3:
        return stations
    along = stations.along_m[inner]
    low = np.searchsorted(along, along - window_m / 2.0, side="left")
    high = np.searchsorted(along, along + window_m / 2.0, side="right")

    def sliding(values: np.ndarray, pick) -> np.ndarray:
        return np.array([pick(values[a:b]) for a, b in zip(low, high, strict=True)])

    changed = {}
    for extent_name, kerb_name in (("left_m", "kerb_left"), ("right_m", "kerb_right")):
        whole = getattr(stations, extent_name)
        extent = whole[inner]
        lower = np.minimum(sliding(sliding(extent, np.min), np.max), extent)
        # 🔴 **Per BUMP, and only a bump standing out by more than `bump_m` at its
        # peak.** An opening flattens every outward feature, centimetre kerb
        # jitter included: applied whole at 30 m it moved 33,400 m2 of Wan Chai
        # from ribbon to area and cleared 27% of the kerb flags, for bumps that
        # total ~3,000 m2. A run is let go WHOLE or kept whole, so a rail never
        # flickers between the two inside one bay.
        rail = extent.copy()
        # ⚠️ A run is where the rail stands out by more than the BAR, not by more
        # than a hair: kerb jitter puts almost every station a few centimetres
        # over its opening, so runs cut at a hair merge every bump on the edge
        # into one that reaches both ends — and the guards below then skip it.
        over = extent - lower > bump_m
        for start, stop in true_runs(over):
            # 🔴 A bay has ROAD either side of it. A run reaching an end of the
            # interior is the edge's own body standing between its two wedges —
            # which on an edge shorter than the window is the whole edge — and an
            # opening cannot tell the two apart, so this does.
            # ⚠️ And "road" is a quarter of a window of kept rail, not one station:
            # what is left of a wedge inside the interior is a station or two at
            # each end, and a body standing between two of those is still a body.
            if start == 0 or stop == len(extent):
                continue
            flank = window_m / 4.0
            if along[start] - along[0] < flank or along[-1] - along[stop - 1] < flank:
                continue
            rail[start:stop] = lower[start:stop]
        out, kerb = whole.copy(), getattr(stations, kerb_name).copy()
        out[inner] = rail
        kerb[inner] = np.where(rail < extent - _OFF_KERB_M, 0.0, kerb[inner])
        changed[extent_name], changed[kerb_name] = out, kerb
    return replace(stations, **changed)


def flare_m(stations: Stations, window_m: float, bump_m: float) -> tuple[float, float]:
    """How far in from each node this territory is still the JUNCTION's shape.

    🔴 **A carriageway widens toward a junction — a bell-mouth, a turning pocket —
    and that is not a bump to filter, it is where the ribbon should not yet have
    started.** Of 351 Wan Chai sides bumping > 0.75 m off their own median, 300
    do it within 25 m of a node, where `opened` rightly refuses to flatten
    anything. The junction trim was a radius guessed from `width_m`; this is the
    same distance READ: walking in from the node, the first station where both
    sides sit within `bump_m` of their own median over the next `window_m`. Past
    it the lane lines run parallel; before it the asphalt is junction, and the
    areas draw it.

    `(from the start, from the end)`, in metres; zero where the edge is settled
    from its first station. The caller caps it — an edge that never settles is
    all junction, which `junction_trim_max_fraction` already has a rule for.
    """
    along = stations.along_m
    total = float(along[-1])

    def settled(index: int, forward: bool) -> bool:
        if forward:
            ahead = (along >= along[index]) & (along <= along[index] + window_m)
        else:
            ahead = (along <= along[index]) & (along >= along[index] - window_m)
        return all(
            abs(side[index] - float(np.median(side[ahead]))) <= bump_m
            for side in (stations.left_m, stations.right_m)
        )

    start = next((i for i in range(len(along)) if settled(i, True)), len(along) - 1)
    end = next((i for i in reversed(range(len(along))) if settled(i, False)), 0)
    return float(along[start]), total - float(along[end])


@dataclass
class Region:
    whole: BaseGeometry
    shapes: dict[Key, BaseGeometry]
    stations: dict[Key, Stations]
    # Kerbed islands standing IN the carriageway (`region.islands_of`). A
    # territory's extent is read through one, so a ribbon is drawn over it and
    # the island owes its kerb back: `areas` rings every one, under a ribbon or not.
    islands: list[Polygon] = field(default_factory=list)


def _polygonal(shape: BaseGeometry) -> BaseGeometry:
    """The polygons of a geometry and nothing else.

    `make_valid` on a ring that crosses itself — a ribbon outline on a tight
    bend — hands back a collection with the crossing left in as a line, and GEOS
    refuses to overlay a mixed-dimension input.
    """
    parts = [part for part in shapely.get_parts(shape) if part.geom_type == "Polygon"]
    return shapely.union_all(parts) if parts else Polygon()


def _shape(rows: list[dict]) -> BaseGeometry:
    if not rows:
        return Polygon()
    # Repaired on the way in: the document rounds to a millimetre, which pinches
    # the odd ring shut on itself, and GEOS refuses the union of an invalid one
    # ("side location conflict"). Repaired, never dropped — it is asphalt.
    polygons = np.asarray([Polygon(row["outer"], row["holes"]) for row in rows], dtype=object)
    return _polygonal(shapely.union_all(shapely.make_valid(polygons)))


def read(out_dir: Path, region_id: str) -> Region:
    document = read_region(out_dir / REGION_NAME, region_id)
    shapes: dict[Key, BaseGeometry] = {}
    stations: dict[Key, Stations] = {}
    for row in document["territories"]:
        key = (bool(row["foreign"]), int(row["edge"]))
        shapes[key] = _shape(row["rings"])
        stations[key] = Stations(
            along_m=np.asarray(row["along_m"], dtype=np.float64),
            left_m=np.asarray(row["left_m"], dtype=np.float64),
            right_m=np.asarray(row["right_m"], dtype=np.float64),
            kerb_left=np.asarray([end == KERB for end in row["left_end"]], dtype=np.float64),
            kerb_right=np.asarray([end == KERB for end in row["right_end"]], dtype=np.float64),
            left_kerb_m=np.asarray(row["left_kerb_m"], dtype=np.float64),
            right_kerb_m=np.asarray(row["right_kerb_m"], dtype=np.float64),
            vertex_station=np.asarray(row["vertex_station"], dtype=int),
        )
    whole = _shape([*document["region"]["hyd"], *document["region"]["rails"]])
    islands = [Polygon(ring) for ring in document["region"]["islands"] if len(ring) >= 4]
    return Region(whole=whole, shapes=shapes, stations=stations, islands=islands)


def _heights(centreline: np.ndarray, plan: np.ndarray) -> np.ndarray:
    """The owner's centreline height under each plan point — flat across the road,
    which is the cross-section every ribbon here already has."""
    step = np.diff(centreline[:, [0, 2]], axis=0)
    along = np.r_[0.0, np.cumsum(np.hypot(step[:, 0], step[:, 1]))]
    line = shapely.LineString(centreline[:, [0, 2]])
    at = shapely.line_locate_point(line, shapely.points(plan))
    return np.interp(at, along, centreline[:, 1])


def _key_of(plan: np.ndarray) -> np.ndarray:
    return np.round(plan / _GRID_M).astype(np.int64)


def _face_up(triangles: np.ndarray) -> np.ndarray:
    """`(n, 3, 3)` triangles, each wound so its face points up: `surface._shoelace`
    negative."""
    x, z = triangles[:, :, 0], triangles[:, :, 2]
    twice = (x * np.roll(z, -1, axis=1) - np.roll(x, -1, axis=1) * z).sum(axis=1)
    triangles[twice > 0.0] = triangles[twice > 0.0][:, ::-1]
    return triangles


def _owners(
    region: Region, centrelines: dict[Key, np.ndarray]
) -> tuple[list[Key], shapely.STRtree | None]:
    """The territories a height can be read from, and the index over them."""
    owners = [
        key for key, shape in region.shapes.items() if key in centrelines and not shape.is_empty
    ]
    return owners, shapely.STRtree([region.shapes[key] for key in owners]) if owners else None


def areas(
    region: Region,
    ribbons: list[np.ndarray],
    centrelines: dict[Key, np.ndarray],
    rails: list[np.ndarray],
    high: tuple[float, float] | None = None,
    kerbed: list[np.ndarray] | None = None,
    kerb_width_m: float = 0.0,
    tolerance_m: float = 0.0,
    island_band: BaseGeometry | None = None,
) -> tuple[np.ndarray, list[np.ndarray]]:
    """`R - ribbons` as `(n, 3, 3)` triangles, each wound to face up — and the
    KERB LINES of it: `(N, 3)` polylines along every stretch of R's own boundary
    that an area meets, walked with the road on the RIGHT.

    `ribbons` are the plan outlines of every level-0 ribbon, the neighbour's
    included; `centrelines` the `(N, 3)` polyline each owner's height is read
    from; `rails` the drawn rails' `(N, 3)` positions.

    🔴 **A vertex standing on a drawn rail takes THAT rail's height**, and one
    shared by two owners' pieces takes the mean of theirs. Two owners at
    different heights meet on a line; left alone that line is a crack the car's
    wheel reads and `paint_clearance`'s `deeper than` row counts. The rail wins
    outright because the ribbon is what carries paint, and a mean there would
    move the road under it.
    """
    drawn = (
        _polygonal(
            shapely.union_all(
                shapely.make_valid(np.asarray([Polygon(ring) for ring in ribbons], dtype=object))
            )
        )
        if ribbons
        else Polygon()
    )
    rest = shapely.difference(
        shapely.set_precision(region.whole, _GRID_M),
        shapely.set_precision(drawn, _GRID_M),
        grid_size=_GRID_M,
    )
    pieces = [
        part
        for part in shapely.get_parts(rest)
        if part.geom_type == "Polygon" and part.area > _MIN_PIECE_M2
    ]
    if not pieces:
        return np.zeros((0, 3, 3)), []
    # 🔴 **Triangulated WHOLE, not per owner.** Cut by territory first, every
    # boundary between two owners arrives carrying a vertex per Voronoi site —
    # 272,248 triangles on Wan Chai where the surface it replaces had 32,177 —
    # and the cut buys nothing: a triangle spanning two owners interpolates
    # between their heights, which is what the seam between them should do.
    triangles = shapely.get_parts(
        shapely.constrained_delaunay_triangles(shapely.multipolygons(pieces))
    )
    plan = np.asarray([np.asarray(tri.exterior.coords)[:3] for tri in triangles])
    if not len(plan):
        return np.zeros((0, 3, 3)), []

    # One height per plan position: the mean of every owner whose territory
    # reaches it, so two owners at different heights meet in a shared vertex
    # rather than along a crack.
    keys = _key_of(plan.reshape(-1, 2))
    unique, group = np.unique(keys, axis=0, return_inverse=True)
    group = group.reshape(-1)
    at = unique * _GRID_M
    owners, tree = _owners(region, centrelines)
    found, owner = tree.query(shapely.points(at), predicate="dwithin", distance=2.0 * _GRID_M)
    total, count = np.zeros(len(at)), np.zeros(len(at))
    for index in np.unique(owner):
        rows = found[owner == index]
        total[rows] += _heights(centrelines[owners[index]], at[rows])
        count[rows] += 1.0
    # A crumb of R no territory claims takes the nearest owner's height.
    for row in np.flatnonzero(count == 0.0):
        nearest = owners[int(tree.nearest(shapely.points(at[row])))]
        total[row], count[row] = _heights(centrelines[nearest], at[row : row + 1])[0], 1.0
    mean = total / count
    flat = mean[group]
    if rails:
        rail = np.vstack(rails)
        pinned = {tuple(k): y for k, y in zip(_key_of(rail[:, [0, 2]]), rail[:, 1], strict=True)}
        for index, k in enumerate(map(tuple, keys)):
            if k in pinned:
                flat[index] = pinned[k]
    out = _face_up(np.stack([plan[:, :, 0], flat.reshape(-1, 3), plan[:, :, 1]], axis=2))
    clip = shapely.box(0.0, 0.0, *high) if high is not None else None
    drawn_kerbs = (
        shapely.union_all([shapely.LineString(run) for run in kerbed if len(run) >= 2]).buffer(
            kerb_width_m
        )
        if kerbed and kerb_width_m > 0.0
        else None
    )

    def road_height(plan: np.ndarray) -> np.ndarray:
        """The road under points no area reaches: an island a ribbon runs under."""
        nearest = owners[int(tree.nearest(shapely.points(plan[0])))]
        return _heights(centrelines[nearest], plan)

    return out, _kerb_lines(
        region.whole,
        shapely.multipolygons(pieces),
        clip,
        drawn_kerbs,
        keys,
        flat,
        tolerance_m,
        region.islands,
        island_band if island_band is not None else island_rings(region),
        road_height,
    )


def island_rings(region: Region) -> BaseGeometry | None:
    """Every island's outline, a hair wide: what a kerb line lies within when it
    is an island's ring and not an area's edge. Such a line needs no lip —
    `island_tops` covers the whole island at the lip's height."""
    if not region.islands:
        return None
    band = shapely.union_all([island.exterior for island in region.islands]).buffer(10.0 * _GRID_M)
    shapely.prepare(band)
    return band


def on_island(rings: BaseGeometry | None, line: np.ndarray) -> bool:
    """Whether an `(N, 3)` kerb line is an island's ring (`island_rings`)."""
    return rings is not None and bool(rings.contains(shapely.LineString(line[:, [0, 2]])))


def island_tops(region: Region, centrelines: dict[Key, np.ndarray]) -> np.ndarray:
    """Every island's plan as `(n, 3, 3)` triangles at ROAD height, wound to face
    up; `surface.py` lifts them onto the kerb.

    An island's kerb ring is a riser and a lip `kerb_width_m` deep, which leaves
    the middle of anything wider than two lips open — onto nothing where an area
    surrounds it, and onto the ribbon's asphalt, lane lines and all, where a rail
    was read through it. The top closes both.
    """
    owners, tree = _owners(region, centrelines)
    if not region.islands or tree is None:
        return np.zeros((0, 3, 3))
    out = []
    for island in region.islands:
        plan = np.asarray(
            [
                np.asarray(tri.exterior.coords)[:3]
                for tri in shapely.get_parts(shapely.constrained_delaunay_triangles(island))
            ]
        )
        if not len(plan):
            continue
        owner = owners[int(tree.nearest(island.centroid))]
        y = _heights(centrelines[owner], plan.reshape(-1, 2)).reshape(-1, 3)
        out.append(np.stack([plan[:, :, 0], y, plan[:, :, 1]], axis=2))
    if not out:
        return np.zeros((0, 3, 3))
    return _face_up(np.vstack(out))


def _kerb_lines(
    whole: BaseGeometry,
    rest: BaseGeometry,
    clip: BaseGeometry | None,
    drawn_kerbs: BaseGeometry | None,
    keys: np.ndarray,
    heights: np.ndarray,
    tolerance_m: float = 0.0,
    islands: list[Polygon] | None = None,
    island_band: BaseGeometry | None = None,
    road_height: Callable[[np.ndarray], np.ndarray] | None = None,
) -> list[np.ndarray]:
    """Where an area meets R's own boundary: a kerb no ribbon draws.

    🔴 **A ribbon draws the kerb along its own rail and an area had none**, so
    every junction corner was a flat edge onto the pavement — and every bay a
    rail is `opened` past would lose the kerb it had. The boundary the areas
    share with R is exactly the kerb line the ribbons do not cover: where an
    area meets a ribbon the boundary is interior to R, and is not here.

    ⚠️ The region's own rectangle is a cut and not a kerb, so its edges are
    taken out. Each line is walked with the road on its RIGHT, so `surface.py`
    builds it as it builds a ribbon's left kerb, outward being left of travel.
    Heights are the areas' own, by plan position, so riser and asphalt share
    their foot.
    """
    edge = shapely.intersection(rest.boundary, whole.boundary, grid_size=_GRID_M)
    if islands and island_band is not None:
        # 🔴 An island is ringed WHOLE, the stretches under a ribbon included. A
        # rail is read through an island (`region._through`), so the ribbon is
        # drawn over it and no area meets that part of its boundary — left to the
        # line above, a refuge in a lane has no kerb at all.
        # Lines only: where an area touches R's boundary at a corner the overlay
        # hands back a point, and GEOS refuses a mixed-dimension union.
        # ⚠️ And less what the areas already met of an island: the overlay nodes
        # that stretch on its own grid, so unioned with the ring it is the same
        # kerb twice a millimetre apart — 80 m of it on Wan Chai, where the rings
        # under a ribbon add 657 m of the islands' 1,235.
        rings = shapely.union_all([island.exterior for island in islands])
        # ⚠️ ONE difference over the whole collection: per part it was 19,701
        # overlays against an unindexed band, 1.0 s of a 4.9 s stage against 48 ms.
        lines = shapely.multilinestrings(
            [
                part
                for part in shapely.get_parts(edge)
                if part.geom_type in ("LineString", "LinearRing")
            ]
        )
        met = [
            piece
            for piece in shapely.get_parts(lines.difference(island_band))
            if piece.geom_type == "LineString"
        ]
        edge = shapely.union_all([*met, rings])
    if clip is not None:
        edge = shapely.difference(edge, clip.boundary.buffer(10.0 * _GRID_M))
    # 🔴 Less every stretch a ribbon's own kerb already runs beside. Rails are
    # simplified to `rail_tolerance_m`, so a sliver of area lies between almost
    # every rail and R's true boundary; without this the ring was 27.4 km on Wan
    # Chai — most of the kerb in the region, drawn a second time 5 cm away.
    if drawn_kerbs is not None:
        edge = shapely.difference(edge, drawn_kerbs)
    # Simplified at the rails' own tolerance: a kerb strip is four triangles a
    # vertex, HyD digitises a corner radius a vertex every few centimetres, and
    # the mitre folds on wiggles that tight (71 inverted triangles against 15).
    # Douglas-Peucker keeps a subset of the vertices, so every one kept still
    # has the areas' own height under it.
    lines = [
        part
        for part in shapely.get_parts(shapely.simplify(shapely.line_merge(edge), tolerance_m))
        if part.geom_type == "LineString" and part.length > 0.0
    ]
    height_at = {tuple(key): y for key, y in zip(keys, heights, strict=True)}
    shapely.prepare(whole)
    out: list[np.ndarray] = []
    for line in lines:
        plan = np.asarray(line.coords)
        # Which side the road is on, asked a hand's breadth off the longest step.
        step = np.diff(plan, axis=0)
        longest = int(np.argmax(np.hypot(step[:, 0], step[:, 1])))
        unit = step[longest] / np.hypot(*step[longest])
        probe = 0.5 * (plan[longest] + plan[longest + 1]) + 0.05 * np.array([-unit[1], unit[0]])
        if not shapely.contains_xy(whole, *probe):
            plan = plan[::-1]
        y = [height_at.get(tuple(key)) for key in _key_of(plan)]
        if any(value is None for value in y):
            # A vertex the overlay made and the triangulation did not: between
            # two that it did, so it takes the line's own interpolation.
            known = np.flatnonzero([value is not None for value in y])
            if len(known):
                y = np.interp(np.arange(len(y)), known, [y[index] for index in known])
            elif road_height is not None:
                # No area touches it: an island lying wholly under a ribbon.
                y = road_height(plan)
            else:
                continue
        out.append(np.column_stack([plan[:, 0], np.asarray(y, dtype=float), plan[:, 1]]))
    return out
