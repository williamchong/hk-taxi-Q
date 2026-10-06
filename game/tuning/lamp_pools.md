# lamp_pools.tres

Rationale for `game/tuning/lamp_pools.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The light a street lamp throws on the road (`Q160`, the user's ask: "can the street light actually
light up the road?"), drawn by `lamp_pool.gdshader` on a cylinder of air under every lantern and
stood by `scripts/city/lamp_pools.gd` on the lamps' own 300 m cells.

🔴 **Not a light.** Forward Mobile pairs 8 spot lights with an object, a road chunk is one object,
Wan Chai stands 1,077 columns — about sixteen a chunk — and the taxis' beams already ration those
eight (`beams.md`). The pool adds to the frame already drawn wherever the depth buffer says
something stands inside the cylinder, so it lights the road, the kerb and the car alike and costs
one draw a cell. By day the cylinder collapses to a point and fills nothing.

Measured on the throttle route from the start line, `--debug-view=off --hud=off --fares=off`,
positions identical on both sides: by day 89 → 91 `draws` and 762,374 → 767,222 `prims` at t=1
(the cylinders' own triangles, drawn and unfilled).

## `render_priority = -1`

Before the outline's pass, which is the other reader of the frame: the line is drawn over a lit
road, not lit by the lamp.

## `shader_parameter/pool_gain = 6.0`

How much of what is already on screen the lamp adds back at the foot of the column. A lit surface
is its own colour brighter rather than a wash of lamp colour, so paint under a lamp stays paint.

## `shader_parameter/pool_floor = 0.05`

The part that does not depend on the surface. Night asphalt is near black and six times near
black is still near black; this is what makes the pool read on the road at all. ⚠️ Raise it and
the pool turns to fog on every surface alike.

## `shader_parameter/radius_m = 9.0`, `shader_parameter/drop_m = 11.0`

The cylinder: how far the light reaches on the ground, and how far under the lantern it looks for
one. `lamp_pools.gd` builds the mesh from these two, so they have one home. The drop is past the
9 m column so a road falling away under the arm is still inside; `spacing_drawn_m`'s median is
well over twice the radius, so pools stay pools and do not merge into a lit strip.
