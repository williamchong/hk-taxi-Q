# moored.tres

How the Star Ferry at Wan Chai Ferry Pier rocks at its berth (`Q254`): `MooredProfile`, read by
`scripts/city/moored.gd`, which `landmarks.gd` stands at every `afloat` entry of `landmarks.json`.
The hull rests at `basemap.water_level_m` (the ETL places it there) and this moves it about that
rest: a heave, a roll about its long axis and a pitch about its beam, each one sine.
`verify_landmarks.gd` checks that the motion reaches its amplitude and that the hull, drawn
`hull_below_m` under the water in `tools/make_landmark.py`, never lifts a gap into view at the
worst sum of the three.

**Why a swell of its own and not the water shader's waves.** `water.gdshader`'s chop has 6 m
crests at 0.25 Hz (`water.md`). Over a 35 m hull a 6 m train averages to almost nothing, so a hull
that took the shader's waves would barely move, or would jitter if sampled at a point. A moored
ferry answers the harbour's longer swell and the wash of passing traffic, so the periods here are
seconds long and the amplitudes small. The trains are not matched point for point; the water's
shading moves and the hull moves, which is what reads from the quay.

- `heave_m = 0.08`, `heave_period_s = 5.3`: a slow 16 cm rise and fall in all. More and the hull
  reads as afloat in open sea, not tied up at a pier.
- `roll_deg = 1.2`, `roll_period_s = 6.7`: the lean a driver notices first, because the masts and
  wheelhouses swing it. 1.2° moves a mast top about 20 cm.
- `pitch_deg = 0.35`, `pitch_period_s = 4.1`: small, because a 35 m hull is stiff end to end; the
  ends move about 10 cm.
- The three periods share no small multiple, so their sum does not visibly repeat. Periods are in
  real seconds, read off the engine's clock, and keep running through a pause as the water does.
