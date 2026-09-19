---
paths:
  - "tools/ground_clearance.py"
  - "etl/tests/test_ground_clearance.py"
---

# ground_clearance.py's structure half — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- **`ground_clearance.py`'s STRUCTURE half — `structure_above`, `Structure`, `--structure-within-m`,
  `buildings.structure_class`, `BUMPER_LOW_M`/`BUMPER_HIGH_M`, or anything that CARVES: paste the
  band table, the section-share line and the per-edge band table, before and after.** 🔴 **It is a
  second class over the same walk and it is NEVER pooled with the ground** (`Q57`): ground proud of
  the road is the sink and the flat cross-section (`Q24`), structure proud of it is a wall in the
  carriageway (`Q19`), and they want opposite fixes. ⚠️ **Only the ground half gates** — a structure
  figure read against `--accept-share` or `--accept-edges-over-travel` is one population's number on
  the other's bar. 🔴 **The terrain rule may not be reused and that is measured**: `ground_above`
  takes the *nearest* height because terrain is single-valued where a car can be, but structure is a
  volume in a stack and upward-wound faces include a flyover's **deck top**, so read that way the
  interchange reports **+13.27 m** of structure proud on 210 of 737 edges. `structure_above` takes
  the **lowest face strictly above the road**; ⚠️ *both* wrong rules — nearest, and highest — delete
  the finding rather than corrupting it, so both have a test and both are mutation-checked.
  ⚠️ **Absence is the normal answer, not a coverage miss** — 92.8% of the region's road-drawn cells
  have no structure at all — which is why there is deliberately no coverage gate on this half.
  ⚠️ **The band is the finding and the row above it is not**: anything past `BUMPER_LOW_M` is already
  `carriageway_occupancy`'s population, so summing the two republishes `Q19`'s own count as this
  tool's discovery. ⚠️ **Sweep `--structure-within-m`** — it decides a refusal, and a bound that
  cannot be swept is `Q58`'s trap; the band is flat at 330 cells over 0.50-8.00 m while the row above
  runs 382 → 21,289, which is what proves the finding is not the window's. ⚠️ **A CARVE is a change
  here** — it moves structure to the carriageway edge, which is exactly what this measures — and
  `e99` now reads worst **−0.18 m**, so the edge this was prescribed for is no longer its own known
  positive. 🔴 **`optional_structure_faces` exists so this half can never abort the GROUND gate** —
  `structure_faces` exits on a city with no `structure_class` and on a region whose tiles carry none,
  both reachable, so it degrades to an empty index and every cell books `absent`. Do not "simplify"
  it back to a direct call. ⚠️ **`Structure.observe` owns the four-way decode and `check` grades it**;
  moving that decode back into `survey`'s loop makes the identity the caller checked against itself,
  which is how two write-only counters shipped. Numbers in `Q19`.
