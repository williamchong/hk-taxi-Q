# cel_outline.tres

Rationale for `game/tuning/cel_outline.tres` (`Q119`).

The ink line round the city (`P3-64`, `Q158`), drawn by `cel_outline.gdshader` on the `CelOutline`
quad in both rig scenes. The shader's header says how it works and why it reads depth alone.

- `ink_colour` near black: the user's pick on 2026-11-18 from a sheet of seven so the city sits in
  the vehicles' comic line (`Q248`). It also draws the black line round every vehicle, which is why
  they carry no outline pass of their own. Before it, each edge was its nearer surface's colour,
  halved in linear light: `ink_from_surface` 1.0 and `surface_darkness` 0.5, which exist only under
  the shader's `SURFACE_INK` define because reading the frame costs a full-frame colour copy.
- `ink_strength` 1.0: the hue already softens the line.
- `line_width_px` 1.5 at rest (the shader's default is 1.0). The drawn line is about twice the
  sample step. 2.5 was on the same sheet and
  refused: lamp posts and sign poles ink solid.
- `speed_thin_px` 0.5, `speed_fade` 0.2 (`P3-65`): at `car_outline.tres`'s `full_speed_kph` the
  line is 1.0 px at 80% strength. Thinner and fainter with speed, never bolder. The shader floors
  the width at 1.0 px. Read through the `outline_speed` global; a scene with no car keeps the
  resting line.
- `edge_start` 0.004, `edge_full` 0.03: ratios of the Laplacian of inverse depth to the centre's
  own. A crease reads in the thousandths, a silhouette in the tenths.
- `edge_distance_m` 40: lifts both bars by one more of themselves every 40 m. At 0 the harbour, a
  plane seen grazing, draws rows of ink stripes from depth rounding.
- `fade_start_m` 120, `fade_end_m` 240: the line is gone before the 250 m LOD1 switch
  (`streaming.tres`).
- `night_colour` `(0.6, 0.66, 0.8)`, `night_glow` 0.45 (`Q160`): as the rig's `night_lights` rises
  the colour blends, on the square, to a pale moonlit rim. `night_width_px` 0.0 and `night_reach`
  1.0 are no-ops. The shader's own defaults are the cyan, wider line the user refused as "too
  scifi"; do not let a key fall back to them.

Thin things ink solid: a pole narrower than about two line widths is outlined from both sides. No
`edge_*` value changes that.

Cost on the desktop: +1 draw call, +2 primitives. Owed to the `P3-9` handset round: the pass break.
A depth-texture reader makes the Mobile renderer resolve the 4x MSAA depth mid-frame. The colour
copy went with the own-hue ink (`SURFACE_INK` off). The retreat is the quad's `visible` off, and
the vehicles then want `vehicle_outline.gdshader` back (`vehicle_body.md`).
