---
paths:
  - "etl/pipeline/tramlines.py"
  - "etl/tests/test_tramlines.py"
  - "game/scripts/traffic/tram_lines.gd"
  - "game/scripts/traffic/tram_profile.gd"
  - "game/scripts/traffic/tram_system.gd"
  - "game/tools/verify_trams.gd"
  - "game/tuning/trams.tres"
  - "tools/make_tram_bell.py"
---

# The moving trams — before marking work done

- **`pipeline/tramlines.py` or `tramway.lines`: paste the stage's `tramlines:` line for BOTH regions,
  before and after** (`P3-4`, `Q176`): the partition (beds → refused, pruned, kept), the witnesses,
  metres with and against the street, joins (forks, reduced, longest), open ends, stops (offside),
  stop lines, junctions unbound, and `in_tram_path` by layer. Wan Chai 63 → 60 kept (4393 m), 0
  refused, 3 pruned, 3 + 3 open; Causeway Bay 15 → 13 (1371 m), 2 refused, 0 pruned, 2 + 2 open.
  🔴 **A fragment under `min_flow_m` does not vote**: a turnout's curve has the main line beside it
  and read as double track it cost the Happy Valley branch. 🔴 **`_continues` tests the chord's own
  heading**: without it the other track's end, 2.6 m abeam and parallel, reads as a continuation.
  🔴 **Open only with nothing to run on to**, or a tram vanishes 10 m into the street. ⚠️ The stop
  and signal bars are published data read wide: `Q58`'s reserve stands a rail 3.26 m past the kerb,
  so the car's own line would miss it. ⚠️ 799 + 234 m against the street is reported, not gated: the plan was read
  by eye (main line, Happy Valley branch, Causeway loop), no timetable says which way a track runs.
- **`tram_lines.gd`'s seam: `verify_trams`' `lines:` line.** 🔴 Resident regions are a fact about this
  run, so the seam is joined at runtime; `seam: both tracks cross the seam` fails by name if a
  region's rectangle moves. `unreached` must read 0, or a join went nowhere.
- **`tram_system.gd`, `trams.tres`: `tools/check.sh`, paste `verify_trams`' `lights:` and `stops:`
  lines, and a throttle-route `draws` / `phys` with and without `--trams=off`.** 🔴 **A tram reads
  what is ahead down the rails, not a cone** (`_gap_on_route`): a straight cone missed a taxi round
  a curve until the tram stood on it (0.1 m, 10.7 m since). 🔴 **A tram is placed at rest**: at speed,
  one placed short of a red could not stop (seed 4). ⚠️ A tram does not stop for a car crossing,
  for `TrafficSystem`'s deadlock reason. ⚠️ Mutations are in `Q176`; a GDScript mutation must still
  compile, since Godot hangs on an unused variable.
- **The push** (`Q180`): `verify_trams`' `push:` lines. 🔴 **A tram gives only along its rails**:
  `push_inverse_mass` is `(n · rails)² / m`, so a push square across moves nothing and a tram cannot
  be derailed — never add a free-body term. A tram pushed back rolls back (`_roll`) and brakes to
  rest before it runs on. 🔴 A knocked car holds a tram at any heading (`_follow`'s `ANY_HEADING`).
  The mass is `parked.tres`' `masses_kg["tram"]`, HKT's own figure.
- **The bell** is `tools/make_tram_bell.py`, byte-identical each run
  (`test_make_tram_bell.py`). It was the game's first sound, and nothing has graded a level for it or for the horn and the beep (`Q178`).
- **A tram's lamps are the running bit** (`Q177`): the head lamp on `headlamp_l` (⚠️ `headlamp_c` is on no
  circuit, so the lens goes dark without a word) and the side lamps on `foglamp_{side}`. They burn by day
  too, on the user's "always". A close tram cannot be re-shot on demand: placement moves with `--shots`.
- **A tram at its stop winks left** (`Q187`): `TramSystem.at_stop` (braking into the stop or
  standing at it) puts the left bit in its lamp write; `verify_trams`' `stops:` wink line.
- **A tram throws a beam at night** (`Q213`) through the traffic's `TrafficBeams`; its rules are
  `signals.md`'s beams bullet.
