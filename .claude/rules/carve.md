---
paths:
  - "etl/pipeline/carve.py"
  - "etl/tests/test_carve.py"
---

# The carve — before marking work done

- **`pipeline/carve.py`, the `carve` block, or which edges are carved**: `tools/battery.py carve
  --region <r> --before <root>` (the `Q19` battery). From `carve.json` compare per-edge
  `carved_area_m2`, `carved_volume_m3`, `wall_m`, `soffit_bounded`, `triangles_removed`,
  `population`, `deck_top_kept`, plus `tiles_written`, `facing_away`, and the region's tile vertex
  total and bytes from `buildings.json`. Anything that carves also owes `ground_clearance` and
  `clearance`. `clearance_reconcile` fails until its ratchet is moved; that is the ratchet working.
  Evidence is a frame shot twice (`Q62`), and a drive off a listed ramp, `e99` first.
- The cut face is constructed, not derived: the estate is not watertight (5.38% of edge slots open
  at source, 14–26% in the tiles), so "edges the removal opened" returns zero closed loops. Carving
  at source rescues nothing.
- A second pass degrades the first (`e327`'s wall 141.8 → 75.8 m). `buildings.json` carries a
  `carved_edges` marker and the stage refuses; `--from roads` reaches it. Rebuild from `buildings`.
- The wall takes its colour and class from the structure removed, never from the tile's first
  vertex. `carved_volume_m3` accumulates per prism.
- The prism is the surveyed `width_m`, never the drawn floor. A residual is never answered by
  widening the prism (`Q54`); the three residuals are the grader's 1.0 m plan bin.
- `e99` and `e207` are the two exceptions, each on the user's call and neither a precedent: cut at
  an authored 6.40 m because the obstruction is interior and every width rule that catches it
  fences 59–67 edges (`Q19`). On `e99` the carve moves the wall to the carriageway edge, so a
  corridor reading barely changes (4.50 → 5.00 m); on `e207` it removes three flyover piers from
  the lane (1.95 → 4.96 m) and the ramp overhead stands on nothing there. `e125` and `e781` stay
  unlicensed.
- The cut face is capped at the deck plus `parapets.face_above_m` (`EdgePlan.face_above_m`,
  `test_the_wall_is_capped_at_the_face_top`, `Q147`). A change owes the `e99` frame
  (`--camera=261,7,384 --look=229,5,422`) and a drive off `e99`.
- **Parapet band** (`carve.parapets`, `Q147`): a carved ramp's edge is jumpable (user's call). A
  listed edge takes the band whole. The by-rule populations (`levels`, `on_structure`) ship off:
  the band over every flyover edge was built and withdrawn on the user's call. Flip them on his
  instruction only.
  - `_band_split` keeps the deck and removes the wall by triangle normal; `_band_candidates` takes
    a parapet whole by centroid. No prism: one floored at the ribbon takes the deck top
    (`test_the_naive_prism_takes_the_deck_with_the_wall`), and its planes sliver every wall. Three
    refused shapes cost +47%, +22% and +4.6% tile vertices.
  - `deck_top_kept` is the counter a split mutation drives to 0; mutation-check it. `wall_max_m`
    keeps piers, a neighbouring deck's side and noise barriers.
  - The band's width is `deck_rim_m` per station, not the authored width. `wall_m` is 0 on band
    rows by construction. `_snap_rows` is load-bearing (`verify_tiles` refuses a `TEXCOORD_1` row
    between two objects). Absent, the band is a no-op and the bundle byte-identical.
  - A widening, `reach_m` or `wall_max_m` change moves the band.
