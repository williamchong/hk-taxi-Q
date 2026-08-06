# Art Design

## Direction

**Low-poly, flat-shaded, saturated. Accurate city, toy vehicles.**

That split is deliberate and is the core art decision:

| | Treatment | Why |
|---|---|---|
| **City** | Accurate proportions, real massing, real street widths (then widened for play) | Recognition is the product. Stylising building proportions destroys the one thing that makes this game worth making |
| **Vehicles** | Choro-Q / toy proportions — short wheelbase, oversized wheels, chunky | Charm and readability. Cars are what the player looks at for hours |

Stylise the actors, not the stage. A deformed Hopewell Centre stops being Hopewell Centre; a deformed
taxi is just cuter. **`Q8` measured this rather than assuming it:** driving the real city was judged
fun on the strength of recognition alone, which is what makes the expensive half of the trade worth
what it costs.

---

## Why the art style and the data choice are the same decision

The source data — 3D Visualisation Map (non-textured) and 3D-BIT00 Level 1 — is **extruded footprints
with no textures**. That is already a flat-shaded low-poly building. Consequences that make the whole
project affordable:

- No texture atlas packing, no KTX2 transcoding, no texture memory pressure
- Untextured meshes with vertex colours **merge into one mesh per tile**, which is what keeps draw
  calls under budget — 53 against a 150 budget, measured
- Geometry-only glTF quantises and compresses far better than textured assets

The art direction isn't a stylistic preference layered on top of the data. It *is* the data.

---

## Palette

Hong Kong-specific, not generic-city. Anchor colours:

| Role | Colour family | Notes |
|---|---|---|
| Building base | Warm off-white, beige, pale grey-green | HK tenement and podium concrete |
| Building accent | Muted terracotta, jade, faded blue | Older Wan Chai stock |
| Road surface | Dark warm grey | Not blue-grey; HK asphalt reads warm |
| Road markings | Bright white, saturated yellow | Yellow box junctions are iconic |
| **Player taxi** | **Red** with silver roof | HK Island urban taxi. Non-negotiable |
| Minibus | Cream body, **green** roof | Green minibus |
| Tram | Green and white | Instantly recognisable silhouette |
| Neon | Saturated magenta, cyan, gold — emissive | Sparingly; accent only |
| Vegetation | Deep saturated green | HK street trees are dark and dense |

**Time of day: golden hour by default.** Low warm sun flatters flat shading, gives long readable
shadows, and separates building faces without any texture work. Night (neon-forward) is a strong later
variant — plan the emissive channel now, build the mode later.

---

## Buildings

### General fabric (≈95% of buildings)

- Source: extruded footprints, untextured
- **Vertex colour**, assigned by ETL from height band and building class — no textures
- Flat/faceted shading, hard normals
- Subtle per-building colour jitter so blocks don't read as uniform

**The palette lives in `etl/config/cities/hong_kong.yaml` under `buildings:`**, not in code — five
height bands from warm beige for the low pre-war and post-war stock up to cool pale grey for
commercial towers, a flat concrete grey for `INFRASTRUCTURE`, and the jitter amount. Change it there;
change *why* here first. The jitter is seeded from each building's LandsD id, so it is stable across
rebuilds.

⚠️ **The jitter means a class is a *ray* through its base colour, not a value.** Any tool matching a
class by colour must test the scale factor, not equality — `tools/deck_error.py` matched 428 of
434,149 triangles before this was understood.

### The window-band shader

Cheap, and does more for "this is Hong Kong" than any other single technique. Instead of window
textures, a shader draws **horizontal banding in world space** on vertical faces — floor lines and
window rows, procedurally. Dense repetitive window grids are the defining visual signature of HK
residential towers.

```
Inputs:  face normal, TEXCOORD_0.x = metres above the building's own base,
                      TEXCOORD_0.y = surface marker + per-object phase
Output:  band mask → darkened window rows, occasional lit window (emissive at night)
Cost:    a few instructions, zero texture memory
```

⚠️ **`TEXCOORD_0.x` was specified here as `0-1` and ships as metres, which is a correction rather
than a detail.** Normalised, a vertex says what fraction of its own building it is up, and the shader
cannot recover the building's height from that — so a 3-storey shophouse and a 40-storey tower get
the *same number of window rows*. The floor count is the signature. In metres the row spacing is a
constant of the city rather than of the object, and the podium mask becomes an absolute height.

**The storey height is measured, not chosen: 2.8 m.** 227 walls on 219 buildings of one
individualised (textured) LandsD sheet, read offline and discarded — height-weighted median 2.77 m,
and Hong Kong's domestic floor-to-floor really is that tight. A guessed 3.2 would have put a storey
too few on every tower. Column pitch is measured the same way at 2.4 m. `docs/DATA_SOURCES.md`
records that the sheet does not enter the build path; `docs/PROGRESS.md` carries the distribution.

⚠️ **Two of those inputs have to come from the ETL, and they are why `P3-7` is one commit across both
sides.** A vertex knows its world Y, not where its building starts — a podium vertex and a 30th-floor
vertex are indistinguishable to the shader — and it has no seed at all, so neighbouring towers would
share a window pattern. Buildings ship **no UVs today**, so `TEXCOORD_0` is free, costs about 2 bytes
per vertex quantised, and survives vertex clustering through the same representative-selection path
that already carries colours.

⚠️ **Not `COLOR_0.a`**, although it is free and currently a constant `255`: the project-wide import
default sets `vertex_color_use_as_albedo`, and an opaque material ignores albedo alpha only until
somebody enables transparency on a tile, at which point the city goes see-through with no error.

A third thing comes for nothing once `TEXCOORD_0.x` exists: **darken the bottom couple of metres of
every building.** Grounding a wall where it meets the pavement does more for perceived quality than
per-building colour accuracy.

⚠️ **This said "bake a vertical gradient into `COLOR_0`" and is now done in the shader instead**,
because it was written before the height payload existed. Baking it would force `colour_for` to
materialise a per-vertex colour array where it currently returns a read-only broadcast view of four
bytes — real memory through the bucket phase, for a result `smoothstep(0, h, UV.x)` gives free.

Windows must **not** appear on roofs or ground-level podium faces — mask by normal and by height above
the building's own base. Both are in `assets/shaders/city_facade.gdshader`; the numbers are in
`tuning/city_facade.tres`, because they are tuning data (hard rule 4) and retuning the city must not
be a rebuild.

### The clean/futuristic variant

🔴 **Every façade element below is switched off in the shipping `city_facade.tres`, and the city is
massing plus flat per-building colour.** User's call on 2026-08-06, made from the driver's seat: with
`Q27` fixed, the measured per-building hue carries the city on its own, and the window grid was
competing with it rather than adding to it. **Parked, not deleted** — the shader keeps all of it and
seven parameters in one `.tres` hold it back, listed in that file's header with the values that
restore them. The rest of this section describes what is still in the shader and what turning it back
on would give.

⚠️ **This retires nothing above it and settles nothing in `Q26`.** Flat colour is where the look
rests while a new idea is found, not a verdict that the elements were wrong — they were judged
against a city whose albedo was arriving at a third strength, which is not a fair test of anything.
Anything reconsidered here should be re-judged against the fixed render first.

**A second look, shipping beside the first and switched by one file.** The window bands above are
accurate and were called **dull** on sight. The fault is *scale*, not colour: they are drawn at the
measured 2.8 m × 2.4 m pitch, which from a car at 30 m is about four pixels across — too fine to
read as architecture and too regular to read as material. `assets/shaders/city_facade_clean.gdshader`
draws the same city an order of magnitude larger and moves the unit of variation from the **window**
to the **building**.

Values below are the ones the `.tres` files actually ship, which are **not** the shader's own
defaults — the defaults are the first pass, and the corrections further down this section are why
they differ. `tuning/city_facade.tres` is the authority for the clean column and
`tuning/city_facade_warm.tres` for the warm one.

| | `city_facade` | `city_facade_clean` |
|---|---|---|
| Vertical unit | 2.8 m window row | 2.8 m glazing ribbon, doubled on 22% of buildings |
| Horizontal unit | 2.4 m column | 5.5 m structural bay, hashed ×0.72–1.45 per building |
| Per building | rows offset by phase | **treatment** — 38% solid mass, 62% glazed, 22% accented |
| Glass | flat dark mix | fresnel toward a sky colour |
| Distance fade | 90–240 m | 140–244 m |

Three renderer tricks do the work, and none of them is a texture:

1. **Per-building treatment**, hashed from the `TEXCOORD_0` phase the ETL already ships. Two in five
   buildings repeat *nothing*, which is what stops a block reading as one wallpapered surface.
2. **Fresnel sky reflection** — `pow(1 - dot(NORMAL, VIEW), p)` mixed toward a sky colour is a
   mirrored tower for a few ALU instructions, with no reflection probe. Probes stay an anti-goal.
3. **Grazing sky bounce** at low strength on solid wall, which is what keeps a white city from
   reading as grey card.

⚠️ **The podium mask is where this look breaks, and it breaks in exactly the frame the player
occupies.** `podium_height_m` protects shopfronts from being banded like flats — correct, and it
left the first build white card from kerb to cornice while every element sat forty storeys above a
1.5 m eyeline. The podium therefore gets its own elements rather than being a hole in the mask:
shopfront glazing at 0.7–4.6 m on **every** building, a cornice where the podium stops, and the
accent colour on the plinth rather than up the tower. Anything added to this shader must be asked
the same question: *is it visible from a car?*

⚠️ **The phase does not cure repetition, because offsetting one grid still leaves one grid.** Judged
against a street photograph, the fault was that every building was built in the same *grammar*. A
Hong Kong frame carries three or four at once — vertical-fin towers with continuous piers and no
horizontal banding at all, full mirror curtain wall, punched windows in solid stone, and horizontal
ribbon. So the seed picks a **grammar**, not just an offset, and the four are one grid with different
ratios rather than four code paths: a fin is the horizontal cut switched off and the piers widened,
curtain wall is both masks nearly open, punched is both nearly closed. The structural bay and the
storeys a glazing band spans are hashed per building too; only `floor_height_m` stays a constant of
the city.

⚠️ **A single reflection colour is why glass read as a swatch rather than a mirror.** Real glazing
shows the sky *gradient*, so the reflected ray's own elevation has to choose between horizon and
zenith — and below the horizon it reflects the city, which is darker than either. Two more things
follow, both nearly free: **curtain-wall panes are never flat**, and bowing the reflected ray per
pane is what produces the wavy light and dark bands down a real glazed facade; and **mirror glass is
not transparent when faced squarely**, so a fresnel that falls to nothing head-on leaves every wall
facing the camera a flat dark colour. ⚠️ Reflectance must not carry the whole surface either — Hong
Kong's curtain wall is heavily body-tinted and reads **dark while reflecting a bright sky**, so the
glass colour is what sets the value and the reflection only lifts it. Glass colour is hashed per
building across three tints; one glass colour across a district is as flat as one wall colour.

⚠️ **The first pass over-corrected, and "too coarse" looks worse than "too fine".** `P3-7` was called
dull for drawing at 2.8 m; the answer was *not* to move the glazing to a 5.6 m band, because at 52%
glass that is a 2.9 m black slot and a facade of them reads as a **parking garage deck**. One ribbon
per storey, glass that is not a hole (it only lifted at grazing angles, so a wall seen head-on went
to near-black), and a mullion wide enough to be a pier. ⚠️ **A mullion is wall, not a dark line** —
the pier between two panes is the same pale concrete as the facade, so it cuts glass away and must
not also darken what it reveals.

⚠️ **`band()` needs analytic antialiasing, not just `fwidth`.** Past about a quarter of a period per
pixel the smoothstep pair stops meaning anything and the grid turns into diagonal moire on any wall
seen at a shallow angle — which in a street of towers is most of them. Converge on the band's own
**duty cycle**, which is what infinite samples inside one pixel would average to. This is why the
grid does not need the distance fade to hide it — but it is *not* why the fade may be pushed out,
and the next warning but two is the constraint that actually decides where it ends.

⚠️ **The shopfront must not be on every building, and it cannot be on the *right* ones.** Applying it
unconditionally — "at street level even a solid mass has shops in it" — draws one dark ribbon along
an entire street, and it is the most repetitive thing in the frame precisely because it is the part
a driver is closest to. It is now hashed per building at a varying height, with podium piers much
heavier than a curtain-wall mullion so a shopfront reads as discrete openings.

⚠️ **But "true to the actual site" is not reachable from this data, and no amount of shader work
changes that.** The 3D Visualisation Map is geometry: **no land use, no building use, no ground-floor
attribute**. The shader knows height above its own base, a surface marker and a per-building seed, so
nothing in the pipeline can tell a shopfront from a plant room from an MTR entrance. Judged against
Convention Avenue, the fabric can be made *varied and plausible* and not *correct*. The honest routes
if that ever matters, cheapest first: **face a street** (the road graph is already in the ETL, so a
frontage test is build-time work and no new source); **land utilisation data** (a new dataset, a
schema bump, and a per-building attribute); or hand-authored `landmarks.json` entries for the
buildings that matter, which `P3-6` already provides for.

⚠️ **The distance fade must finish before the LOD switch, and that is a hard constraint rather than a
taste.** `tuning/streaming.tres` swaps to LOD1 at **250 m**, where buildings are clustered at 4 m
cells — and `TEXCOORD_0.x` comes from a *cluster representative*, so out there "metres above the
base" is wrong by up to a storey and a half and neighbouring triangles disagree about it. A grid
drawn on that shatters into blocky patches. `P3-7`'s 90–240 m fade was safe by being conservative;
moving it to 260–420 m on the reasoning that a 9 m bay survives to the far plane was true about
*aliasing* and ignored the tier entirely. The shipped fade is therefore **140–244 m**, finishing
just inside the switch. **Any change to `fade_end_m` must be checked against `tier_distances_m`.**

⚠️ **The horizontal coordinate must not be derived from the face normal.** The plan-perpendicular of
the normal gives every triangle of a *curved* facade its own grid origin, so the bays shatter into
per-triangle strips — chevrons wherever Hong Kong puts a round corner on a mall. It survived in
`P3-7` only because a 2.4 m column pitch made the seams read as noise. Project onto a world axis
*chosen* by the normal instead: continuous as the normal turns, at the cost of a little stretch near
45°.

💡 **And when something looks wrong in a preview scene, check what the preview scene draws before
blaming the shader.** `city_preview.tscn` instantiates `road_preview.gd`, which renders the road
graph as coloured lines and **1,125 direction arrows** — it says so in its own run log. Those were
mistaken for accent courses here. `city_drive.tscn` puts the same overlay behind `--debug-view`,
which is why it never appears in a drive shot.

⚠️ **What moire is left is very likely not the shader's.** Fine diagonal hatching survives on
surfaces around the flyovers, and `Q20` already records that **the flyovers are drawn twice**. Two
coincident surfaces with the same flat colour hide their fight; give each a *different* window phase
and it shows as a pattern. This is the same latent defect the roads section predicts the markings
shader will expose at junction caps — identical surfaces conceal an overlap, distinct ones reveal it.

⚠️ **Roofs are excluded from the grid and must not be excluded from the look.** Every element is
gated on `upness < wall_normal_max`, which left roofs at the full white wash — and a roof takes a 48°
sun nearly head-on, so it clipped where the wall beside it did not, and every downward view came out
as a white blob. `roof_darkness` is the whole roof treatment, and it is enough: nothing up there is
visible from a car.

⚠️ **"Washed out" was four settings each contributing a little**, and worth naming because none of
them is the obvious one. `tonemap_white` compressed highlights so nothing reached true white;
`ambient_light_energy` lifted the shadows; `glow_bloom` adds glow *regardless* of the HDR threshold,
which is a global lift rather than a bloom; and the fog hazed everything past ~100 m. The reference
look is bright **and high contrast** — blown whites against deep saturated shadow — so the lever is
always to raise the ceiling, never to raise the floor.

**Switching is data, and never a rebuild.** Both shaders read the same `TEXCOORD_0` payload and the
same surface markers, and `tools/generated_scene_import.gd` maps the ETL's material name to
`tuning/city_facade.tres` and only that path. `tuning/city_facade_warm.tres` holds the measured
values; `cp` it over and reimport. **Which look ships is `Q26`, and it is a verdict for `P3-9a`'s
drivers rather than something to settle here** — the clean look keeps the accurate massing and
abandons the accurate surface, and recognition is the product.

### What buildings will *not* get

- **No per-building texture, and no low-res atlas.** Any texture needs UVs, and UVs do not survive the
  vertex clustering that produces both shipped LOD tiers. It is paying to break the LOD system.
- 🚚 **"No colour sampled per building" has moved out of this list — buildings now get it.** All
  three original objections fell to measurement; see "Per-building façade colour" below and the
  `PROGRESS.md` entries of 2026-08-06. What survives of the objection is narrower and still binding:
  **the photographs' `L*` is not usable and is not used.**
- ⚠️ **What this document used to sanction — "re-author the five `height_bands` from clustered façade
  colour" — is measured and close to pointless.** Height explains **1.2% of `a*` and 0.8% of `b*`**
  across all 2,214 buildings, so re-authoring the bands while keeping height as the key moves the fit
  barely at all. **Height is not the signal**, and the ramp stays what it is: a *lightness* ramp,
  old-and-darker below to pale-above, which is the one thing height does predict (10.9%).

### Per-building façade colour

Every building carries its **own measured hue**, read offline from the individualised set's photo
textures and joined to the massing by the building id's stem. 2,214 buildings, 100% matched, and it
costs the runtime nothing: it lands in the `COLOR_0` the tiles already shipped, so there is no new
attribute, no schema change, no shader change and no interaction with the LOD clustering. Where an
atlas is unreadable a building falls back to its height band. `etl/config/cities/hong_kong.yaml`
holds the switch; `etl/pipeline/colour.py` holds the conversion and the reasoning.

⚠️ **Hue is taken and lightness is refused, and that is a measurement rather than a preference.**
Across the survey, the `L*` spread *within* one building — its four walls, same cladding, differing
only in which way they faced the sun — is **22.9 on average and 41.1 at p90**, against a
between-building spread of **16.25**. The confound is larger than the signal. Hue survives because
illumination moves value far more than it moves hue, so `a*`/`b*` are evidence and `L*` is a record
of the flight. Shipping it as albedo would bake that flight's shadows into the city for the engine's
sun to shade a second time. `facade_hue.strength` scales the measured chroma and is the *stylisation*
knob, kept separate so the two cannot be confused.

✅ **The city used to read pale, and neither the palette nor the rig was why.** `COLOR_0` is authored
in sRGB and was consumed as linear, so **57%** of a lit façade pixel's luminance was
albedo-*independent* and a per-building difference reached the screen at a third of its size. Closed
as `Q27` on 2026-08-06; the fix is a conversion in the two façade shaders and the road's
`BaseMaterial3D`, and the share falls to **6%** at street level.

⚠️ **The lesson is about the diagnosis, not the bug.** "The rig's light levels swamp albedo" was the
previous entry here, and it was wrong: ambient, exposure, glow, fog, the tonemap curve and specular
were each ablated and **none moved albedo transmission by more than 0.05**. A washed-out frame is not
evidence about the lights. Grade a pair of renders with `tools/frame_stats.py` and ask whether an
*albedo change* survives to the screen before touching anything — a rig can only redistribute
contrast that arrives.

### Hero buildings (~5)

Distinctive silhouettes need hand-authored low-poly models with light texturing, placed via
`landmarks.json`:

| Building | Why it needs authoring |
|---|---|
| **HK Convention & Exhibition Centre** | The curved "flying wing" roof |
| **Central Plaza** | Pyramid crown |
| **Hopewell Centre** | Cylindrical tower |
| **Times Square** | Needs its signage identity |
| **Wan Chai government slabs** | Read fine as boxes, but the grouping needs composition |

The ETL must exclude the source geometry these replace (`replaces_source_ids`) to prevent z-fighting.
**Budget:** ~3–8k triangles each — silhouette landmarks seen from a distance at speed, not hero props.

⚠️ **The reason is *not* "LOD1 extrusion flattens them", which was the original wording.** Measured,
the non-textured source is not an extrusion at all: it carries the individualised set's exact
silhouette. The lever these buildings need is texture and hand-authored detail, not a better source
dataset.

---

## Roads

- Ribbon mesh generated from road-graph polylines, vertex-coloured
- Markings via **shader along the ribbon's UV** (lane lines, yellow boxes, crossings) rather than a
  texture atlas — keeps the untextured pipeline intact. `P1-4` already ships the UVs the shader will
  read: **U is a lane coordinate**, 0 at the nearside kerb line and `lanes` at the offside, so an
  integer U is a lane boundary regardless of the playability widening — including the per-station
  widening `Q23` introduced. V is metres along the carriageway, so dashes keep a real-world pitch.
  Junction caps carry `(0, 0)`; a box junction is a mask keyed on the node, not a length of lane.
- Kerbs modelled but low and mountable — collision is forgiving by design. Built as a 0.15 m riser
  and a 0.5 m lip. The lip used to stop the carriageway ending in mid-air, back when there was no
  terrain to end against; since `P3-10` its job is the seam — the ground tucks *under* it, 0.20 m
  down, which is what hides the join.
- Tram tracks as an inset strip on flagged edges — **not yet built.** `tram_tracks` reaches the graph
  but `P1-4` draws no inset; it belongs with the markings shader, not with the ribbon.

⚠️ **When the markings shader lands it will expose a junction defect that is invisible today.** A cap
overlaps its arms rather than abutting them wherever a short edge is held back by the junction trim —
6,051 m² of 52,985 m² of cap area. Cap and carriageway are the same colour at the same height in one
material, so nothing shows; give the ribbon lane markings and the cap will read as a patch over them.

---

## Ground

**Shipped in `P3-10`.** Between the roads and under the buildings used to be skybox; it is ground now.
It landed in `B2` because the build whose verdict question is "does this read as Wan Chai?" cannot be
judged over a void.

**The source ships one, and it ships it textured** — 224 MB of JPEG across the region's six sheets
against 43 MB of geometry. The texture is the whole reason terrain was called unaffordable.

**So the texture is read at build time and never shipped.** Ground obeys the same rule as buildings:
untextured, vertex-coloured, merged into the tile's single primitive. That is not a compromise — it is
what keeps the invariant the whole pipeline rests on.

| | Predicted | **Measured** |
|---|---|---|
| Triangles, decimated at 4 m cells | 88,081 ≈ 1,355 per tile | **+87,649** at LOD0 (434,149 → 521,798), +30,695 at LOD1 |
| Texture memory | 0 | **0** — `verify_tiles.gd` still passes |
| Bundle | 1.5–2.5 MB | **+4.56 MB of PCK** (27.73 → 32.30, measured from the PCK) |
| Draw calls | +0 | **+0** — one primitive per tile, unchanged |

⚠️ **The bundle figure is nearly double the prediction, and the collider is why.** The estimate
counted geometry; the ground merges into the tier-0 mesh, so it also gets a
`ConcavePolygonShape3D`. The split between the two was not separately measured — only the total,
one variable changed. Worth knowing before predicting the next class's cost from geometry alone.

**Resident triangles went 236,882 → 280,807** at the worst streaming sample, against a mobile budget
of 300k *visible*. Those are different quantities and `verify_city_streamer.gd` refuses to gate one
on the other — but the headroom is now thin enough that `P2-6` should not be surprised by it.

⚠️ **The ground collides**, which two earlier lines of this document contradicted each other about.
It merges into the tier-0 mesh and that mesh is named `-col`, so there was never a version of
"merged for +0 draw calls" that was also "visual only, no collider". Merged and solid was the call:
a driver who leaves the road now drives on the pavement instead of falling through what they can
see. `docs/ARCHITECTURE.md` carries the mechanism.

Deleting the texture also deletes the reason terrain was awkward to decimate: clustering moves UVs and
a photographic texture smears where it does, and there are no UVs left to move.

⚠️ **The ground is flat-shaded in the fragment stage, and it has to be asked for** (`Q29`). The
source ships terrain faceted, but `mesh.collapse` averages its normals — the `height_field` path
drops the facing key, which it must, or the sheet tears — leaving 8.72° of mean normal error and a
surface that reads as plaster dunes beside a city of hard facets. Both facade shaders rebuild the
normal from screen-space derivatives where `marker` is `MARKER_GROUND`, which costs no geometry.
Anything that later draws ground through a different material has to do the same.

**Colour comes in two steps, and the first has shipped.**

1. **Flat.** One warm ground colour — `#837d72`, warm concrete. It is placed by what it has to sit
   between: clear of the kerb `#9a968d` so the 0.15 m riser still reads as an edge, and darker than
   the `#968872` shophouse band so low blocks read as standing *on* it. It and the bands share the
   same 0.520 linear scale (`docs/PROGRESS.md`, 2026-08-06) — the level moved, the relationships
   did not.
2. **Land-cover classes,** only if flat reads dead. Sample the source JPEG per source triangle, snap
   to a small palette — asphalt, pavement, vegetation, water, bare — and put the class in the cluster
   key alongside the facing. Cluster boundaries then land *on* the park and harbour edges instead of
   blending across them, which is what makes 4 m colour blobs read as deliberate low-poly ground
   rather than as mush. **Not written**, and `Q18` is what decides whether it ever is.

**Prior art says the first step can be the last one.** *Art of Rally* ships flat-shaded untextured
terrain as its finished look, not as a placeholder. Wan Chai is far denser than that game's
countryside, so it settles nothing here — but if the first pass reads dead, **suspect the palette
before the technique**.

✅ **That advice was taken and it held.** The city reading white was the palette — the five
`height_bands` 19 `L*` too light — and not the flat-shading, the rig, or the missing per-building
lightness a survey was nearly rebuilt to supply. `Q18` is still open on the technique.

**What is explicitly not done: shipping the orthophoto, resampled or otherwise.** It would cost a draw
call per tile, since a textured surface cannot merge with a vertex-coloured one. And an orthophoto has
the *real* roads baked into it at their real width, while the generated ribbon sits coplanar with the
terrain and **1.6× wider** — so photographic asphalt and photographic lane markings would show from
under a wider synthetic road, along with parked cars and baked shadows.

**The sink was guessed at 0.2 m and measured to 0.2 m.** The ground sits coplanar with the level-0
carriageway by construction, so it drops under the kerb; `tools/ground_clearance.py` sized the drop
the way `deck.clearance_m` was sized, by measuring what still stood proud of the shipped road:

| `ground_sink_m` | of carriageway area | of the points the road's height was sampled from |
|---|---|---|
| 0.00 | 47.5% | 49.9% |
| 0.10 | 9.3% | 1.8% |
| 0.15 | 5.2% | 0.97% |
| **0.20** | **3.3%** | **0.36%** |
| 0.25 | 2.2% | 0.24% |
| 0.35 | 1.2% | 0.12% |

**0.20 m is the shallowest value that passes both gates**, and deeper buys little: the second column
is the sink's own score and it is already at a third of a percent. Going deeper is not free either —
the ground hides behind a 0.15 m riser, so every extra centimetre is gap to be seen under at a
grazing angle.

⚠️ **The first column does not fall with it, because most of it is not the sink's to fix.** The road
is a *plane* and the ground is not: interpolated along its length between the 2.0% of source
vertices `simplify` kept, and flat across a width the playability widening made 1.6× too wide. On a
crest between two retained vertices the ground rises straight through a road that never sampled it —
**0.35% of centreline points proud within a metre of a vertex against 5.78% at 15–40 m from one.**
This was `P2-7`'s densification finding at grade, and `roads.ground_profile` closed the along-the-road
half of it: the area with ground proud fell **3.289% → 1.898%**, and at the centreline 2.274% →
0.712%. What is left is the across-the-road half — the ribbon is flat over a width the playability
widening made 1.6× too wide, so it cuts into a cross-slope at the kerb, and the outer rim moved only
5.393% → 4.360%. That is `Q19`'s trade, not the ground's.

---

## Vehicles

| Property | Target |
|---|---|
| Triangles | 800–2,000 |
| Materials | 1–2, flat shaded |
| Colours | 3–5 flat colours per vehicle |
| Wheels | Oversized, separate mesh, simple rotation |
| Windows | Flat dark colour with a fixed specular hint — no reflection probes |

Proportions: shortened wheelbase, tall greenhouse, exaggerated wheel arches. Readable silhouette from
behind at speed — that's the only angle most players ever see.

**Vehicle roster for the slice:** player taxi, private car (2 variants), red taxi (AI), double-decker
bus, green minibus, tram. See `PROGRESS.md` for the real models these are based on and the drivetrain
differences that make it an architecture constraint rather than an art note.

**The vehicles are generated, not modelled — `P3-11`.** `tools/make_vehicle.py` emits each `.glb`
into `game/assets/authored/vehicles/` from the numbers in this table plus named proportions
(wheelbase, track, greenhouse height, arch flare, roof taper, colour list). They are committed:
hand-authored under CC BY-SA 4.0, not build output. The reason is that everything above is a
*proportion* spec rather than a detail spec, and proportions are worth tuning in a diff rather than
guessed in a mesh. ⚠️ **The player taxi's arches must line up with the
wheel mount points in `taxi.tscn`**, which `P0-5` tuned handling against; the physics raycasts never
read the mesh, so a mismatch looks correct and drives to the old tuning.

---

## Lighting

- One directional light (sun), warm, low angle, from the shared `golden_hour.tscn` rig
- Ambient from a simple gradient sky — no HDRI, no reflection probes
- **Mobile tier:** vehicle blob shadows only, no realtime shadow maps
- **Desktop tier:** **two** directional shadow cascades at 400 m — the camera's far plane
- No global illumination, no SSAO on mobile

⚠️ **This said "one cascade" until it was measured.** One is cheaper — 55% off the frame's primitives
against 35% for two — and unusable: it has a distinct artefact at every distance, a visible shadow
cutoff mid-street at 150 m, banding on large soft shadows at 250 m, and off-screen casters dropping
out entirely at 400 m. Two gives a fine near split and a coarse far one and shows none of them.

⚠️ **"Vehicle blob shadow only" deserves re-examination before anyone builds the mobile tier.** Shots
with shadows *off* looked markedly worse than that line implies — flat and blown out, the canyon
losing its depth entirely. A real mobile tier needs the ambient and tonemap re-tuned around a blob
shadow, not the shadow switched off.

Flat shading plus a single strong key light is what makes low-poly read as intentional rather than
cheap. Resist adding lights.

**The clean/futuristic variant needs a different rig, and it is `scenes/world/clean_daylight.tscn`.**
A low warm sun is load-bearing for golden hour and actively wrong for a white city — it rakes to two
values, blown and blue, with the massing lost between them. The clean rig is a 48° sun, a pale
horizon under a deep blue top, thresholded glow, and light depth fog for aerial perspective. Both dev
scenes must name **the same** rig; splitting them is what `golden_hour.tscn`'s header warns against.

⚠️ **`ambient_light_sky_contribution` is the colour of every shadow in the city, and it is the
setting that misleads.** Dark albedo takes almost all of its light from ambient, so a saturated blue
sky paints the `#3c3a37` asphalt blue while leaving the sunlit white facades alone — the *road* looks
broken and the road's colour is not what is wrong. It is also the only thing separating one white
face from the next, so lowering it fixes the road and flattens the massing at once. Blend low toward
a **cool neutral** `ambient_light_color`: shadow colour without sky saturation. Do not reach for the
road palette in `hong_kong.yaml` for this; it is a lighting problem and costs a rebuild to get wrong.

🔴 **Everything above was tuned against a colour-space bug, and the numbers in the `.tres` files
inherit it.** Until `Q27` closed, `COLOR_0` was authored in sRGB and consumed as linear, so every
albedo in the city rendered lighter than it was asked to be — the asphalt worst of all, which is
exactly why it looked as though ambient were painting it. The rig was then tuned to compensate: the
sky contribution came down, `tonemap_white` was pushed around, and the paragraph above was written
about the symptom. With the conversion in place the asphalt is genuinely dark and the road no longer
needs ambient held back for it, so **the clean rig is now tuned against inputs that no longer exist**
and is due a pass — `Q26` owns the look, and the measured starting point is in `PROGRESS.md`.

**The general lesson, and it is the one worth keeping:** a washed-out frame is not evidence about the
lights. Grade the frame with `tools/frame_stats.py` and ask whether an *albedo change* reaches the
screen before touching a single light — a rig can only redistribute contrast that arrives, and this
project spent a sweep of ambient, exposure, glow, fog, tonemap curve and specular discovering that
none of them could put back what was lost before the light ever hit the surface.

---

## LOD policy

Generated by the ETL, not decimated at runtime.

| Tier | Distance | Content | Cell size | Wan Chai triangles |
|---|---|---|---|---|
| LOD0 | 0–250 m | Merged massing, window shader, props | 1.5 m (infrastructure 0.5 m) | 434,149 |
| LOD1 | 250–400 m | Silhouette-only merged block, flat colour | 4.0 m (infrastructure 1.0 m) | 222,375 |

Desktop tier shifts these distances outward rather than adding a new tier.

⚠️ **There is no exact-weld tier, and that is a measured decision rather than an omission.** The table
carried one at 0–150 m until `P2-1`'s review: driven side by side against a build that had none, the
user could not tell them apart, because extruded massing is big boxes and a 1.5 m cell takes half the
triangles while leaving the silhouette. Dropping it cost **30.5 MB of a 51.6 MB bundle** and **40% of
worst-case visible triangles**, both measured from real exports rather than summed from source.
Restoring it is one entry in `lod_cell_sizes_m` and a rebuild, so a later region or a desktop-only
asset split can have it back.

Tiers are produced by **vertex clustering** — merging vertices that share a grid cell *and* a facing.
Facing is in the key deliberately: cluster on position alone and a wall vertex averages with the roof
vertex above it, rounding off the hard normals this whole style rests on. Clustering also suits
extruded footprints better than quadric decimation, which smooths corners the art direction wants
kept.

⚠️ Anything **smaller** than a cell disappears entirely at that tier — intended for street furniture
at 400 m, but it means the cell sizes cannot be raised much further without losing small buildings.

⚠️ **And anything *thinner* than a cell flattens, which is a different failure and a worse-looking
one.** Clustering merges a structure's top surface into its bottom one, so a 0.8 m deck goes from 12
triangles to 2 at a 1.0 m cell while a 60 m tower is untouched at every cell the pipeline uses. That
is why cell size is **per mesh class**: `class_lod_cell_sizes_m` overrides the table above, and Hong
Kong holds `INFRASTRUCTURE` at `[0.0, 0.5, 1.0]` so flyover decks, ramps and footbridge canopies keep
their depth. A class is collapsed at its own cell and the tile is merged afterwards, so it is still
one mesh and one draw call.

⚠️ **Towers are hit harder by LOD1 than the rest, not less** — 36% of their triangles kept against 44%
for everything else. They read as fine in a canyon shot because they were distant, where a tower is
mostly silhouette. Recorded because the opposite was written down first.

---

## UI

**Visual language: Hong Kong road signage and the taxi meter.**

- Typography: condensed grotesque for English, paired with a clean Traditional Chinese face.
  **Bilingual throughout** — this is not a localisation afterthought, it is part of the art.
- Fare display styled as a **taxi meter** — LCD segments, red digits
- Direction arrow styled after HK directional road signs
- Colour: high-contrast, safe for outdoor phone use in daylight
- Safe areas respected for notches and rounded corners; **resolution-independent** because desktop is
  a target

---

## Audio direction

Not art, but it belongs to the same authenticity budget and is cheap:

- Tram bell — the single most evocative HK sound
- Minibus engine whine
- Bilingual passenger callouts (Cantonese primary)
- Ferry horn from the harbour side
- Radio stings between fares

---

## Anti-goals

- No photorealism, PBR metalness workflow, or reflection probes
- No photogrammetry textures — a trademark surface as well as an aesthetic mismatch. **Reading one at
  build time to *derive* a flat colour is not the same thing and is allowed**; what must not happen is
  a photograph reaching the bundle
- No per-building unique textures; the window shader replaces them
- No texture atlas for buildings. UVs do not survive the vertex clustering that builds both LOD tiers,
  so an atlas costs the LOD system, not just memory
- No realistic weather or wet-road reflections in the slice
- No baked lightmaps — flat shading plus one directional light is the look
