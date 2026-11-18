# far_view.tres

How far a region's far version is drawn from (`Q249`): `FarViewProfile`, read by the `Backdrop`
node of `scenes/region.tscn`, which `CityRegions` also stands up for a region synced for its far
version alone. `city_layer.gd` hides each far mesh whose box lies further than `max_far_m` from
the camera, measured to the box's nearest point, so a far sea the camera stands over is never
hidden. `verify_backdrop.gd` holds the node to this file and the reach to past the street's far
plane.

- `max_far_m = 8000.0`: where the fog has a block. `noon.tres`'s `fog_density` 0.00025 fogs
  `1 − e^(−0.00025 d)` of it: 53% at 3 km, 71% at 5 km, 86% at 8 km. Fog is computed from the true
  view position (`far_shore.gdshaderinc` squeezes only the clip position), so a far version is
  fogged at its real distance. Sha Tin, ~11 km from Wan Chai, is past it; Tsim Sha Tsui and Mong
  Kok, 1–4 km, are not.
- `hysteresis_m = 100.0`: a box is shown again only 100 m inside the reach and hidden 100 m past
  it, so one on the edge does not flicker with the camera's shake. A region's box is kilometres
  across, so the margin is a few percent of the cut's distance.
