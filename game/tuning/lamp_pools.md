# lamp_pools.tres

Rationale for `game/tuning/lamp_pools.tres` (`Q119`).

The light a street lamp throws on the road (`Q160`), drawn by `lamp_pool.gdshader` on a cylinder of
air under every lantern, stood by `scripts/city/lamp_pools.gd` on the lamps' own cells.

Not a light: Forward Mobile pairs 8 spot lights with an object and the taxis' beams already ration
them (`beams.md`). The pool adds to the frame already drawn wherever the depth buffer puts
something inside the cylinder, at one draw a cell. By day the cylinder collapses to a point.

- `render_priority` -1: before the outline's pass, so the line is drawn over a lit road and not
  lit by the lamp.
- `pool_colour`: `lamps.tres`'s `lantern_colour`.
- `pool_gain` 6.0: how much of what is on screen the lamp adds back at the foot of the column. A
  lit surface is its own colour brighter, so paint under a lamp stays paint.
- `pool_floor` 0.05: the part that does not depend on the surface, which makes the pool read on
  near-black asphalt. Raised, the pool turns to fog on every surface.
- `radius_m` 9.0, `drop_m` 11.0: the cylinder; `lamp_pools.gd` builds the mesh from these. The
  drop is past the 9 m column so a road falling away is still inside. The radius is under half
  the median lamp spacing, so pools do not merge into a strip.
