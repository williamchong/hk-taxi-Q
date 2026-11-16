# water.tres

The harbour's water plane: `water.glb`, drawn flat at mean sea level by `region.tscn`'s `Water`
node. `tools/generated_scene_import.gd` maps the ETL's `sea_water` material name to this file;
`verify_water.gd` checks the dispatch by `resource_path`, because the fallback (matte, pale) is a
quiet failure.

`water.gdshader` is vertex colour times the rig's exposure plus two crossed sine wave trains in
world plan that tilt the shading normal and lift the crests. No texture (`Q63`).

No colour here: the albedo is `sea_water` in `hong_kong.yaml`'s `materials:` (8.2%, cited). Do not
lighten it to make the harbour bluer. The blue is the reflected sky, and its dial is
`roughness_value`.

- `roughness_value = 0.45`: at 0.15 the harbour is a near-white mirror of the horizon haze; at
  0.45 the reflection spreads and the sea reads as one deep blue plane (the user asked for blue).
- `wave_length_m = 6.0`, `wave_ratio = 0.6`: the first train's crest spacing, and the second's as
  a share of it. Harbour chop: a visible pattern from the quay, short of moiré at distance.
- `wave_cross_deg = 53.0`: the angle between the trains. 90 tiles into a chequerboard; under about
  30 they merge into one stripe.
- `wave_speed_hz = 0.25`, `wave_speed_ratio = 0.7`: slow, so it does not strobe under a fast car.
  The second train runs the other way at 0.7 of the rate. `TIME` wraps at `time_rollover_secs`
  (3600 s), so each train's cycles per wrap must be whole (900 and 630) or the sea jumps once an
  hour; 0.33 Hz would.
- `wave_slope = 0.12`: the normal leans about 7°, which bands the sky's reflection. Raise it
  before `crest_lift` if the water reads flat.
- `crest_lift = 0.12`: crests 6% lighter, troughs 6% darker. Small on purpose: it departs from the
  cited albedo.
- `wave_bearing_deg = 20.0`: the first train runs roughly along the harbour. A bearing, because
  the frame's north is -Z (`crs.py`).
