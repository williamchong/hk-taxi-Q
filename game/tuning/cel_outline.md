# cel_outline.tres

Rationale for `game/tuning/cel_outline.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The ink line round the city (`P3-64`, `Q158`, the user's ask, 2026-10-06), drawn by
`cel_outline.gdshader` on the `CelOutline` quad in both rig scenes, and shipped 2026-10-07 on the
user's pick from rendered frames: each edge in its own surface's hue at half its value, 1.0 px.

What the shader does and why it reads depth alone is in its header. The numbers:

- `ink_from_surface` 1.0 and `surface_darkness` 0.5 are the user's pick (2026-10-07) over black ink
  and over ×0.20 and ×0.35: the line is the frame's own colour on the nearer side of the edge, halved
  in linear light. ×0.20 read as ink, ×0.35 as coloured pencil, ×0.50 as a fine crease line.
- `line_width_px` 1.5 at rest. The user first took 1.0 ("outline thin", 2026-10-07) over the 1.5
  the hue variants were shown at, then asked for it bolder at rest "so that we can have thinner
  outline on speed" the same day. The drawn line is about twice the sample step, because both sides
  of a break test positive.
- `speed_thin_px` 0.5 / `speed_fade` 0.2 (`P3-65`, the user's ask, "all
  outline sensitive to speed"): at `car_outline.tres`'s `full_speed_kph` the line is 1.0 px and 80%
  strength. Thinner and fainter, never bolder — the user's own logic: speed smears edges, and a
  louder city at speed fights the road. The shader floors the width at 1.0 px, where it breaks into
  dots; the fade covers what width cannot. A first cut bolded with speed (1.0 → 2.0 px) and was
  turned round. An edge-weighted fade (0.3, plus 0.6 toward the corners) was rendered and
  not taken; its dial was dropped rather than shipped at zero. Read through the `outline_speed` global, which the car writes; a
  scene with no car keeps the resting line.
- `ink_strength` 1.0: the hue already softens the line, so it is laid at full strength.
- `edge_start` 0.004 / `edge_full` 0.03 are ratios of the Laplacian of inverse depth to the centre's
  own. A crease between two walls reads in the thousandths, a silhouette in the tenths.
- `edge_distance_m` 40 lifts both bars by one more of themselves every 40 m. ⚠️ At 0 the harbour,
  a plane seen grazing at 100 m and more, drew rows of ink stripes: the depth buffer's rounding read
  as a Laplacian. 40 cleared them on the `taxi` viewpoint while keeping the building creases on
  `street`.
- `fade_start_m` 120 / `fade_end_m` 240: the line is gone before the 250 m LOD1 switch
  (`tuning/streaming.tres`), so it never traces geometry about to change.

⚠️ **Thin things ink solid.** A lamp post or a sign pole narrower than about two line widths is
outlined from both sides and draws in its own darkened colour. That is the depth outline's nature, not a threshold: no
`edge_*` value outlines a pole without filling it.

Measured on the drive's `taxi` recipe: +1 draw call and +2 primitives, at every second of it.

⚠️ **Not measured: the pass break.** A visible depth-texture reader makes the Mobile renderer resolve
the 4x MSAA depth and copy it mid-frame, and the hue's `hint_screen_texture` is a second full-frame
copy; on a phone's tile GPU both are likely dearer than the taps (`Q158`). Owed to the `P3-9`
handset round; the cheap retreats are `ink_from_surface` 0 (drops the colour copy) or the rig's
`visible` off.
