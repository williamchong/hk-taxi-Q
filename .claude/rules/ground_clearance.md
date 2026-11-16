---
paths:
  - "tools/ground_clearance.py"
  - "etl/tests/test_ground_clearance.py"
---

# ground_clearance.py's structure half — before marking work done

- **`structure_above`, `Structure`, `--structure-within-m`, `buildings.structure_class`,
  `BUMPER_LOW_M`/`BUMPER_HIGH_M`, or anything that carves**: `tools/ground_clearance.py
  --generated <dir>`; paste the band table, the section-share line and the per-edge band table,
  before and after (`Q19`).
- Structure is a second class over the same walk and is never pooled with the ground (`Q57`):
  proud ground is the sink's problem (`Q24`), proud structure is a wall in the carriageway. Only
  the ground half gates; `--accept-share` and `--accept-edges-over-travel` do not apply to
  structure.
- `structure_above` takes the lowest face strictly above the road. The terrain rule (nearest
  height) reads a flyover's deck top as +13.27 m proud on 210 of 737 edges. Nearest and highest
  both delete the finding; both have a mutation-checked test.
- Absence is the normal answer (92.8% of cells have no structure), so there is no coverage gate.
- The band is the finding. Anything past `BUMPER_LOW_M` is already `carriageway_occupancy`'s
  population; do not sum the two.
- Sweep `--structure-within-m`: the band is flat over 0.50–8.00 m while the row above it runs
  382 → 21,289.
- A carve moves structure to the carriageway edge, which is what this measures.
- `optional_structure_faces` degrades to an empty index so this half cannot abort the ground gate
  on a region with no `structure_class`. Do not replace it with a direct `structure_faces` call.
- `Structure.observe` owns the four-way decode and `check` grades it; keep the decode out of
  `survey`'s loop.
- `BUMPER_*` are imported from `pipeline.clearance` on purpose; no second import follows.
