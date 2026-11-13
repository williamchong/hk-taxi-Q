# traffic_beams.tres

Rationale for `game/tuning/traffic_beams.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The light a moving vehicle's headlamps throw on the road at night (`Q213`, the user's ask: "all
traffic cars not parked in road should have big lamps turned on at night so that player can see
nearby and incoming traffic also via lighting"). Drawn by `traffic_beam.gdshader` on a box of air
ahead of each nose and stood by `scripts/traffic/traffic_beams.gd`, one `MultiMesh` for the
traffic and one for the trams. Parked vehicles (`ParkedLayer`) throw none: nothing hands them over.

🔴 **Not a light**, for `lamp_pools.md`'s reason: Forward Mobile pairs 8 spot lights with an object,
a road chunk is one object, and the taxi's beams already ration those eight (`beams.md`). The beam
adds to the frame already drawn wherever the depth buffer says something stands inside its cone, so
it lights the road, the kerb and the car ahead alike. By day the box collapses to a point and fills
nothing; at dusk it fades in with `night_lights`.

## `render_priority = -1`

Before the outline's pass, as the pools: the line is drawn over a lit road, not lit by the lamp.

## `shader_parameter/beam_colour = Color(1, 0.96, 0.88, 1)`

A halogen white, cooler than the lanterns' sodium (`lamp_pools.tres`' `pool_colour`), so a car's
light reads apart from the street's on the same tarmac.

## `shader_parameter/beam_gain = 8.0`, `shader_parameter/beam_floor = 0.16`

The pools' pair, louder than the lanterns' 6.0 / 0.05 because the ask was "big lamps": night
asphalt is near black, so the floor is what makes a pool read at all. Rendered 2026-11-14 on
`f_045`'s run at `--time-of-day=1` against an oncoming bus: 4.0 / 0.04 was a grey smear the eye
had to look for, 8.0 / 0.16 a pool that reads at a glance, and 12.0 / 0.32 at 30 m a headlamp
sweep — the user's to pick between (`Q213`).

## `shader_parameter/reach_m = 24.0`, `shader_parameter/spread_deg = 14.0`

A dipped beam: long enough to show round a corner before the car does, short of the next junction.
The cone opens from the body's own width (`INSTANCE_CUSTOM.r`), so a bus throws a wider pool than a
car. `traffic_beams.gd` builds the box from both, wide enough for the fleet's widest body.

## `shader_parameter/drop_m = 3.0`, `shader_parameter/rise_m = 1.2`

How far under the lamps the box looks for a road — past a ramp falling away ahead — and how far
above them the light reaches at `reach_m`: a car ahead is lit to its boot, a wall to its knee,
never a façade.

## `shader_parameter/lamp_height_m = 0.7`

The lamps over the ground under the body, read by `traffic_beams.gd` alone, which stands each box
from it. One height for every kind: the box is dipped from it, and a bus's higher lamps only move
the soft top.

## `shader_parameter/draw_m = 140.0`

Past this from the camera a beam fades and then is not drawn. Every box is drawn with the depth
test off, so this is what bounds the fill: a car past it is a pair of lit lenses and nothing more,
which is what a far car looks like at night anyway.
