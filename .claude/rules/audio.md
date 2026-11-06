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
---

# The sounds — before marking work done

`Q176`, `Q178`, `Q185`. Every file is synthesised by a script under `tools/`; the game plays it.

- 🔴 **The committed file is what the script writes**: run the script, then `pytest
  tests/test_make_sounds.py` (byte-identical, silent ends on a one-shot, a loop's join and its `smpl`
  chunk). Never edit a `.wav` or its `.import` by hand: a loop is a loop because the file carries a
  `smpl` chunk and the import's `loop_mode` is 0, "Detect From WAV". `verify_vehicle` loads every
  file and fails a loop that does not loop or a one-shot that does.
- 🔴 **A loop is exactly periodic**: every tone on the loop's own grid (a horn's on 5 Hz), every noise
  through `_band_noise`'s `irfft`, every engine loop whole engine cycles at its rpm. A new loop
  breaks one of these and clicks at every pass; the join test catches it.
- 🔴 **What is always there sits under what happens** (the user's call, 2026-11-06): the engine, the
  EV whine and the wind 10–20 dB under the one-shots, the squeal a little under. Raise a loop only
  against a drive, never on its own (`taxi_audio.md`).
- 🔴 **A petrol four is thump, not whine** (the user, 2026-11-06: the first engine read as "some kind
  of noisy motor"): pulses through `_exhaust_gain`, nothing over 1.5 kHz. 🔴 **And a taxi, not a sports
  car** ("sound like ferrari more than taxi"): it changes up by 4,000 rpm and sits at −18 dB. ⚠️ And not so low a phone
  cannot play it: a pass with the idle at 66 Hz vanished on small speakers. Measure the spectrum
  (energy under 150 Hz / 150–800 / over 1.5 kHz) and paste it; render the run-up from the shipped
  loops for the user to hear.
- ⚠️ **`loop_rpms` and `ev_ref_kph` mirror the script** (`ENGINE_RPMS`, `EV_REF_KPH`). Change both.
- ⚠️ **Read-only on the car**: `TaxiAudio` reads `step_hit_mps`, never `take_impact_mps` (the
  fare's latch), and `wheel_slips`. A change in `vehicle_controller.gd` owes the `handling` rule's
  skidpad before and after, identical but for the cost column.
- ⚠️ **The tiers are `skills.tres`' bars, the squeal's start is `skid_marks.tres`'**: read from
  those files, never copied. `verify_vehicle` holds the box (no hunting at 0–160 kph, three
  pedals), the crossfade (the louder loop within 0.64–1.56× of its pitch) and the tiers and
  `materials` names. Mutations caught by name: the downshift raised into a hunt, the crash bar
  exclusive, the door's open uncounted.
- ⚠️ **The PCK cost is measured from a PCK** (root rule), never summed from the WAVs.
- 🔴 **The taxi is silent while `parked`** (`Q185`, 2026-11-06): its loops fade over `park_fade_s`,
  as the horn does. `verify_vehicle`'s `_check_the_taxi_is_silent_parked` reads the LEVEL — a
  headless player with no stream does not hold `stream_paused`. A voice is written only on a
  change, so a check that a write happened every tick is wrong by design.
