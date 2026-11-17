---
paths:
  - "tools/make_vehicle_sounds.py"
  - "tools/make_meter_beep.py"
  - "tools/make_tram_bell.py"
  - "etl/tests/test_make_sounds.py"
  - "game/assets/authored/audio/*"
  - "game/scripts/vehicle/taxi_audio.gd"
  - "game/scripts/vehicle/taxi_audio_profile.gd"
  - "game/tuning/taxi_audio.{tres,md}"
  - "game/default_bus_layout.tres"
  - "tools/make_bgm.py"
  - "etl/tests/test_make_bgm.py"
  - "game/scripts/audio/*"
  - "game/tuning/music.{tres,md}"
  - "game/tools/verify_music.gd"
---

# The sounds — before marking work done

`Q176`, `Q178`, `Q185`. Every `.wav` is synthesised by a script under `tools/`.

- **Any sound script**: run it, then `pytest tests/test_make_sounds.py` from `etl/` (byte-identical,
  silent ends on a one-shot, a loop's join and `smpl` chunk; the bell has `test_make_tram_bell.py`).
  Never edit a `.wav` or its `.import` by hand: a loop loops because the file carries a `smpl` chunk
  and the import's `loop_mode` is 0 (detect from WAV). `verify_vehicle` fails a loop that does not
  loop or a one-shot that does.
- **A loop is exactly periodic** or it clicks: tones on the loop's own grid (a horn's on 5 Hz),
  noise through `_band_noise`'s `irfft`, an engine loop whole cycles at its rpm.
- **Loops sit under events** (the user's call): engine, EV whine and wind 10–20 dB under the
  one-shots, the squeal a little under. Raise a loop only against a drive (`taxi_audio.md`).
- **The engine is a taxi's petrol four** (the user's calls): pulses through `_exhaust_gain`, nothing
  over 1.5 kHz, changes up by 4,000 rpm, −18 dB; an idle at 66 Hz vanished on phone speakers. A
  change owes the spectrum (under 150 Hz / 150–800 / over 1.5 kHz) and a rendered run-up to hear.
- `loop_rpms` and `ev_ref_kph` mirror the script's `ENGINE_RPMS` and `EV_REF_KPH`: change both.
- **`TaxiAudio` only reads the car**: `step_hit_mps` (never `take_impact_mps`, the fare's latch) and
  `wheel_slips`. A change in `vehicle_controller.gd` owes the `handling` rule's skidpad before and
  after, identical but for the cost column.
- The tiers are `skills.tres`' bars and the squeal's start is `skid_marks.tres`': read, never
  copied. `verify_vehicle` holds the gearbox (no hunting at 0–160 kph, three pedals), the crossfade
  (the louder loop within 0.64–1.56× of its pitch) and the tier and `materials` names.
- **The taxi is silent while `parked`** (`Q185`): loops fade over `park_fade_s`. `verify_vehicle`
  reads the LEVEL (a headless player with no stream holds no `stream_paused`). A voice is written
  only on a change, so never check for a write every tick.

## The music — `make_bgm.py`, `music.tres`, `drive_music.gd` (`Q246`)

Owed: `python tools/make_bgm.py`, `pytest tests/test_make_bgm.py` from `etl/`, `tools/check.sh`
(runs `verify_music`), and a drive HEARD — a level is never set off a number.

- **Thirteen loops of the same eight bars, in one `AudioStreamSynchronized`, only turned up and
  down**: four beds (stereo) and the combo's layers (mono; the three drum layers are two bars).
  Every file's length divides the bed's, or it drifts. Nothing is started, stopped or pitched.
- **The hour is the rig's** (`mood_from` on `RigCycle`'s scale), never a second clock; a resting
  rig plays `held_mood`. **The count is `FareSystem`'s combo signals**, never a poll.
- **The files share one scale**: `FULL` in the script mirrors `tiers`' last row, so that row over
  the loudest bed peaks at `PEAK`. Raise a row past it and the mix clips.
- A new bed or layer is a name in the script AND in `music.tres` (`test_make_bgm.py` holds the
  mirror). The day and night chords share three notes a slot so the beds cross-fade; keep that.
- Silent while `parked`, like the taxi. Its switch and slider are the `Music` bus
  (`Settings.apply_sound`); the sound's own are still the Master.
- ⚠️ The source `.wav`s are 16.7 MB in git, not LFS. Unheard on the web build and on a handset.
