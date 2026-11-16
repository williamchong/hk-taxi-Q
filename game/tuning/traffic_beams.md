# traffic_beams.tres

The light a moving vehicle's headlamps throw on the road at night (`Q213`, the user's ask). Drawn
by `traffic_beam.gdshader` on a box of air ahead of each nose, stood by
`scripts/traffic/traffic_beams.gd`: one `MultiMesh` for the traffic, one for the trams. Parked
vehicles throw none.

Not a light, for `lamp_pools.md`'s reason: Forward Mobile pairs 8 spot lights with an object and
the taxi's beams already ration them (`beams.md`). The beam adds to the drawn frame wherever the
depth buffer has something inside its cone. By day the box collapses to a point; it fades in with
`night_lights`.

- `render_priority = -1`: before the outline's pass, so the line is drawn over a lit road.
- `beam_colour`: halogen white, cooler than `lamp_pools.tres`'s sodium `pool_colour`.
- `beam_gain = 8.0`, `beam_floor = 0.16`: louder than the lanterns' 6.0 / 0.05. Night asphalt is
  near black, so the floor is what makes a pool read. 4.0 / 0.04 was a grey smear and 12.0 / 0.32
  a headlamp sweep; the user's to pick between.
- `reach_m = 24.0`, `spread_deg = 14.0`: a dipped beam, shown round a corner before the car is.
  The cone opens from the body's own width (`INSTANCE_CUSTOM.r`).
- `drop_m = 3.0`, `rise_m = 1.2`: how far under the lamps the box looks for a road (a ramp falling
  away), and how high the light reaches at `reach_m`: a car's boot, never a façade.
- `lamp_height_m = 0.7`: read by `traffic_beams.gd` alone to stand each box. One height for every
  kind.
- `draw_m = 140.0`: past this from the camera a beam fades out. Boxes draw with the depth test
  off, so this bounds the fill.
