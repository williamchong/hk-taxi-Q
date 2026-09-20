# region.tscn

Rationale for `game/scenes/region.tscn`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

One region's content, placed once per synced region by `CityRegions` (`P5-9c`). Every node here
reads its own region's bundle — `CityRegions` sets each one's `region` before it enters the tree —
and everything it draws is authored in that region's frame, so the one translation on the region
node places all of it. Both `city_drive.tscn` and `city_preview.tscn` instance this, which is why
`verify_city.gd` holds this file, not those two, against `generated_layer.gd`'s table.

There are no tiles here. They are the one child the two scenes disagree on — the drive streams them
(`CityStreamer`), the preview loads every one (`tile_preview.gd`) — so `CityRegions` adds them, as
the region's first child, according to whether it was given a `StreamingProfile`.

## `[node name="Tramway" type="Node3D" parent="."]`

The tramway (`P3-14`), beside the road surface rather than under it: it is a
separate mesh at the position iB1000 publishes, and `Q58` measured that this
is *not* on the carriageway — only 18.8% of cross-sections have both tracks
on the drawn ribbon, and 1.5% on Hennessy. A region whose sources publish no
tramway ships none and this node simply stays empty.
No collider: it has no `-col` suffix, it lies on ground that is already solid
(`P3-10`), and a 30 mm rail modelled as collision geometry is a kerb the
player cannot see the point of.

## `[node name="Arrows" type="Node3D" parent="."]`

The turn arrows (`P3-15`), beside the road surface for the same reason the
tramway is — separate geometry; one draw call per glyph code since `P5-4`
made it a library stood by `arrows_placements.json` — but for the opposite
geometric reason. The tramway is separate because `Q58` measured it is *not* on the
carriageway; the arrows are separate because they are, and drawing them on it
would put them under `road_markings.tres`'s 6 m junction fade at exactly the
junctions they are about. A region whose sources publish no marking symbols
ships none and this node simply stays empty.
No collider, for a sharper reason than the tramway's: an arrow lies flat
across a lane the car drives along, so a collider is a step every vehicle in
the region crosses at speed rather than one at the edge of the road.

## `[node name="BoxJunctions" type="Node3D" parent="."]`

The published yellow box junctions (`P3-18`), one mesh for the whole region,
drawn over the caps the ribbon markings fade away from. A region whose
sources publish no box polygons ships none and this node simply stays empty.
No collider, for the arrows' reason: the hatch lies across the middle of
every boxed junction, so a collider is a 12 mm step every vehicle crosses at
speed.

## `[node name="Crossings" type="Node3D" parent="."]`

The published pedestrian-crossing stripes (`P3-35g2`), one mesh per paint —
light-signal yellow and zebra white — drawn at their surveyed extent. A region
whose sources publish no crossing lines ships none and this node stays empty.
No collider, for the arrows' reason: a stripe lies across the whole carriageway.

## `[node name="RoadMarks" type="Node3D" parent="."]`

The published stop and give-way lines (`P3-23`), one mesh for the whole
region, drawn across the junction mouths the ribbon markings fade away from.
Lifted 16 mm — a clear millimetre above the arrows — because where the two
overlap the bar is the boundary and the arrow is an instruction already read.
A region whose sources publish no transverse markings ships none and this
node simply stays empty.
No collider, and this layer is the sharpest case for it: a stop line crosses
every approach in the city, so a 16 mm step modelled as collision geometry is
a kerb the player mounts at every junction while braking.

## `[node name="Railings" type="Node3D" parent="."]`

The published pedestrian railings (`P3-19`), standing on the kerb the
ribbon actually drew rather than where they were surveyed — two-thirds of
them were surveyed inside it. One panel per class since `P5-5`, tiled
along every run by `railings_placements.json`: three draw calls, as before.
A region whose sources publish no railing layer ships none and this node
simply stays empty.
No collider, and here that is a design decision rather than a rendering one:
`GAME_DESIGN.md` lists railings under "omit or make breakable" precisely
because a solid one turns a narrow street into a corridor. Collision is a
`B3` question.

## `[node name="Lamps" type="Node3D" parent="."]`

The published lamp posts (`P3-26`), one mesh for the whole region, standing on
the kerb the ribbon actually drew rather than where they were surveyed — 64.1%
of them were surveyed inside it — with a bracket arm reaching over the
carriageway. **Unlit**, and deliberately: `Q38` bakes the exposure into
`COLOR_0` at build time, `Q26` has not chosen a look, and `ART_DESIGN.md` says
to resist adding lights. A region whose sources publish no utility point layer
ships none and this node simply stays empty.
No collider: a lamp column is a 90 mm prism every twenty metres down every
kerb, so modelling 897 of them as collision geometry before `P2-6` has
measured a frame on the device floor is the wrong order — and a car catching
one mid-drift is a worse failure than passing through it. `B3` revisits it;
breakaway poles are the genre's answer, and that is an effect rather than a
shape.

## `[node name="Signs" type="Node3D" parent="."]`

The published traffic signs (`P3-16`), one mesh for the whole region, standing
on the poles TD surveyed rather than at the abbreviation points that name them
— those are drawing labels and sit a median 2.6 m away. Only the signs whose
meaning is their *shape* are here; the text-faced 2,364 are refused (`Q42`).
No collider, and unlike the railings that is a budget decision rather than a
design one: a sign post is a real obstacle a real car would hit, but 699 of
them is 699 collision bodies and `P2-6` has not measured a frame on the
device floor yet. Breakaway posts are a `B3` question.

## `[node name="Landmarks" type="Node3D" parent="."]`

The authored heroes, placed from `landmarks.json` (`P3-6`). Beside `Tiles`
rather than under it: the streamer owns what it streams, and a hero is
always resident.

## `[node name="Fence" type="Node3D" parent="."]`

The barriers dressing P3-29's fence, placed from `fence.json`. 🔴 Not
optional chrome: `RoadGraph.fits_car` refuses 14 drivable edges, and Q19
forbids a refusal the player cannot see — round 0 of P3-9a ended with three
drivers stopping at geometry they could not read. The prop is the only thing
in the barrier family that collides, and that is the point of it.
