---
paths:
  - "etl/pipeline/config_blocks/boxjunctions.py"
  - "etl/pipeline/drawnsurface.py"
  - "etl/pipeline/boxjunctions.py"
  - "etl/pipeline/boxsource.py"
  - "tools/box_extent.py"
  - "tools/paint_clearance.py"
  - "etl/tests/test_boxjunctions.py"
  - "etl/tests/test_box_extent.py"
  - "etl/tests/test_paint_clearance.py"
---

# Box junctions and paint height — before marking work done

- **`pipeline/boxjunctions.py`, the `boxjunctions` block, or anything that moves the drawn ribbon's
  extent (any widening)**: `tools/battery.py boxjunctions --region <r> --before <root>`
  (`box_extent.py --sweep`, `paint_clearance.py --layer boxjunctions`). Paste the per-box table and
  the `--ray-m` sweep.
  - `box_extent.py` grades and exits 0. A box is a published statement that the ground under it is
    carriageway — the only extent publisher covering junctions (`Q104`).
  - Quote the basis and the radius: the three-way split differs by twelve points between triangle
    count and area, and the void share runs 5.1% → 77.8% over `--ray-m` 1 → 8.
  - `void` (two ribbons that never meet) and `past kerb` (a ribbon narrower than the paint) want
    opposite fixes and never share an acceptance number (`Q57`). Do not add a mutation check asking
    a widening to move one and not the other — a widening closes both.
    `test_the_three_classes_are_exhaustive_and_disjoint` holds the partition; mutation-check it.
  - `--ray-m` and `--reach-m` are two values on purpose (`Q58`); a reach under the radius is refused.
  - Identity is point-in-polygon on the source rings, never a cluster of the mesh (clustering finds
    18 of 20 boxes at every radius). `unattributed` must stay 0.
  - `boxjunctions.glb` is a mesh per 300 m cell (`cell_m`, `Q135`); pool every mesh.
- **Any painted layer's height, `surface.py`'s cap construction, any paint `lift_m`**:
  `tools/paint_clearance.py --generated <dir> [--layer <l>]`, and paste its table. It is the only
  check that paint is on top of the asphalt; a top-down raster cannot see a wrong Y (`Q91`, `Q92`).
  - Four columns — `under hi`, `on kerb`, `in c'way`, `deep` — and only `deep` (past
    `--accept-depth-m`) is gated. Do not pool them. `tramway` and `arrows` are reported, never gated.
  - Measured shut (`Q92`): a burial is never answered by raising `lift_m` — clearing the p99 needed
    0.158 m, paint floating 16 cm over the road.
  - `DrawnSurface.split` cuts every paint polygon along the road's creases before placing; a cut
    vertex takes its own piece's side (`sample(toward=)`), because the road steps along a cap ring
    (0.46 m riser). `split(thin_m=)` refuses a cut leaving a sliver (cutting regardless lost 1.96%
    of box paint area).
  - `DrawnSurface` reads the rails (`roadsurface.json`'s `ribbons`); a point over nothing drawn
    takes the nearest drawn edge with no radius. `vertices_over_cap` and `vertices_over_void` are
    the in-stage tripwires.
  - No "placed minus drawn" counter: it is `lift_m` by construction (`Q72`).
