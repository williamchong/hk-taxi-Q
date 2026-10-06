# cel_outline.tres

Rationale for `game/tuning/cel_outline.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The ink line of the city's cel look (`P3-64`, `Q158`, the user's ask, 2026-10-06), drawn by
`cel_outline.gdshader` on the `CelOutline` quad in both rig scenes. The quad ships hidden, so these
numbers draw nothing until a rig shows it; the user picks from the rendered variants first.

What the shader does and why it reads depth alone is in its header. The numbers:

- `line_width_px` 1.0 is the trial's thin line; the bold variant is 1.5 with `ink_strength` 1.0. The
  drawn line is about twice the sample step, because both sides of a break test positive.
- `edge_start` 0.004 / `edge_full` 0.03 are ratios of the Laplacian of inverse depth to the centre's
  own. A crease between two walls reads in the thousandths, a silhouette in the tenths.
- `edge_distance_m` 40 lifts both bars by one more of themselves every 40 m. ⚠️ At 0 the harbour,
  a plane seen grazing at 100 m and more, drew rows of ink stripes: the depth buffer's rounding read
  as a Laplacian. 40 cleared them on the `taxi` viewpoint while keeping the building creases on
  `street`.
- `fade_start_m` 120 / `fade_end_m` 240: the line is gone before the 250 m LOD1 switch
  (`tuning/streaming.tres`), so it never traces geometry about to change.

⚠️ **Thin things ink solid.** A lamp post or a sign pole narrower than about two line widths is
outlined from both sides and draws black. That is the depth outline's nature, not a threshold: no
`edge_*` value outlines a pole without filling it.

Measured on the drive's `taxi` recipe: +1 draw call and +2 primitives, at every second of it.

⚠️ **Not measured: the pass break.** A visible depth-texture reader makes the Mobile renderer resolve
the 4x MSAA depth and copy it mid-frame, which on a phone's tile GPU is likely dearer than the five
taps (`Q158`). The handset's frame time decides it, before the line is turned on.
