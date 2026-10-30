# signal_heads.tres

Rationale for `game/tuning/signal_heads.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The signal heads' material (`P3-3e`, `Q173`): `MATERIAL` in `tools/make_signal_heads.py`,
dispatched by `tools/generated_scene_import.gd` onto the AUTHORED `heads.glb`. Its own shader,
`signal_head.gdshader`, because the lamp is read from `INSTANCE_CUSTOM` — the light
`SignalHeads` writes from `SignalController.light_at` — against the lens circuit the mesh carries
on `UV.x` (never `COLOR_0` alpha, which the Compatibility renderer reads as 0). The housing and the unlit glass are on the vertex (`signals.heads.drawing`);
only the LIT colour and its brightness are here.

⚠️ **Its fallback failure is the quiet one**: a head left on its imported `BaseMaterial3D`
draws the right box with every lens dark, so `verify_signals.gd` checks the dispatch by
`resource_path`. 🔴 **Lit by day** — a driver reads a signal at noon, so the emission does not
multiply `night_lights` (the cars' brake lens is the precedent); the night only raises it.

## shader_parameter/body_roughness

0.7: a painted cast housing, duller than a sign plate's 0.55, so a head does not catch the sun
the way the sheeting beside it is meant to.

## shader_parameter/lamp_red

The lit red, the amber and the green below: saturated lamp colours rather than TD's printed
ones, because nothing published states a lamp's emitted colour. Green leans blue-green, as an
LED aspect reads on the street. An art call; render the junction by day and night to change it.

## shader_parameter/lamp_amber

See `lamp_red`.

## shader_parameter/lamp_green

See `lamp_red`.

## shader_parameter/lamp_emission

3.0: bright enough that a lit aspect reads against the noon sky at a stop line's distance,
without blooming over the housing. Zero in the shader, so a material that forgets it shows a
dark head, which a frame catches, rather than a lamp at a guess.

## shader_parameter/lamp_night_gain

2.0: the night doubles the day's emission, so a lit aspect glows after dark as the cars' lamps
do, but never goes out by day.
