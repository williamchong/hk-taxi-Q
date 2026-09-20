---
paths:
  - "etl/pipeline/join.py"
  - "tools/join_seam.py"
  - "etl/tests/test_join*.py"
---

# The seam between regions — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- 🔴 **`join.reach_m`, `Config.neighbours` / `read_*`, a region's `bounds`, or anything that moves
  where a crossing road is cut or who owns it: `tools/join_seam.py --region-a wan_chai --region-b
  causeway_bay` before and after, both regions' sheet lists, and a byte-identical `roadgraph.json`
  on a region with NO neighbour** (`Q116`, `P5-7`). The reach widens what a region *reads* and never
  where it *is* — `bounds`, `region_high` and the tile grid do not move (`Q10`) — so a change that
  moves `mong_kok`'s graph has widened the wrong thing. ⚠️ **Byte-identity on the region WITH a
  neighbour is not the proof and is not expected** once `P5-7e` publishes the far halves; until then
  it holds, and `P5-7c` measured it holding through 24 extra parts read. 🔴 **Since `P5-7e` the neighbour's runs ship under
  `roadgraph.json`'s own `foreign_edges` list, never as a flag on `edges`** — nineteen readers iterate
  `edges` and a list they never open is inert by construction. ⚠️ **`edges` keeps its ids WITH GAPS**
  where a run turned foreign (`e207` still names what it named); nothing may index it by position, and
  the sequence handed to `_turn_restrictions` must stay in **id order** — `owned + foreign` resolved
  35 → 11 turns in Causeway Bay with nothing raised. ⚠️ **Foreign edges are kerbside TRACKS and are
  published on nothing**: past the line the nearest road is the neighbour's, and with only owned
  tracks a restriction painted a run on Causeway Bay's `e0`. ⚠️ **`Config.clip_extent` widens along
  the shared axis ONLY** — the same latitude projects 4 cm apart 1.65 km east, and a union across that
  axis moved 45 of Wan Chai's own outer-edge cuts. Prove a change here with `join_seam.py`'s
  **one owner per run / 0 + 0 nodes on the line / 0 unmatched copies** and a field-by-field diff of
  the non-crossing edges — node ids renumber, everything else must not. 🔴 **A junction cap admits a
  foreign mouth and goes WHOLE to the region containing its node, by `roads.Ownership`** (`P5-7f`):
  `surface.py` shapes the foreign runs so the hull can read them and draws none; paste
  `roadsurface.json`'s `join` block (`foreign_ends` / `caps_with_foreign_mouth` / `caps_in_neighbour`)
  and mutation-check it by stripping `foreign_edges`. ⚠️ **The far half rides in the LAST column's
  chunk** — `_tile_keys` clips into the grid and the streamer picks by `aabb` — so do not build an
  out-of-grid tile id for it. 🔴 **`pipeline/join.py` is the reference merge and
  `reachability.py --graph-dir` is how the pair is graded** (`P5-7g`): paste its `foreign_matched /
  foreign_unmatched / nodes_unified / turns_dropped` and the cross-seam routed pairs (334,767 against
  194,774 + 13,718 alone). 🔴 **`Edge.offset_m` is ONE number per edge, and the cut found it**: a run
  whose halves sit on two decks takes the median of both, and `e364`'s near half lost 1.3 m of drawn
  half-width to its far half. Do not answer that by trimming the run; the fix is per station
  (`Q103`). 🔴 **`join_seam.py`'s carriageway line is
  0.00 m over 8 roads and 64.62 m a side (`P3-33e`)**: R is cut by rectangle, so nothing else makes
  the two builds agree where asphalt meets the line. ⚠️ It sections BOTH on one city-frame line,
  because `city_offset` is whole metres and the rectangles overlap by 0.62 m — an inset per side
  reads every oblique crossing as a disagreement. ⚠️ **`clearance_reconcile.EXPECT` is keyed by
  region** — 28 / 32 / 8 and 9 / 13 / 4 — and
  the deck graders read a region's own tiles, so an owned far half over the neighbour's structure
  reads as hanging in air (`overhang` 25.1% on Causeway Bay); quote that with the cause or it reads
  as a defect.
