---
paths:
  - "etl/pipeline/join.py"
  - "tools/join_seam.py"
  - "etl/tests/test_join*.py"
---

# The seam between regions — before marking work done

- **`join.reach_m`, `Config.neighbours` / `read_*`, a region's `bounds`, or anything that moves
  where a crossing road is cut or who owns it** (`Q116`): `tools/join_seam.py --region-a wan_chai
  --region-b causeway_bay` before and after, both regions' sheet lists, and a byte-identical
  `roadgraph.json` on a region with no neighbour. The reach widens what a region reads, never
  where it is (`Q10`). Byte-identity on a region with a neighbour is not expected.
- Proof: `join_seam.py`'s one owner per run / 0 + 0 nodes on the line / 0 unmatched copies, its
  carriageway line at 0.00 m, and a field-by-field diff of non-crossing edges (node ids renumber,
  nothing else). It sections both builds on one city-frame line, because the rectangles overlap
  by 0.62 m.
- The neighbour's runs ship in `roadgraph.json`'s `foreign_edges`, never as a flag on `edges`.
  `edges` keeps its ids with gaps: nothing indexes it by position, and `_turn_restrictions` takes
  the sequence in id order (`owned + foreign` resolved 35 → 11 turns silently).
- Foreign edges are kerbside tracks and are published on nothing.
- `Config.clip_extent` widens along the shared axis only; a union across it moved 45 of Wan Chai's
  outer-edge cuts.
- A junction cap admits a foreign mouth and goes whole to the region containing its node
  (`roads.Ownership`). `surface.py` shapes foreign runs and draws none. Paste `roadsurface.json`'s
  `join` block (`foreign_ends`, `caps_with_foreign_mouth`, `caps_in_neighbour`) and mutation-check
  it by stripping `foreign_edges`. The far half rides in the last column's chunk; do not build an
  out-of-grid tile id.
- `pipeline/join.py` is the reference merge; grade the pair with `tools/reachability.py
  --graph-dir <joined dir>` (`foreign_matched`, `foreign_unmatched`, `nodes_unified`,
  `turns_dropped`, cross-seam routed pairs). Rebuild `etl/out/wan_chai+causeway_bay`
  (`python -m pipeline.join`) after moving either region, or `verify_join` fails.
- `Edge.offset_m` is one number per edge: a run whose halves sit on two decks takes the median of
  both (`e364`). Do not trim the run; the fix is per station (`Q103`).
- `clearance_reconcile.EXPECT` is keyed by region. The deck graders read a region's own tiles, so
  an owned far half over the neighbour's structure reads as hanging (`overhang` 25.1% on Causeway
  Bay); quote the cause with it.
