# city_preview.tscn

Rationale for `game/scenes/dev/city_preview.tscn`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## `[node name="Regions" type="Node3D" parent="."]`

Every synced region at its offset from the frame (`P5-9c`): `region.tscn` once per region, each
with a `tile_preview.gd` added as its `Tiles`. The layers are here as well as in the drive because
the two fixed colour viewpoints `Q27` judges the palette from are shot in this scene, and the heroes
because without them it shows holes where the excluded buildings stood; each node is argued in
`region.md`. The camera frames the frame region, which is the box `built` forwards.

Every tile and, since `P5-6`, every road chunk `city.json` names, at once: the
drivable surface (`P1-4`) is one chunk per tile now, each with the `-col`
trimesh the wheels stand on, and `tile_preview.gd` draws them here the way
`CityStreamer` streams them in the drive. There is no `RoadSurface` node any
more. Every layer node in `region.tscn` prints its collider count for the opposite reason
— there must be none — and each says why (`Q74`).

## `[node name="Fares" type="Node3D" parent="."]`

`P1-5`'s fare nodes. Visible by default, unlike the graph diagnostic below,
because nothing else in this scene draws them and they do not z-fight anything
— the pins sit in the air and the tethers are lifted clear of the carriageway.

## `[node name="Roads" type="Node3D" parent="."]`

The `P1-3` graph diagnostic, kept and hidden. It draws flat ribbons at the
same heights the surface now occupies, so leaving both on z-fights; switch it
back on to read one-way arrows or elevation levels off the graph itself.
