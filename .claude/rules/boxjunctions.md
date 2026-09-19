---
paths:
  - "etl/pipeline/boxjunctions.py"
  - "etl/pipeline/boxsource.py"
  - "tools/box_extent.py"
  - "tools/paint_clearance.py"
  - "etl/tests/test_boxjunctions.py"
  - "etl/tests/test_box_extent.py"
  - "etl/tests/test_paint_clearance.py"
---

# Box junctions and paint height — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- **`pipeline/boxjunctions.py`, the `boxjunctions` config block, or anything that moves the drawn
  ribbon's EXTENT — `surface.floor_default_m` included: also `tools/box_extent.py`, and paste its
  per-box table and its `--ray-m` sweep.** 🔴 **A yellow box cannot be painted on a pavement**, so
  each one is a published statement that the ground beneath it is carriageway — a **fourth extent
  publisher** beside `Q94`'s three, and the only one covering junctions, where `Q95`'s ray survey
  refuses to station. Today **6.71%** of box paint area (38.75 m² of 577.83) has no drawn
  carriageway under it. 🔴 **Quote the BASIS and quote the RADIUS or the number means nothing.**
  The three-way split reads **55.7 / 40.3 / 4.0 by triangle count** and **43.6 / 48.0 / 8.4 by
  area** over the same paint — twelve points apart, because a void triangle is small and there are
  many of them — and `Q104` first published the count split beside an area headline. The void share
  also runs **5.1% → 77.8%** over `--ray-m` 1 → 8, against a constant off-road population.
  🔴 **The two classes want OPPOSITE fixes and must never share an acceptance number** (`Q57`):
  `void` is the gap between two ribbons that never meet and is `P3-31`'s; `past kerb` is a ribbon
  genuinely narrower than the paint and is `P3-32`'s. ⚠️ **Do not add a mutation check asking a
  widening to move one and not the other** — it was written into `PLAN.md`, and a widening closes
  voids *and* kerb overhangs, so only a broken classifier could pass it (`Q72` inverted). What holds
  disjointness is the partition asserted at runtime and the 256 ray patterns in
  `test_the_three_classes_are_exhaustive_and_disjoint` — mutation-check that rather than reading its
  pass. ⚠️ **`--ray-m` and `--reach-m` are two values on purpose**: the overrun runs past the
  classification radius, so one value would confine the distribution to the bar by construction
  (`Q58`'s trap), and a reach under the radius is refused at startup. ⚠️ **Identity is
  point-in-polygon on the source rings, never a cluster of the shipped mesh** — clustering returns
  **18 of 20** boxes and is flat from 1.5 m to 15 m, so a sweep cannot see the undercount;
  `unattributed` must stay **0**. ⚠️ It **grades rather than checks** and exits 0 whatever it finds.
  Numbers in `Q104`.
- **Any painted layer's height, `surface.py`'s cap construction, or any paint `lift_m`: also
  `tools/paint_clearance.py`, and paste its table.** It asks the one question a marking stage cannot
  ask from inside — **is the paint on top of the asphalt or inside it?** — because every counter
  `boxjunctions.json` and `roadmarks.json` publish grades the ETL against its own intermediate
  values. 🔴 **`Q91` closed the previous box-junction defect on "a top-down raster of the shipped
  mesh is a complete grid", which is true and is exactly the projection that cannot see this**: the
  mesh is complete in **plan** and wrong in **Y**, and 23.2% of it shipped under the road. ⚠️ **Four
  columns, and only the last is gated** — `under hi` (what the depth buffer hides), `on kerb` (a
  surveyed extent past the drawn ribbon, which is registration and `Q54` refuses to scale), `in c'way`
  (the wrong height on the road it is drawn on) and `deep` (that, past `--accept-depth-m`). Pooling
  them leaves nothing to do but raise the bar. ⚠️ **`tramway` and `arrows` are reported and never
  gated**: `Q58` measured tram rails p50 3.26 m past the drawn kerb, so a third of them are over no
  carriageway at all and gating that fails the tool on a fact. ⚠️ **The shallow residue was geometric,
  not a defect, and is closed by construction since 2026-09-16** — paint is a flat triangle over a road
  that creases at every cap fan edge and every ribbon station, so its chord dipped below the crown it
  spanned by millimetres however right its vertices were; `DrawnSurface.split` now cuts every paint
  polygon along the creases it crosses before it is placed, and the higher of two planes is convex, so
  a covered piece stands on or above the road everywhere. What is left under the bar is the
  nearest-edge fallback over void, which is not a surface. 🔴 **A cut vertex takes the height of its own
  piece's side (`sample(toward=)`), and that is not tidiness**: the drawn road *steps* along a cap's
  ring as well as folding, and sampled inclusively the piece outside the ring was drawn down a 0.46 m
  riser — `check_faces_up` refused 2 of 1,578 Causeway Bay box triangles while `inverted` read 0.
  ⚠️ **`split(thin_m=)` refuses a cut that would leave a piece under the builder's sliver bar**: cutting
  regardless lost 1.96% of the box paint's plan area. 🔴 **Do not answer a burial by raising `lift_m`**: clearing `Q92`'s p99 needed
  **0.158 m**, paint floating 16 cm over the road. ⚠️ **`vertices_over_cap` and `vertices_over_void` are the in-stage
  tripwires and there is deliberately no "placed minus drawn" counter** — that is `lift_m` by
  construction and `Q72`'s tautology. 🔴 **`DrawnSurface` reads the RAILS since 2026-09-16**
  (`roadsurface.json` schema 10, `ribbons` in `_Builder.strip`'s order): the ribbon case is the
  strip's own quads, never a centreline's station height, and a point over nothing drawn takes the
  nearest drawn edge with no radius — `vertices_over_void` reads every vertex off a cap if `ribbons`
  stops being published. Numbers in `Q92`.
