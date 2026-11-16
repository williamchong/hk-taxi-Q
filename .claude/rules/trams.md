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

- **`pipeline/tramlines.py` or `tramway.lines`** (`P3-4`, `Q176`): paste the stage's `tramlines:`
  line for both regions, before and after (beds → refused / pruned / kept, witnesses, metres with
  and against the street, joins, open ends, stops, stop lines, junctions unbound, `in_tram_path`).
  - A fragment under `min_flow_m` does not vote: a turnout's curve read as double track cost the
    Happy Valley branch.
  - `_continues` tests the chord's own heading, or the other track's end 2.6 m abeam reads as a
    continuation.
  - An end is open only with nothing to run on to, or a tram vanishes 10 m into the street.
  - Stop and signal bars are read wide: `Q58`'s reserve stands a rail 3.26 m past the kerb.
  - Metres against the street are reported, not gated.
- **`tram_lines.gd`**: `verify_trams`' `lines:` line. The seam is joined at runtime (`seam: both
  tracks cross the seam` fails if a region's rectangle moves); `unreached` must read 0.
- **`tram_system.gd`, `trams.tres`**: `tools/check.sh`, `verify_trams`' `lights:` and `stops:`
  lines, and a throttle-route `draws` / `phys` with and without `--trams=off`.
  - A tram reads what is ahead down the rails (`_gap_on_route`), never a cone: a cone missed a taxi
    round a curve.
  - A tram is placed at rest: at speed, one placed short of a red could not stop (seed 4).
  - A tram does not stop for a car crossing (`TrafficSystem`'s deadlock reason).
  - A GDScript mutation must still compile: Godot hangs on an unused variable.
- **The push** (`Q180`): `push:` lines. A tram gives only along its rails — `push_inverse_mass` is
  `(n · rails)² / m`; never add a free-body term. Pushed back it rolls back (`_roll`) and brakes to
  rest. A knocked car holds a tram at any heading (`_follow`'s `ANY_HEADING`). The mass is
  `parked.tres`' `masses_kg["tram"]`.
- **The bell**: `tools/make_tram_bell.py`, byte-identical (`test_make_tram_bell.py`). No level has
  been graded for it, the horn or the beep (`Q178`).
- **Lamps** (`Q177`): the head lamp is on `headlamp_l` (`headlamp_c` is on no circuit and goes dark
  silently), side lamps on `foglamp_{side}`; lit by day too, the user's call. A close tram cannot
  be re-shot on demand: placement moves with `--shots`.
- **At a stop it winks left** (`Q187`): `TramSystem.at_stop`; `stops:` wink line.
- **The night beam** (`Q213`) goes through `TrafficBeams`; rules in `signals.md`.
