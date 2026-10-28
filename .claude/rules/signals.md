---
paths:
  - "etl/pipeline/signals.py"
  - "etl/pipeline/config_blocks/signals.py"
  - "etl/tests/test_signals.py"
  - "game/scripts/traffic/signal_plan.gd"
  - "game/scripts/traffic/signal_controller.gd"
  - "game/scripts/traffic/signal_plan_profile.gd"
  - "game/tools/verify_signals.gd"
  - "game/tuning/signal_plan.tres"
---

# The signal plan and its controller — before marking work done

- **`pipeline/signals.py`, the `signals` block, `surface.py`'s `junctions` key, or
  `roadmarks.transverse_host`: paste the stage's `signals:` line for BOTH regions, before and
  after** (`P3-3a`, `Q173`) — the two partitions (stop lines → no host / off axis / dead end /
  hosted; junctions → staged / at the seam / not owned / no approach), the approaches with their own
  stop line, and the stages histogram. Wan Chai 120 → 40 staged of 41, 98 approaches; Causeway Bay
  15 → 8, 16. 🔴 **`RM1011` is the signal stop line BY MEASUREMENT** (115 of 120 within 15 m of a
  head; `RM1012` / `RM1013` p50 52 / 46 m): do not add a give-way or STOP-sign code to
  `stop_line_codes`. 🔴 **The junction is `surface.py`'s stub cluster or a lone node — no radius**
  (`Q72`: 15 / 25 / 35 m give 297 / 240 / 202 junctions, no plateau). 🔴 **The host fixes the
  JUNCTION, never the approach**: 68 of 120 stop lines cross no centreline and the host is often
  the edge LEAVING the junction, so the approaches are every level-0 edge entering it, stopped at
  `trim_m`. Do not "fix" an approach to the host edge. ⚠️ **`axis_tolerance_deg` is the one free
  value and it is authored** — sweep it and paste the stages table (`hong_kong.yaml` has 20 / 30 /
  45). ⚠️ A junction a neighbour's edge reaches is refused (`at_seam`, 1 on Wan Chai): its
  approaches are split across two bundles.
- **`signal_controller.gd`, `signal_plan.gd`, `signal_plan.tres` or `verify_signals.gd`: run
  `tools/check.sh` and paste `verify_signals`' `plan:` line for both regions.** 🔴 **The timeline is
  a pure function of the clock** (`light_at`): no state may depend on what was asked before, or
  the tool's walk stops being the controller. 🔴 **The conflict check is graded on a junction
  built to fail it** (`_check_the_checker`); mutation-check the tool rather than reading its pass —
  `light_at` returning GREEN outside its slot, and `along` flipped in `SignalPlan.add_region`, both
  fail it by name (2026-10-29). ⚠️ `CONFLICT_DEG` (45) checks the ETL's result and is not its
  tolerance; do not tie the two. ⚠️ **Every timing is authored** (`signal_plan.md`): TD publishes
  none, and red-and-amber 2 s / amber 3 s are the British values, TD's own unread.
