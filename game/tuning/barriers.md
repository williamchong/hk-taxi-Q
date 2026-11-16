# barriers.tres

Rationale for `game/tuning/barriers.tres` (`Q119`).

Vehicle restraint: the railing layer's `CBARRIER` and `CRASHGATE`, as their own class (`Q61`). Same
shader as `railings.tres`; a class is a parameterisation, and the mask numbers are the whole
difference: two horizontal rails on posts, no balusters.

- `rail_colour`: authored. Bare galvanised grey is the conservative reading; the layer's `COLOR`
  field has no coded-value table (`Q60`), so nothing says which barriers are painted.
- `rail_roughness` 0.7: rougher than the pedestrian railing; galvanised steel weathers matte.
- `rail_metallic` 0.0: the only environment is sky, so a metallic rail renders sky blue (`P3-14`).
- `sky_zenith`, `sky_horizon`, `ground_reflection`, `rail_reflect`, `rail_face_on`,
  `fresnel_power`: `railings.tres`'s sheen and values (`Q168`).
- `baluster_width_m` 0.0: no balusters; zero width is the shader's "off". `skirt_top_m` 0.0: no
  skirt.
- `post_pitch_m` 3.0, `post_width_m` 0.14: heavier and further apart than a railing's posts.
- `top_rail_m`, `bottom_rail_m`: two rails, metres above the deck, against the class's `height_m`
  0.9 in `hong_kong.yaml`.

No collider in the asset: collision is the placer's (`Q159`, `region.tscn`'s `Railings` node,
`collides`).
