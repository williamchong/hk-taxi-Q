# taxi_audio.tres

How the taxi's sounds are played (`P3-79`, `Q185`): `TaxiAudio` off the car, `TaxiHire` off the
fare. The files are `tools/make_vehicle_sounds.py`'s.

Every key `TaxiAudioProfile.usable` names is required (no defaults; the taxi stays silent on a
zero). The decibel levels and `hybrid` are not guarded, since 0 dB and off are real choices; the
writer drops them at those values (`hybrid` and `impact_db` are absent: off and 0 dB).

No level is graded by a number; all are owed the user's ear. One rule holds (the user's call):
loops that run the whole drive (engine, EV whine, wind) sit 10–20 dB under the one-shots, and the
squeal a little under them. Raise a loop only against a drive.

## Engine and gearbox

- `hybrid` (absent, off): the Crown Comfort LPG's four through a 4-speed automatic, matching
  `crown_comfort.tres`. On is the Comfort Hybrid: EV whine and a CVT drone.
- `loop_rpms = (1050, 2520, 5040)`: mirrors `make_vehicle_sounds.ENGINE_RPMS`. Each is an rpm at
  which an engine cycle is a whole number of samples at 22,050 Hz. Crossfaded between neighbours.
- `idle_rpm = 800`, `redline_rpm = 6000`: a 1TR-FPE's.
- `rpm_per_kph = (103, 55, 37, 27)`: typical Toyota 4-speed ratios (2.8 / 1.5 / 1.0 / 0.73) and a
  4.3 final drive on 0.31 m wheels. Top gear at 140 kph is about 3,800 rpm.
- `upshift_rpm = 4000`, `upshift_light_share = 0.6`, `downshift_rpm = 1200`: a pedal-down change
  at 4,000 and a light-pedal one at 2,400; at 5,000 the user heard "a ferrari more than a taxi".
  The downshift must sit under the light change's landing rpm in the next gear or the box hunts:
  the lowest landing is 2,400 × 55 / 103 = 1,282. A share under 0.59 hunts; `verify_vehicle`
  sweeps it.
- `stall_rpm = 1800`: the torque converter lets the engine run this far over idle at rest with the
  pedal down.
- `rpm_slew = 6000`: the heard rpm follows the box at this rate per second, so an upshift is a
  drop over about a sixth of a second, not a cut.
- `engine_db = -18`: lowered twice on the user's "need less engine noise".
- `off_throttle_cut_db = 6`, `pedal_up = 0.05`, `off_throttle_ease_db_s = 40`: under 5% pedal the
  engine drops 6 dB, eased over 0.15 s so a keyboard's all-or-nothing pedal does not step the
  level.
- `park_fade_s = 0.6`: parked (menu showroom, HOME, REPORT) the loops fade to silence and pause
  (the user's call). One-shots already playing finish.

## Hybrid only

- `ev_ref_kph = 50` (mirrors `EV_REF_KPH`), `ev_db = -20`, `ev_pitch_min = 0.05`,
  `ev_pitch_max = 2.0`: the whine's pitch is speed over `ev_ref_kph`, clamped.
- `engine_on_kph = 45`, `engine_on_throttle = 0.6`, `cvt_low_rpm = 1200`, `cvt_high_rpm = 4800`:
  when the engine starts, and the CVT's rpm band, held by the pedal.

## Tyres and wind

- `skid_full_slip = 2.0`, `skid_db = -10`, `skid_pitch_rise = 0.15`: the squeal starts at
  `skid_marks.tres`'s `mark_from_slip` (read from that file, so sound and marks start together)
  and is full at twice the tyre's peak, 15% higher in pitch.
- `skid_full_kph = 60`, `skid_slow_share = 0.3`, `skid_speed_pitch = 0.2`: the squeal follows
  speed too (the user's ask): 30% of the level at a crawl, full by 60 kph, pitch ±10%.
- `wind_from_kph = 30`, `wind_full_kph = 140`, `wind_db = -22`, `wind_pitch_still = 0.8`,
  `wind_pitch_rise = 0.4`: nothing under 30, full at top speed. The quietest loop.

## Impacts

- `tap_min_mps = 1.5`, `impact_cool_s = 0.25`: under 5.4 kph a contact is silent. The tiers above
  are `skills.tres`'s bump and crash bars, so the crash heard is the one docked. A second hit
  inside a quarter second is the same impact.
- `materials`: what a struck body is, by a piece of its node's name (the traffic's `car_<id>`,
  `tram_<n>`, the parked library's `<kind>_col_<n>`, the trees' `<mesh>_trunks_<x>_<z>`, the
  fence's `barrier_col_<n>`). First match wins; no match is a wall.
- `scrape_from_mps = 1.0`, `scrape_full_mps = 10.0`, `scrape_db = -6`: the grind along a wall, by
  sliding speed.
- `land_min_air_s = 0.3`: a kerb hop is not a landing. A little under `skills.tres`'s `air_min_s`.

## Cabin

- `cabin_db = -2`: the flag, the payout and the indicator relay, not positioned.
- `relay_off_pitch = 0.8`: the relay ticks at 1.0 and tocks at 0.8. It follows
  `VehicleLamps.indicator_lit`, so indicators and hazards alike. Its level is the file's:
  `test_the_indicator_relay_is_heard_beside_the_cabin_s_other_sounds` holds it within 4 dB of the
  flag and the card reader.
- `shot_pitch_jitter = 0.06`: every one-shot's pitch is scattered ±6%.
- `coin_hkd = 2.0`, `coin_max = 15`, `coin_gap_s = 0.07`, `coin_after_s = 0.35`: at delivery, a
  coin per HK$2 of tip after the reader's beep, capped so the longest payout is about 1.4 s.
