# signboards_neon.tres

The signboards' neon tube (`P3-103`, `Q260`): `NEON_MATERIAL` in `etl/pipeline/signboards.py`,
dispatched by `SHADERS` in `tools/generated_scene_import.gd`. One quad over every board's lit face
but a screen's, `signboards.neon_lift_m` off it; the shader cuts it down to a tube round the rim,
so the board keeps its own colour and its own `face_glow` inside.

- The hue is the board's `COLOR_0` pushed from grey by `saturation`, then scaled until its
  brightest channel is 1. `saturation` 5.0: most surveyed boards are muted (a pinkish grey, a
  beige), and at 1.0 their tubes burned white; 3.0 still read pale on the beige boards
  (2026-11-22, four variants at `--time-of-day=0.95` on Hennessy Road and under the HKCEC
  footbridge). The face keeps its own colour; only the tube is pushed.
- `tube_inset_m` 0.15, `tube_width_m` 0.06, `corner_m` 0.2: metres on the face, read off UVs that
  are metres from its centre, so every board's tube is the same size. A board under 1.2 m on its
  short side takes a quarter of its half-side as the inset. A far tube never thins below a pixel.
- `neon_glow` 3.0: at the glow pass's 3.0 threshold, so the tube's brightest channel blooms
  where the face (`face_glow` 1.5) does not. 4.0 whitened the tube's core under the tonemap. Times the rig's `night_lights`, and the quad is cut away entirely by
  day, so the day look is unchanged.
- The tube's albedo is the board's own colour, unpushed: as `night_lights` leaves 0 at dusk the
  tube appears matching the face and glows in, rather than popping in as a coloured line.
- `roughness_value` 0.3: glass, smoother than the board's 0.6.
- Left on its imported `BaseMaterial3D` the quad draws a solid face over the board, so
  `verify_signboards.gd` checks the dispatch by `resource_path`.
