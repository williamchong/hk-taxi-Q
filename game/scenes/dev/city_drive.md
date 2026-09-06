# city_drive.tscn

Rationale for `game/scenes/dev/city_drive.tscn`, kept beside it because Godot's resource writer
drops every comment on save. Each heading is the line the block sat above;
`Overview` is the file as a whole. `tools/check.sh` requires this file to exist
and stay non-empty, and refuses any `;` line in the resource itself.

## Overview

The first scene that puts the car on the real city (`P1-4` + `P0-5`).

`city_preview.tscn` is for looking at the ETL output; this is for driving it.
The two are separate because they answer different questions and want
different cameras — and because a free-look camera in a scene with a physics
body is a scene where nobody is sure what they just judged.

It exists to put a real answer under `Q8` — whether real Wan Chai geometry is
fun to drive — which a grey box could not.

Since `P2-1` the tiles stream from `city.json` rather than being instantiated
wholesale by a dev preview, so this is no longer only a dev scene: it is what
`run/main_scene` boots and the closest thing to a build the project has. The
buildings still carry no collision — that is an ETL product, see PROGRESS.md.

## `[node name="Tiles" type="Node3D" parent="."]`

`camera_path` points at the Camera3D inside the rig, not at the rig and not
at the Taxi — the far plane is on the camera, and it is the camera a look-back
swings away from the car. See city_streamer.gd for the rest.

## `[node name="RoadSurface" type="Node3D" parent="."]`

The drivable surface (`P1-4`): the one generated layer that COLLIDES — its
`-col` mesh is what the wheels stand on, and `verify_road_surface.gd` asserts
it is there. Every layer node below prints its collider count for the
opposite reason — there must be none — and each says why (`Q74`).

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

## `[node name="Signals" type="Node3D" parent="."]`

The published traffic signal heads (`P3-17`), one mesh for the whole region,
standing on the kerb the ribbon actually drew rather than where they were
surveyed — nearly three quarters of them were surveyed inside it. Static and
**unlit**: no dataset publishes signal timing, an invented cycle instructs, and
nothing obeys it until `P3-3`'s traffic exists. A region whose publisher spells
its codes outside `head_prefixes` ships none and this node simply stays empty.
No collider: a signal post is a 60 mm prism at every junction mouth, so
modelling it as collision geometry before `P2-6` has measured a frame on the
device floor is the wrong order — and a car catching one mid-drift is a worse
failure than passing through it. `B3` revisits it; breakaway poles are the
genre's answer, and that is an effect rather than a shape.

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

## `[node name="Taxi" parent="." instance=ExtResource("4_taxi")]`

⚠️ This transform is a FALLBACK, not the start line. Since P2-3 the spawn is
resolved at runtime: drive_harness.gd asks RoadSpawn for a fare node and calls
place_at, so what is written here only survives on a clone with no generated
assets — where there is no road to drive on either. The harness prints the gap
between the two when it exceeds AUTHORED_DRIFT_M.

It is left in place because it puts the camera somewhere sensible while the
"run the ETL" warning gets read, and because it records what the query should
produce: eastbound in the nearside lane of Expo Drive underneath HKCEC Phase
II, 2.56 m off the centreline, road surface + 1.0 m.

Do NOT hand-edit it to move the spawn — set `spawn_fare_id` on the root, which
defaults to RoadSpawn.DEFAULT_FARE_ID. And do not rewrite these twelve floats
from a direction: they are row-major while "forward" is the -Z column, so
writing them as columns transposes the basis, which is undetectable on a
north-south street. road_spawn.gd carries that argument in full;
tools/verify_spawn.gd is what asserts the resolved basis against the edge.

See docs/ARCHITECTURE.md "To drive it".

## `[node name="GraphOverlay" type="Node3D" parent="."]`

`P2-2`'s debug overlay: what `RoadGraph` believes is under the car, drawn on
the road and written out as text. Dev-only, and after the Taxi so the node it
follows already exists when it looks for it.

## `[node name="Camera3D" type="Camera3D" parent="CameraRig"]`

400 m, not the fly camera's 2 km. The region is only 1.66 km across, so a 2 km
far plane culls nothing at all, and a chase camera 6.5 m behind a car in a Wan
Chai street canyon cannot see past a couple of blocks anyway. Measured: 94 draw
calls and 2.06 M primitives at 2 km, against 48 and 1.16 M at 400 m, with
nothing visible lost at street level.

## `[node name="Hud" type="CanvasLayer" parent="."]`

The player's HUD (`P3-24`) — speed, the street you are on, and three reserved
slots that `P3-5a` and `P3-5b` fill. Last in the scene so the Taxi it reads
already exists when it first looks, and on layer 10 so `DebugHud` (127) and
`FpsCounter` (128) still win the corners when someone turns them on.

⚠️ `--hud=off` frees it. That is for `P3-9` first — the authenticity test is a
drive with the direction arrow disabled, and a permanent street plate is
closer to a navigation aid than that test's premise assumes — and for clean
art-review frames second.
