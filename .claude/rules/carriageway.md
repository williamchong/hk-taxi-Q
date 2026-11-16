---
paths:
  - "etl/pipeline/carriageway.py"
  - "etl/pipeline/carriageway_area.py"
  - "tools/carriageway_margin.py"
  - "tools/width_evidence.py"
  - "tools/centreline_error.py"
  - "etl/tests/test_carriageway.py"
  - "etl/tests/test_carriageway_area.py"
  - "etl/tests/test_carriageway_margin.py"
  - "etl/tests/test_width_evidence.py"
  - "etl/tests/test_centreline_error.py"
---

# The carriageway width survey — before marking work done

- **`pipeline/carriageway.py`, the `carriageway_survey` block, `lane_width_m`, `surface.floor_*`, or
  anything that moves `width_m`**: `tools/battery.py width --region <r> --before <root>`, both
  regions. Paste the roads stage's `carriageway:` block (two-station line, `HyD strip:` line,
  both-read agreement, `confirmed by:`) and all four `carriageway_margin.py` tables. These tools
  grade and exit 0.
- **Publishers** (`Q94`): `carriageway_survey.edges` has three, in a load-bearing order applied per
  station — TD's painted edge, iB1000's margin, then HyD's Pavement Polygon (`geometry: area`,
  `_union_boundary`; a seam between HyD tiles is not a kerb). HyD arrives via `paged_sources`.
- **`pipeline/carriageway.py` and `tools/carriageway_margin.py` are deliberately duplicated**
  (`Q95`). Do not import one into the other; they agree to p50 0.005 m and a drift is the finding.
  `carriageway_margin.shipped_rows` moves in the same commit as the pipeline's walk. Widths are
  never read from `carriageway_width.json` (`--json`, gitignored).
- **Reading `carriageway_margin.py`**:
  - Headline: quote it, not the two-source agreement, which is cap-sensitive.
  - Span: cap-sensitive, so quote `--max-ray-m`. On a one-way edge it is kerb-to-kerb, not a
    width, wherever the ray crosses an opposed pair (`off_centre`).
  - Pairs (`own = 2 x near`): never pooled into the span line (`Q57`). The load-bearing counter
    is the negative residual, the split refusing itself. Sweep `--pair-bearing-deg`. The six
    shared-endpoint pairs in `surface.py` are the ground truth for any pairing rule.
  - Widths (`beyond = span − 2 x near`): three states; the middle one publishes nothing on purpose
    (`e142`). Quote `basis` with `carriageway_m`. `--dual-min-m` licenses nothing — every width
    rests on `hard_min_m` — so a moving licensed count under its sweep is the alarm.
- **Lanes** are a bracket off TPDM 4.3.9.8 (`width_bounds.lane_m`), never a division by
  `lane_width_m`. The tool refuses to start unless `2 × max_ray_m` exceeds the ceiling (`Q58`).
- **`MIN_STATIONS`, `MIN_AGREEING_STATIONS`, `_station_scatter`, `_agree_m`, `DECK_MIN_STATIONS`,
  `carriageway_area.py`, `_row_widths`, `_street_widths`, `_confirmed`, `confirm_within_m`**
  (`Q128`):
  - The two-station licence is additive: three-station edges are assigned first and `_assign`
    takes no tolerance.
  - The tolerance is derived over the edges the bounds admit (2.81 m; 2.13 over the licensed
    ones). It may not become config.
  - `DECK_MIN_STATIONS` does not follow the publishers' bar: a p10 of two values is the smaller.
  - HyD's strip is a candidate; agreement is the licence. Alone it reads |p90| 2.53 m pooled and
    4.69 m on short edges, no better than the invented width. `strip_unconfirmed` falling to zero
    means the confirmation stopped confirming. `confirm_within_m` is a trade curve.
  - The ray survey is not a voter (`_confirmed` asserts it). `hyd_strip` never joins
    `width_evidence.MEASURED` or `centreline_error._MEASURED_SOURCES`.
  - `carve.py` cuts at `edge["width_m"]` and `e99` is still `authored`: `carve.json`'s rows must
    stay byte-identical. Rebuild `--from buildings`, not `--from roads`.
  - `strip_agreement_m` is recorded, never gated. Its speed-ups are priced and untaken.
- **`tools/width_evidence.py`, `carriageway_survey.lane_lines`** (`Q127`): paste the synthesis
  table, both `|p90|` columns, both regions. The ray survey is never a combination's second
  reading. Quote the `<60m` column with the pooled one. The street borrow is leave-one-out.
- Measured shut (`Q127`): no junction-opening gate on the ray survey — it moves measured widths at
  every radius and angle swept. `_confirmed`'s openings filter is not that rule: it drops stations
  only where the survey is silent.
- **Station normals are opposite on purpose**: `carriageway._stations` emits right of travel,
  `surface.mitres` and `overhang.left_of` left. Anything that keeps the difference needs a named
  negation and a mutation check (`Q78`);
  `test_the_station_normal_is_the_negation_of_mitres` is the ratchet.
- Measured shut (`Q19` candidate 1, refuted): no centreline-shift rule. `tools/centreline_error.py`
  finds 0.02–0.88 m of correction where 1.43–4.49 m is needed; it clears 0 edges. Re-run it if
  the survey, `_stations`, `surface.mitres` or `clearance.py` moves.
