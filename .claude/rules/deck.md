---
paths:
  - "etl/pipeline/roads.py"
  - "tools/deck_margin.py"
  - "tools/touchdown_error.py"
  - "tools/node_step.py"
  - "etl/tests/test_node_step.py"
  - "etl/tests/test_touchdown_error.py"
  - "etl/tests/test_deck_margin.py"
  - "etl/tests/test_roads.py"
---

# Off-grade ribbons, decks and touchdowns — before marking work done

`tools/battery.py off-grade --region <r> --before <root>` runs `deck_margin`, `overhang`,
`touchdown_error` and `node_step`. `node_step` gates (exit 1 over `P4-3`'s 0.15 m); the battery
still exits 0.

- **`_deck_heights`, `_descend`, `_lifted_heights`, `deck.touchdown_max_grade_pct`**: paste
  `tools/touchdown_error.py`'s table and the roads stage's `descended / refused / graded across`
  line, before and after (`Q90`).
  - `deck_error.py` cannot see a ribbon clamped level in the air over an unmodelled touchdown: it
    reads as uncovered. `check.sh`'s `on_structure` assertions skip off-grade edges. Evidence is a
    frame: one fixed camera in `city_preview.tscn`, `--debug-view=off --hud=off`, shot twice (`Q62`).
  - The grade is measured ribbon to ribbon, `clearance_m` included, never off the deck top.
  - `touchdown_grade_pct` is recorded over refusals too: `len(touchdown_grade_pct) ==
    ends_descended + ends_over_grade`, with `ends_no_target` counted beside it, never appended.
  - `_descend` gates on a level-0 edge at the node, never on "mixed" (a `(1, 2)` node has no street
    to land on). The grader cannot catch a wrongly descended end.
  - `_deck_heights` and `_lifted_heights` ask different questions of one node; lifted and descended
    ends are disjoint by data, not by construction.
  - The bar is one-sided: clamped inside the cap is the defect, over it is the refusal working.
    `overhang.py` reads slightly worse after a descent, because a ramp resting on terrain still
    counts as hanging.
- **`_land_on_street`, or any height at a node joining level 0 to an open deck** (`P4-3`): paste
  `tools/node_step.py`'s table and the roads stage's `raised to meet a deck` line, before and after.
  - The grader walks the **drawn** road, following the surface it is on; it never reads a height
    off `roadgraph.json`. Taking the highest face instead reads an overlapping carriageway as a step.
  - The street rises to the deck, never the deck down to the street: at node 269 a 10% descent
    sinks the road 0.24 m into its structure. The cap is the grade used, and a run that cannot land
    inside its edge is refused (`ends_unlanded`), never cut short — its far node would step.
  - A closed stub (`clearance.stubs`) is never a landing target; `e425` would lift Victoria Park
    Road 6 m. Closed means unmeasured, so `RoadGraph._drivable` refuses it like level −1.
- **Anything that moves an off-grade ribbon (`surface.floor_by_elevation_level`,
  `floor_on_structure_m`, an off-grade width)**: paste `tools/deck_margin.py`'s per-edge table,
  pooled distributions and counterfactual.
  - It splits `overhang.py`'s figure into deck span, signed centreline offset and metres with
    nothing under them: too wide and registered wrong need opposite fixes. It is not independent
    of `overhang.py` (same faces, class, tiles); the two drifting apart is a bug in one (`Q106`).
  - `--bridge-m` (default 1.0) is sourced: the estate is not watertight, the gap distribution is
    bimodal (p50 0.40 m, p90 3.37 m), and without it the tool is a hole detector. `--junction-m 0`
    does not explain the gap between the tools (14.0 → 14.3%).
  - Quote `--max-lateral-m` with a span, never with an overhang or the counterfactual, which are
    cap-stable.
  - The counterfactual (`Q105`) prices cutting each station to its deck's rims. The two halves are
    published apart; their sum is not a width where either is negative, and the tool refuses to
    print unless that count equals `centre_off_deck`. `priced_widths` excludes those stations
    (`TestPricedWidths`). It licenses paint, never a `width_m`.
  - No "stations on deck after the clamp" counter: a half cut to its own rim cannot overhang it,
    so it is total by construction (`Q58`).
- Measured shut (`Q103`): the width survey is not extended off-grade. The publishers license 5 of
  45 level-1 edges, their lines are a 2D plan projection, and 2 of the 5 publish a width wider than
  the deck. A deck is a ceiling on `lanes` and paint, never a source of a count or a `width_m`
  (`Q105`, `Q114`).
