---
paths:
  - "etl/pipeline/config_blocks/buildings.py"
  - "tools/ring_weights.py"
  - "tools/facade_*.py"
  - "tools/lighting_rig.py"
  - "tools/frame_stats.py"
  - "etl/pipeline/colour.py"
  - "etl/tests/test_facade_*.py"
  - "etl/tests/test_colour.py"
  - "game/tuning/city_facade*.{tres,md}"
  - "game/assets/shaders/city_facade*.gdshader"
  - "game/assets/shaders/city_facade*.gdshaderinc"
  - "game/scripts/world/*.gd"
  - "game/tuning/{day_to_night,dusk,twilight,night}.{tres,md}"
  - "game/tools/verify_day_cycle.gd"
---

# Façade, materials and exposure — before marking work done

- **Height ramp or façade survey**: `tools/ring_weights.py`, paste what it derives. The surveyed
  material weights are authored against both and no check sees them go stale (`Q34′`).
- **Façade survey or `facade_hue.strength`**: `tools/facade_chroma.py`, paste its table into
  `docs/ART_DESIGN.md` (`Q30`'s argument holds only while it describes the shipped survey).
- **`materials:` colours, a material's `bounds:`, the rigs' `exposure_anchor`** (`Q38`, `P5-28c`):
  the ETL half and the game half move in ONE commit with `schema_version`. A shipped colour is a
  reflectance and the rig multiplies; one half without the other renders 1/0.520 off with nothing
  in a frame to say which. Owed: the per-material round trip, `facade_chroma.py --shipped` before
  and after, and the `Q27` / `Q31` cameras with the skyline shot at `t=2.0` (at `t=0.8` the
  streamer has not settled).
  - Correct a colour outside its `bounds:`; never widen the bounds to admit it. `bounds:` is the
    only part of `_check_reflectance` that can fail — its round trip is a tautology.
  - The exposure has one home, the rig scene, read by `tools/lighting_rig.py`. Never put the number
    into `etl/`.
  - `C*` scales by `anchor ** (1/3)` (0.804 at 0.520), which `facade_chroma.py` applies;
    `frame_stats.py --albedo-l` moves `gain` only.
- **Bands** — `survey_bands`, `STREET_BAND_M`, `BAND_FACE_TEXELS`, `FALLBACK_SPREAD_AB`, `band_hue`,
  `cut_bands`, `_ship_line`, `facade_hue.bands` (`Q197`); `band_lift`, `band_noise_l`,
  `FALLBACK_SPREAD_L`, `facade_hue.band_lightness` (`Q240`): re-run the survey with `--regions
  wan_chai causeway_bay`, keep the old table in `superseded/`, and its shipped columns must move on
  ZERO rows (a moved whole-building colour is a `Q37` change). Then the build's `facade bands` log
  line (no stale warning), `verify_tiles`, and the four `Q197` cameras against the commit before.
  - Rebuild `podiums` before the survey: a podium band is cut at the line `podiums.json` ships.
  - Cut one object's triangles only: `collapse` stitches seams across two (`verify_tiles`' 8 m box
    check).
  - Lightness is the street band's alone (`Q240`), a step from its own tower; the building's `L*`
    stays refused. `band_lightness` 0 must rebuild `Q197` byte for byte.
- **Filler guard** — `is_filler`, `filler_colours`, `MODAL_SHARE`, `MODAL_STRIDE` (`Q55`):
  `tools/facade_survey.py --all --filler-report`, paste its table. First re-run the survey with
  `MODAL_SHARE` above 1.0: it must differ from the shipped table on zero rows. A repeated GREY is
  `Q37`'s channel tie and stays out of the colour set. `facade_lab.json` is under gitignored
  `etl/sources/`; `superseded/` is the only way back.
- **The day cycle** — `lighting_rig.gd`, `rig_cycle.gd`, `rig_keyframe.gd`, `day_clock.gd`,
  `day_to_night.tres`, a keyframe's environment (`Q160`, `Q222`, `Q225`): `tools/check.sh` (runs
  `verify_day_cycle`), the `street` camera by day shot twice a side against the commit before, and
  frames at `--time-of-day=` 0, 0.36, 0.57, 0.71, 0.79, 0.86, 1, and past the loop 1.464, 1.607,
  1.661.
  - A resting rig writes nothing (it holds the authored `Environment` and sun), which keeps every
    scripted daylight frame. `DayClock.rest()` puts it back.
  - `time_of_day` 0 is the morning; the authored day is at `day_at`; a free drive's cycle comes
    round at `loop_at`; a shift never passes 1.0.
  - The daylight keyframes' angles and `at`s are solved together (`day_to_night.md`): never move
    one alone.
  - Measured shut (`Q160`): one rig blending, never two cross-fading; `exposure_anchor` does not
    move with the hour (it scales `COLOR_0` alone, so the dark comes from the light); night dims
    the key light, never deletes it — the last keyframe's energy sits under `vehicle_lamps.tres`'
    `night_energy` and the two move together.
  - A keyframe `.tres` is read only for `LightingRig.BLENDED` / `BLENDED_SKY`; its `Sky` has
    `radiance_size = 0` (a loaded sky holds 18 MB undrawn). A moved rig shrinks the authored sky's
    and restores it on `rest()` — the one write to the authored resource (`verify_day_cycle`).
  - A still preview camera at a pinned hour can stall the capture (`no frame drawn`): shoot at
    `--seconds=2 --shots=1.0` or from a moving drive. `drive.sh` appends `--day-cycle=off`.
  - `update_hz` is the sky's cost lever (`Q222`); the floor handset is unmeasured.
