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

### The rule (`Q33`)

**Every authored colour is `material reflectance × exposure_anchor`, and `config.py` refuses to load
one that is not.** A `reflectance:` is *evidence* — a published diffuse albedo for asphalt or
concrete or soil, portable to the second city unchanged, arguable against a source rather than
against taste. The anchor is *art direction* — one number per city carrying the sun, the latitude and
the mood, and the only thing that moves when the city wants a different time of day. It is the same
evidence/direction split `facade_hue.strength` already makes.

Hong Kong ships `exposure_anchor: 0.520`, which is not chosen but measured: it is the linear scale
`235aa4f` applied to the bands, graded at frame `L*` 73.0 → 62.7, gain 0.85, responding share 66.4%.

| material | reflectance | source | shipped |
|---|---|---|---|
| `render_warm` | 48.7% | ⚠️ **back-derived, not cited** | `#968872` |
| `render_pale` | 58.4% | ⚠️ **back-derived, not cited** | `#9d9586` |
| `tile_neutral` | 61.5% | ⚠️ **back-derived, not cited** | `#9a9a90` |
| `render_cool` | 60.1% | ⚠️ **back-derived, not cited** | `#949995` |
| `panel_grey` | 55.2% | ⚠️ **back-derived, not cited** | `#8e9393` |
| `concrete_kerb` | 25.0% | weathered concrete, 20–30% | `#68655c` |
| `concrete_sooty` | 22.0% | weathered + sooty concrete | `#615f5a` |
| `concrete_paving` | 20.0% | weathered concrete, grubby end of 20–30% | `#5f5a51` |
| `asphalt_aged` | 10.0% | aged urban asphalt, 7–12% | `#42403d` |

⚠️ **The five facade materials are the soft entries and the whole rule leans on them.** They are
unchanged by the rule, so their reflectance is simply what the shipped colour claims once the anchor
is divided out — the rule is calibrated *on* them and therefore cannot also check them. They read
49–62%, at the top of what painted render and ceramic tile do. If that is wrong the anchor is wrong
with it and every other colour moves. Recorded as a number precisely so it is arguable.

⚠️ **Five names for what is really one material family** at five lightnesses. That is a real claim,
and a deliberately weaker one than a height→material mapping would make (`Q34`). Do not rename the
last of them to anything glazed — 55.2% contradicts curtain-wall glass's 8–15% diffuse albedo
sitting beside it.

### Material is not a function of height (`Q34`)

**A `materials:` table sits at the top level of the city config, and every colour the city ships is
declared there and nowhere else.** `buildings:` and `roads:` reference entries by name.

That shape is the point. **`colour` and `reflectance` must not be fields on `height_bands`**, because
that makes the *schema* assert material is a function of height — a claim nobody would write down and
the data refuses. Measured on the 2,171-building photo survey, **height explains 0.9% of facade `L*`** once
log pixel count is controlled, and 0.7% of `a*`; the best geometric key of any kind, height and
footprint together, reaches 1.4%. So "48.7% = grey painted render" read, on a height bucket, as
*"buildings under 12 m are grey painted render"*, which no source supports. It also broke hard rule
3 — a materials table is portable, a height→material mapping is not.

Hue carries the structure that height does not: **five clusters on measured hue capture 72.4%** of
hue variance. So a surveyed building draws its material from a distribution selected by its measured
chroma and hue angle, seeded from its own LandsD id; an **unsurveyed** one takes the height ramp,
which is now explicitly a *lightness ramp* and claims nothing about the stock.

⚠️ **What that buys is lightness conditioned on hue, and not more.** `with_hue` replaces `a*`/`b*`
immediately afterwards, so the drawn material's own chroma never reaches the screen. The gain is that
a building rendering cream gets an albedo plausible for cream rather than one plausible for concrete.

⚠️ **Not spatial coherence.** Neighbours draw independently and hue does not supply it either — only
0.5% of hue variance lies between the survey's six sheets. Real blocks share cladding; these do not.
That is `Q35`, opened by this shipping, and it wants grading from the *street* viewpoint rather than
the skyline — a canyon shows three façades at once where the skyline averages hundreds.

Every bin's weights are authored so its *expected* reflectance matches what the height ramp already
gave that same population, which is possible only because height and hue are near-independent.
`tools/ring_weights.py` derives them, and must be re-run whenever the ramp or the survey moves
(`Q34′`) — a bin's *share* can swing eleven points while its target moves 0.35. Graded
on the two fixed viewpoints: whole-frame `L*` moved **−0.8** (street) and **−0.1** (skyline) while
~32% of pixels moved by a mean 2.2–2.5 `L*`. The change is a redistribution, not a level change, and
that is deliberate — it is what makes it readable as one.

⚠️ **The property that guarantees this changed with `Q34`, and the new one is stronger and rests on
something narrower.** The rule was written to be enforced over the whole config, never per section,
because the two road colours were authored in `RoadSurface` while the rest of the palette was
authored in `BuildingStyle` — which is exactly how they escaped `235aa4f`, not by argument but
because `roads:` was not in the diff that changed `buildings:`. A per-section check would have passed
that commit.

There is now one section. `_check_exposure` loops over `materials:` and is total **because the table
is**, not because the loop is careful — which means it depends on something it cannot itself see:
that no colour is authored anywhere else. Two checks hold that, and neither is optional.
`_check_every_material_is_used` holds the reverse direction at load;
`test_no_colour_escapes_the_materials_table` walks the shipped document and fails the day a
`#rrggbb`-shaped value appears outside `materials:`. That test is what now carries `235aa4f`'s
lesson.

### Anchor colours

Hong Kong-specific, not generic-city:

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

🔴 **The table above is the authored palette and it is no longer the shipped one.** The five
`height_bands` honour it — `C*` 1.92 to 13.84, which is "warm off-white, beige, pale grey-green" —
but `facade_hue.strength: 2.0` multiplies each building's *measured* chroma on top, and the result
is not muted. Measured by `tools/facade_chroma.py` over the 2,177 surveyed buildings that pass
`vegetation_max`, against the band each would otherwise take:

| `facade_hue.strength` | shipped `C*` mean | median | p90 | p99 | max | share over `C*` 20 |
|---|---|---|---|---|---|---|
| 1.0 (faithful) | 7.75 | 6.13 | 15.16 | 30.23 | 75.24 | **4.6%** |
| 1.5 | 11.59 | 9.08 | 22.83 | 45.33 | 99.61 | **14.1%** |
| **2.0 (ships)** | **15.37** | **12.25** | **30.39** | **60.27** | **104.55** | **26.4%** |

`L*` mean is 61.5 at every strength, so this is chroma alone. **One building in four** is more
saturated than *any* colour this document authorises, and the tail is what the eye picks out — the
mint, teal, lilac and peach blocks in a street frame are not a rendering fault, they are the palette.

⚠️ **The knob is doing two jobs and only one of them is stated.** Its config comment calls it "the
line to move if the city reads too grey or too candy" — but at 2.0 the distribution is *both*:
median 12.25 is still near-neutral while p99 is 60.3. Amplifying chroma linearly widens the spread
far faster than it moves the middle, so the buildings that were already coloured become the loudest
thing in the frame long before the grey majority stops being grey.

**Re-run the tool whenever `strength` moves or the survey does — the two disagree about which end
moves.** `Q37`'s resurvey lifted the median 28.7% and the p99 only 5.1% — the table it replaced
carried 222 rows of atlas filler at exactly `C*` 0, and a population feels that in its middle rather
than at its edge. `strength` does the opposite, and reading one as a proxy for the other is how a
city gets tuned in the wrong direction. Whatever look wins `Q26` should set this against the palette
table, and the palette table should then be rewritten to describe the city that ships. See `Q30`.

---

## Buildings

### General fabric (≈95% of buildings)

- Source: extruded footprints, untextured
- **Vertex colour**, assigned by ETL from the building's material and class — no textures
- Flat/faceted shading, hard normals
- Subtle per-building colour jitter so blocks don't read as uniform

**The palette lives in `etl/config/cities/hong_kong.yaml` under the top-level `materials:` table**,
not in code, and `buildings:` says which building gets which — a measured-hue draw where the survey
has a row, and otherwise a five-step lightness ramp running warm beige for the low stock up to cool
pale grey for commercial towers. `INFRASTRUCTURE` and the ground take flat materials that override
both. Change it there; change *why* here first. The jitter is seeded from each building's LandsD id,
so it is stable across rebuilds — and the material draw is seeded from the *same* id through a
separate `blake2b` stream, deliberately uncorrelated with it.

⚠️ **The jitter means a class is a *ray* through its base colour, not a value.** Any tool matching a
class by colour must test the scale factor, not equality — `tools/deck_error.py` matched 428 of
434,149 triangles before this was understood.

⚠️ **"Untextured extruded footprints" undersells the source, and with the shader grid off that shows
as an inconsistency rather than as a bonus.** A minority of towers arrive carrying **real recessed
window reveals and structural fins in the geometry** — visible in the skyline crop under
`build/driver/art_crops/`, where one slab carries a dotted grid of genuine openings and its
neighbour continuous piers. So the
city currently draws surface three ways at once: flat colour on most buildings, geometric relief on
a few, and neither on the same few once LOD1 clusters at 4 m and swallows the reveal. ⚠️ **And the
relief does not survive the distance it is seen at** — sub-pixel openings alias into a speckle that
reads as dirt on the wall, not as fenestration. This is the same aliasing argument `P3-7`'s
`band()` answered analytically for the *shader* grid; geometry has no such recourse, so the honest
options are to accept it, or to make the shader grid's return cover these buildings too rather than
compete with them. It is evidence for `Q26` and was not on the table when `Q26` was written.

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

⚠️ **`TEXCOORD_0.x` is metres above the building's base, never normalised `0-1`, and the difference
is load-bearing.** Normalised, a vertex says what fraction of its own building it is up, and the shader
cannot recover the building's height from that — so a 3-storey shophouse and a 40-storey tower get
the *same number of window rows*. The floor count is the signature. In metres the row spacing is a
constant of the city rather than of the object, and the podium mask becomes an absolute height.

**The storey height is measured, not chosen: 2.8 m.** 227 walls on 219 buildings of one
individualised (textured) LandsD sheet, read offline and discarded — height-weighted median 2.77 m,
and Hong Kong's domestic floor-to-floor really is that tight. A guessed 3.2 would have put a storey
too few on every tower. Column pitch is measured the same way at 2.4 m. `docs/DATA_SOURCES.md`
records that the sheet does not enter the build path; `docs/DECISIONS.md` carries the distribution.

⚠️ **Two of those inputs have to come from the ETL, and they are why `P3-7` is one commit across both
sides.** A vertex knows its world Y, not where its building starts — a podium vertex and a 30th-floor
vertex are indistinguishable to the shader — and it has no seed at all, so neighbouring towers would
share a window pattern. Buildings shipped **no UVs** when this was written, so `TEXCOORD_0` was free
(shipped float32 rather than the "2 bytes quantised" predicted here — `ARCHITECTURE.md` has the
measured cost), and it survives vertex clustering through the same representative-selection path that
already carries colours. **`TEXCOORD_1` is spent now too** (schema 6): the `Q40`/`Q41` survey
verdicts ride it as one packed per-building state code, with the second float reserved for `Q42`'s
riders — the channel table in `ARCHITECTURE.md` is the contract.

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

⚠️ **This variant's elements are OFF in the shipped build: `city_facade.tres` carries candidate
`C`** — accurate massing, flat per-building colour, no fabric and no surveyed verdicts. User's
call, 2026-08-16, to continue development on flat colour. `A‴` — the seven fabric values, the
surveyed verdicts at `survey_apply = 1.0`, and `P3-7a`'s two corrections (punched openings are
glass, `Q44`; panes vary per building, `Q45`) — shipped from 2026-08-09 to that date and now lives
in **`city_facade_elements.tres`**, one `cp` away.

**All three of `Q26`'s looks are files now** — `city_facade.tres` is `C`, `city_facade_elements.tres`
is `A‴`, `city_facade_warm.tres` is `B` — which discharges the reproducibility lesson `Q26` paid for
when candidate `A` turned out to be unreproducible as written.

⚠️ **Nothing was faulted in `A‴`, and this is not `Q26`'s final word.** Both enables were the
user's own verdict on the fixed render; the `≥3`-HK-driver recognition round (`P3-9a`) still grades
whatever ships, on the web build. `C` is also the reducibility baseline the remaining `P3-7a` steps
are proved byte-identical against, so the default and the baseline are now the same configuration —
✅ verified on the swap, both audit cameras byte-identical to the graded `C` frames.

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

⚠️ **And its sibling: an opening is not necessarily glass** (`Q43`). Whether a wall has openings and
what those openings are made of are two questions, and one switch answering both is what deleted the
windows on 66% of the city's wall vertices — every surveyed `punched` building, which is the dominant
real Hennessy Road stock. Where the survey says glazing does not **dominate**, the openings are dark
reveals in solid wall rather than a mirrored skin: `recess_colour` is what they are made of and
`unglazed_reflect` is the share of the reflection they keep. ⚠️ **Not zero** — a tenement window is
dark glass in a concrete hole and does catch the sky; at zero the openings read as dark rectangles
painted on. That split is what lets building *types* differ in material and not merely in window
spacing, and it takes chroma back off the frame for free, because a matte reveal carries no sky.

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

- **No per-building texture, and no low-res atlas.** ⚠️ **The binding reason is `merge`, not UVs.**
  `merge` refuses textured meshes, so a textured building becomes its own draw call and 53 becomes
  thousands. "UVs do not survive vertex clustering" is true — `collapse` takes them from a cluster
  representative — but it is the weaker half, because the buildings this pipeline ships **have no UVs
  to lose**: the non-textured set carries `COLOR_0` in one primitive with **zero images**
  (`DATA_SOURCES.md`). ⚠️ **An unclustered LOD0 does not rescue it**, which is the obvious next idea:
  `collapse`'s `cell_m <= 0` welds on position *and normal*, which is exactly what the two sides of a
  UV seam share, so even the lossless tier is lossless only for geometry — and restoring that tier
  costs 30.5 MB and 40% of worst-case visible triangles (`Q16`).
- 🚚 **Colour sampled per building is not on this list — buildings get it.** All three original
  objections fell to measurement; see "Per-building façade colour" below. What remains of the
  objection is narrower and still binding: **the photographs' `L*` is not usable and is not used.**
- ⚠️ **Do not re-author the five height bands from clustered façade colour.** It is measured and
  close to pointless: height explains **1.2% of `a*` and 0.8% of `b*`** across all 2,214 buildings,
  so re-authoring the bands while keeping height as the key moves the fit barely at all. **Height is
  not the signal.** The ramp is a *lightness* ramp, old-and-darker below to pale-above, which is the
  one thing height does predict (10.9%).

### Per-building façade colour

Every building carries its **own measured hue**, read offline from the individualised set's photo
textures and joined to the massing by the building id's stem. 2,214 buildings, 100% matched, and it
costs the runtime nothing: it lands in the `COLOR_0` the tiles already shipped, so there is no new
attribute, no schema change, no shader change and no interaction with the LOD clustering. Where an
atlas is unreadable a building falls back to its height band — and so does its *material*, which is
the same contract stated once (`Q34`). `etl/config/cities/hong_kong.yaml` holds the switch;
`etl/pipeline/colour.py` holds the conversion and the reasoning.

⚠️ **Hue is taken and lightness is refused, and that is a measurement rather than a preference.**
Across the survey, the `L*` spread *within* one building — its four walls, same cladding, differing
only in which way they faced the sun — is **22.9 on average and 41.1 at p90**, against a
between-building spread of **16.25**. The confound is larger than the signal. Hue survives because
illumination moves value far more than it moves hue, so `a*`/`b*` are evidence and `L*` is a record
of the flight. Shipping it as albedo would bake that flight's shadows into the city for the engine's
sun to shade a second time. `facade_hue.strength` scales the measured chroma and is the *stylisation*
knob, kept separate so the two cannot be confused.

✅ **`COLOR_0` is authored in sRGB and every consumer must linearise it** — the two façade shaders and
the road's `BaseMaterial3D`. Consumed as linear it puts **57%** of a lit façade pixel's luminance
into an albedo-*independent* term, so a per-building difference reaches the screen at a third of its
size and the city reads pale. Converted, the share falls to **6%** at street level. `Q27`.

⚠️ **A washed-out frame is not evidence about the lights.** "The rig's light levels swamp albedo" is
the diagnosis to resist here, and it is wrong: ambient, exposure, glow, fog, the tonemap curve and
specular were each ablated and **none moved albedo transmission by more than 0.05**. Grade a pair of
renders with `tools/frame_stats.py` and ask whether an *albedo change* survives to the screen before
touching anything — a rig can only redistribute contrast that arrives.

### Hero buildings (~5)

Distinctive silhouettes need hand-authored low-poly models, placed via `landmarks.json`:

| Building | Why it needs authoring | Status |
|---|---|---|
| **HK Convention & Exhibition Centre** | The curved "flying wing" roof | ✅ `P3-6` amendment — **the source mesh itself**, repainted: after three generator rounds converged on the source by measurement, the hero is now the building's own 41,273-triangle mesh, extracted by `pipeline/landmarks.py`, sliced at the photo-measured ribbon elevations (15 m + k·4.8 m, 1.5 m strips) and vertex-repainted pale-panels/dark-ribbons under a darker `roof_grey` (99,577 triangles shipped, generated output, never committed — `LICENSING.md`). Roof and soffit are crease-grown so the sweeps stay grey to their rolled edges, and each ribbon strip is kept only where the building's own aerial texture (the individualised `A0` atlas, consulted at build time and discarded) confirms glazing — bands follow the real elevation, not the band grid; Phase 2 only — Phase 1 and its four towers stay generated |
| **Central Plaza** | Pyramid crown | ✅ `P3-6` — banded triangular shaft, arcade piers, pyramid, two-stage mast |
| **Hopewell Centre** | Cylindrical tower | ⬜ |
| **Times Square** | Needs its signage identity — **massing and placement only, never rendered text** (`Q42`, hard rule 8) | ⬜ |
| **Wan Chai government slabs** | Read fine as boxes, but the grouping needs composition | ⬜ |

The ETL must exclude the source geometry these replace (`replaces_source_ids`) to prevent z-fighting.
**Budget:** ~3–8k triangles for an *authored* hero — silhouette landmarks seen from a distance at
speed, not hero props — generated by `tools/make_landmark.py` from surveyed dimensions, chamfered
geometry, never smoothed (`P3-11`). A *mesh-sourced* hero carries its own measured ceiling instead,
pinned as `triangle_budget` in the city config and enforced per entry by the stage and by
`verify_landmarks.gd` (HKCEC: 99,577 measured against a 120k pin). The two budgets are different
claims: the authored number is a design target, the mesh-sourced number is a regression tripwire.

⚠️ **The first two heroes ship vertex-coloured, and "light texturing" is deferred, not decided
against** (user call, 2026-08-12 — the `P3-6` record has the argument). The anti-goals ban building
textures because `merge` cannot carry them; heroes bypass `merge`, so a texture is *structurally*
possible here and nowhere else — but introducing the bundle's first texture is its own decision
with its own `DECISIONS.md` record, and the detail these two needed (the wing, the crown) carried
the silhouette without it. Hero colours obey the palette rule like everything else: each is
`reflectance x exposure_anchor` (`Q33`/`Q38`) — the mesh-sourced paint by naming entries in the
city's `materials:` table (checked at config load), the authored palette self-checked by the
generator against the live anchor.

⚠️ **The reason is *not* "LOD1 extrusion flattens them", which was the original wording.** Measured,
the non-textured source is not an extrusion at all: it carries the individualised set's exact
silhouette. The lever these buildings need is hand-authored detail (and possibly texture, above),
not a better source dataset. **HKCEC then proved the corollary** (`P3-6` amendment): where the
identity *is* the massing rather than an authored feature, the source mesh needs no lever at all —
three generator rounds measured the source's own shape back into the model before the user called
it, and the "detail" the treatment actually added was paint, which the repaint stage now applies to
the source directly. Central Plaza is the counter-case and stays generated: its crown and mast are
authored features the source captures badly.

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
  and a 0.5 m lip. **The lip's job is the seam:** the ground tucks *under* it, 0.20 m down, which is
  what hides the join. (Before `P3-10` there was no terrain to end against and it stopped the
  carriageway ending in mid-air.)
- Tram tracks as an inset strip on flagged edges — **not yet built.** `tram_tracks` reaches the graph
  but `P1-4` draws no inset; it belongs with the markings shader, not with the ribbon.

⚠️ **When the markings shader lands it will expose a junction defect that is invisible today.** A cap
overlaps its arms rather than abutting them wherever a short edge is held back by the junction trim —
6,051 m² of 52,985 m² of cap area. Cap and carriageway are the same colour at the same height in one
material, so nothing shows; give the ribbon lane markings and the cap will read as a patch over them.

🔴 **The asphalt is not the outlier — it is the one colour that was already right.** Judged against
its neighbours it looks like a hole in the city's value range: every other albedo sits inside 15 `L*`
points — kerb 62.2, band stock 57.4–63.3, ground 52.5, infrastructure 48.1 — while `surface_colour`
was `L*` **24.5**. Judged against published albedo it was claiming **8.2%** reflectance, dead centre
of aged asphalt's real 7–12%. The palette rule moved it 2.7 `L*` and moved the *kerb* 19.4.

⚠️ **The mechanism is worth more than the error, and it is why the rule below exists.** A palette
judged only on internal consistency always indicts its most extreme member — the question "do these
look consistent with each other" has no way to return "the outlier is the only correct one". It takes
an external referent to see it. `Q33`.

**The measurement underneath stands:** of the two frames below, `kerb` really is bimodal with an empty
middle, and the palette rule did not close it. ⚠️ The band shares are now `tools/frame_stats.py`'s,
not an ad-hoc script's. Three of the four cells reproduce exactly; `street`'s 10–30 was recorded as
25.1% and reproduces at **25.4%** on a byte-identical frame, so that one was always slightly wrong.

| Frame | pixels under `L*` 10 | `L*` 10–30 | shipped before → after |
|---|---|---|---|
| `kerb` — Causeway Bay, road in shade | **51.4% → 51.3%** | 0.5% → 2.7% | barely moved |
| `street` — Hennessy Road canyon | 13.2% → 13.0% | 27.0% → 25.4% | barely moved |

🔴 **That is positive evidence about the lighting rig rather than an open question about the road.**
The road albedo has been corrected against a material and the hole stayed. ⚠️ **But the rig term is
`adjustment_contrast`, not the fill** — 1.14 → 1.00 takes `kerb` from 51.3% to **0.9%**, because
Godot's contrast adjustment pivots about mid-grey and the 10–30 band is what it evacuates downward.
The fill sits *upstream* of that curve and is re-crushed by it, which is why every earlier lever
measured as inert. `Q31`.

✅ **The empty middle is a *lit-versus-unlit* gap, not a dark-albedo gap**, and the two failing frames
really are the two shot in shade — `kerb`, and `taxi` at t01.20, which reproduces its recorded 28.9%
exactly. The same `taxi` camera grades clean at t04.50 in sun. ⚠️ But *under a deck* is not the
predictor: `infra`, shot from directly beneath the Canal Road flyover, has the **fullest** middle of
every audit frame at 39.6%.

🔴 **Do not treat the band share as the acceptance test.** Half the `kerb` frame is the shaded road at
one near-constant value: dropping the contrast moves that mass from `L*` 4.91 to 10.99 while its
internal spread goes only 0.79 → 0.85 sd. The statistic reads as fixed because a flat surface crossed
a threshold, not because anything gained information. Grade **variation within the shadow mass**.
Neither contrast nor a uniform fill can supply it — both are monotone per-pixel functions and the
surface is a constant — which is what makes the sky-visibility term structural rather than optional.
The ablation discipline in the Lighting section applies; one lever at a time.

---

## Infrastructure

Flyovers, ramps, footbridge canopies
and podium decks are a whole mesh class — `INFRASTRUCTURE` — with its own colour, its own LOD cell
sizes and its own grader, and until now the only art direction attached to it was one line in the
city config. ⚠️ **It is a smaller share of the frame than its silhouette suggests** — 2.71% even from
beneath the Canal Road flyover, measured below — so this section is a reference rather than a list
of work.

- One flat colour, `#615f5a` — `L*` 40.4, `C*` 3.15, declaring 22% albedo for weathered sooty
  concrete under the palette rule — for **deck, soffit, pier, parapet and
  footbridge alike**, overriding the height bands because a flyover is concrete whatever its height
- Cell sizes held at `[0.0, 0.5, 1.0]` so a thin deck keeps its depth (see LOD policy)

✅ **The class really does take none of the shader's surface treatment, and that part was read from
the code rather than guessed.** `roof_darkness`, the grounding gradient and the jitter are all
applied inside `if (is_facade)` at `city_facade_clean.gdshader:437`, and `is_facade` is
`marker < MARKER_FACADE + 0.5`. `MARKER_STRUCTURE` is `2.0`, so a flyover arrives as raw `#615f5a`
and is lit, full stop.

🔴 **Infrastructure is not the brightest large object in its frame, and its soffit does not sit at
the value of its deck top.** Both are tempting readings of a flyover shot and both are refuted by a
probe that tints `MARKER_STRUCTURE` red and its down-faces green. Measured on
`build/driver/art_infra`, the viewpoint chosen to showcase this class:

| | |
|---|---|
| `INFRASTRUCTURE` share of the frame | **2.71%** |
| …of which faces downward | **15.6%** (0.42% of frame) |
| Structure up/side faces | `L*` **51.1** against a non-sky frame mean of **48.1** |
| Structure soffits | `L*` **35.9** — already 15 points below its own up-faces |

⚠️ **The pale beams filling that frame are `BUILDING`, not `INFRASTRUCTURE`** — they did not tint.
Naming the class from the silhouette was the whole error, and the flyover was never the bright thing.

⚠️ **The reasoning error is worth more than the finding, because it will recur.** "No ambient
occlusion, therefore a soffit renders like a deck top" confuses **AO with `N·L`**. Under a single
directional light a downward face takes *no direct sun at all* — the renderer was already doing the
physically right thing, and the 15 `L*` gap is that term working. AO would have deepened the corner
where soffit meets pier; it was never what separates a soffit from a deck.

⚠️ **Do not add a `structure_soffit_darkness` term.** One was built, measured and reverted: it worked
exactly as designed — flyover soffits `L*` 36.3 → 25.8, whole-frame mean moving 0.05, every other
viewpoint unchanged but for its own soffits — and a correct implementation of a wrong premise is
still cruft. `Q32`, and 0.42% of one frame is the number that closed it.

⚠️ **What survives, and it is small: the class has no art direction of its own, and one flat colour
for deck, soffit, pier and parapet means a viaduct's massing is legible only where the sun catches a
face.** That is a real observation and it is not urgent, because the class is 2.71% of the frame that
was picked to flatter it. Anyone reopening it should start by measuring the share again from
wherever they think it looks wrong — and should not reach for a darker `#615f5a` by eye, which moves
the sunlit deck top by exactly as much and now also needs a material to justify it (`Q33`).

---

## Ground

**Shipped in `P3-10`.** Between the roads and under the buildings is ground, and it is solid. It
landed in `B2` because the build whose verdict question is "does this read as Wan Chai?" cannot be
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

⚠️ **The ground collides, and "merged for +0 draw calls" and "visual only, no collider" were never
compatible.** It merges into the tier-0 mesh and that mesh is named `-col`, so anything merged into
it is solid. Merged and solid was the call:
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

1. **Flat.** One ground colour — `concrete_paving` `#5f5a51`, declaring 20% albedo for weathered
   concrete at the grubby end of 20–30%. It was `#887c66` and placed by eye against its neighbours:
   clear of the kerb so the 0.15 m riser still reads as an edge, and darker than the shophouse band
   so low blocks read as standing *on* it. The palette rule (`Q33`) re-placed it against a material
   instead and it fell 13.9 `L*` — the old value was claiming 39.6% reflectance, which is not soil,
   it is plaster. ⚠️ **Then `Q36` found the material itself was wrong:** the surface here is paving,
   plaza and apron, not the fill under it, and the carriageway is drawn separately from `roads.glb`.
   Reflectance did not move, so this was chroma only — authored `C*` 13.6 → 5.9, rendered 6.71 →
   3.53. ⚠️ **`Q18`'s doubled chroma is superseded, and do not restore it without reading `Q36`:**
   it was compensating for a lightness problem `Q33` later fixed, and the two were never re-graded.
   ⚠️ **Do not "simplify" this to a neutral grey either** — rendered chroma is roughly \|warm albedo
   − blue illuminant\|, so authored `C*` 4.47 renders *bluer* (5.04) than authored 5.93 does (3.53).
   A little authored warmth is what cancels the sky.
2. ~~**Land-cover classes,** only if flat reads dead.~~ ❌ **Refused, and it will not be written.**
   Flat did read dead, twice — but the causes were `Q29`'s smooth shading and then the ground's
   chroma sitting under a **knee** the authored hue has to clear. Both are fixed, one in the
   shader and one in a config line. **What kills the classifier is a resolution mismatch**, and no
   tuning reaches it: the source is ~10 px/m where the ground clusters at 4 m. Its "water" class is
   not water but shadow and sky-cast — **51.1% of it sits on rooftops** — and its vegetation class
   resolves at the shipped 4 m cell into **one-cell fringes tracing building footprints**, only 5.5%
   of cells above half vegetation. It would halo every building in Wan Chai rather than draw a park.
   **If parks are wanted, the source is vector land-use polygons, not the photograph** — crisp edges
   at any cell size, and a clean key for `collapse`. See `Q18`. ⚠️ **`Q36` reached the
   same destination from the other direction** and the detour is worth knowing about: a *geometric*
   split of the hillside, on elevation or on slope, was specified and then refused on a tint probe.
   High terrain draws **0.000% of all six viewpoints above**, and the one road that climbs it looks
   out over ground that is 97.5% flat — paved terrace, not slope. There is no cheap geometric key
   here, because in this region the high ground the player can reach is the ground that was built on.

⚠️ **The ground is solved as a surface and unsolved as a *place*, and that is a content problem
rather than a palette one.** In `build/driver/art_ground` the reclamation south of HKCEC is an
unbroken expanse of one colour running to the region edge — correctly faceted (`Q29`), correctly
materialled (`Q36`), and carrying **nothing**: no pavement/carriageway distinction off the ribbon, no
planting, no street furniture, no contact darkening where a footbridge pier or a building meets it.
**A *correct* flat colour over 200 m with no incident on it converges on beach whatever its hue.**

⚠️ **The colour levers have all been pulled and none of them is the answer.** Chroma bought concrete
over plaster (`Q18`); the palette rule dropped the ground 13.9 `L*` and moved the frame's share above
`L*` 55 from 67.5% to 52.4% (`Q33`); naming the material paving rather than soil took the warm share
of this frame from 29.3% to 2.0% (`Q36`). Each was right and none of them fills an empty plane.

⚠️ **This is not an argument for the land-cover classifier, which is refused on resolution and stays
refused** — a classifier would put a green fringe round every building, which is incident of exactly
the wrong kind. The lever is what stands *on* the ground, and it is `B3`'s (`P3-3`, `P3-4`, `P3-8`)
rather than the terrain's.

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
| Materials | 1–2, flat shaded — the body's is a `ShaderMaterial` since `P3-11c`, still one |
| Colours | 3–5 flat colours per vehicle |
| Wheels | Oversized, separate mesh, simple rotation |
| Windows | Flat dark colour with a fixed specular hint — no reflection probes |

⚠️ **"Flat shaded" now means flat *albedo*, not flat shading, and `P3-11c` is where that changed.**
The body carries a surface marker in `UV.y`, and `vehicle_body.gdshader` gives glazing, lamp lenses
and paint a clearcoat over a three-band sky gradient — zenith, horizon and dark ground, chosen by the
reflected ray's own elevation. Every colour on the car is still one flat authored value; what varies
is what the surface *reflects*, which is why this does not reopen textures or per-vertex shading.

⚠️ **Strength was never the variable, and two tunings had to be judged wrong before that was clear.**
A single flat reflection colour is a swatch at every value — faint when weak, painted-on when strong —
which is the identical failure this document records against the facades. With the gradient in, the
glazing's `L*` spread went **sd 0.05 → 6.35**. On a car it responds to **roll and pitch** — cornering lean,
squat, dive — and *not* to steering, because the band is chosen by the reflected ray's `y` and yaw
leaves `y` untouched. Measured on a skidpad circle, the glazing moves `L*` 23.85 → 27.87 across
headings. ⚠️ An earlier draft of this paragraph claimed turning swept the gradient; it does not.

⚠️ **The one thing that responds to steering is the sun glint**, because the sky gradient cannot:
it is rotationally symmetric about the vertical, so no heading change reaches it. A sun term is
asymmetric about that axis and does. ⚠️ On flat-shaded geometry it is **per-facet** — a pane shares
one normal, so the screen flashes whole as the car turns rather than a highlight sliding across it,
which is a property to tune rather than a defect. Its direction is read from the scene's real
`DirectionalLight3D` and never authored twice.

⚠️ **Gloss on paint is priced, not refused, and the price is linear.** `paint_reflect 0.12` at the
stock roughness costs the red `C*` **−5.42**; adding `roughness 0.9 → 0.55` costs **−9.20** in total
at `fresnel_power` 4.0. The shipped car pays **−7.43** of that, because tightening the fresnel to 6.5
refunds `C*` +1.77 for −0.06 `L*` of glazing. At `C*` 71.63 it is still **9× the frame median** and
clear of the city's 99th percentile — the "only chromatic object" property survives the whole cost.

⚠️ **Fresnel is what makes any of this affordable, and it is easy to mistake for decoration.**
Ablated — the reflection landing at every angle instead of grazing ones — the paint loses a *further*
`C*` **13.75**. It is the term keeping the clearcoat off a panel facing the camera; there is no
priced trade without it, only a wash.
⚠️ The residual risk is **recognition**, not art: red is an identifying feature of 紅的 and `P3-9a`
grades exactly that, so this dial is the first thing to back off if the gate scores poorly. See
`DECISIONS.md` `P3-11c`.

Proportions: shortened wheelbase, tall greenhouse, exaggerated wheel arches. Readable silhouette from
behind at speed — that's the only angle most players ever see.

**The screens are raked by angle, not by taper — 35° front, 30° rear.** Both already sloped before
anyone looked: the roof tapers placed the roof edge and the top of the glass was a bare `* 0.8` of
them, which came out at 32.3° and **18.6°**. The front was near enough; the rear read as a vertical
wall from behind, which the line above makes the angle that decides it. Rake is paid for out of roof
length, so the cabin's rear moved back to the axle to buy it. The windscreen and the cant rail above
it are **one plane** — the silver is where the paint changes, not where the bodywork turns — so one
angle places both, and `roof_*_taper_m` is derived from it.

**The lower body breaks once, all the way round, at `bumper_bottom_y_m`.** Below that line it is red
across the nose and tail — the valance under the bumper — and dark along the flank, which is the
rocker. That is a bumper meeting a sill panel, as the real car has. ⚠️ **The rocker is the third dark
strip tried on this flank**; a box standing proud read as a stick and a continued bumper band read as
a stripe painted on a toy, both recorded in `DECISIONS.md`. It is on trial: at 60 mm it falls inside
the range `P3-11`'s review measured as sub-pixel at review distance, and the chase
camera tracks the car's facing so it never shows the flank at all. `rocker_top_y_m = sill_y_m`
removes it.

✅ **Audited in situ and the split works — the taxi is the only chromatic object in the frame and it
reads instantly.** On `build/driver/art_taxi` t04.50 the red bodywork is **`C*` 86.5** against a
frame median of **7.5**, on 0.5% of pixels, with the whole rest of the city's 99th percentile at
39.8. "Stylise the actors, not the stage" is not a metaphor here; it is an order-of-magnitude chroma
gap and the car pops out of any frame it is in.

⚠️ **Two things the same shot says are wrong, and both are small.** The **silver roof renders
ice-blue**, because `SILVER` is a near-neutral and a near-neutral takes its hue from ambient — the
identical mechanism this document flags for the asphalt under Lighting, arriving on the one part of
the car that is supposed to read as metal. And the **red lens of the tail cluster is still
invisible** exactly as `P3-11b` predicted, so the cluster reads amber-over-white with a bump where
the red should be. Neither is worth a round on its own; both are worth fixing in the next one.

✅ **The roof is fixed, and the diagnosis above was only half right** (`P3-11c`). A near-neutral does
take its hue from ambient — but measured, `SILVER` was *itself* authored blue at `b* -3.56`, so no
lighting change could ever have reached it. `(168,172,178) → (175,171,166)` moves `b*` to `+3.07`
and holds `L*` at 70.17, and the rendered trim drops from `C*` 10.00 to 6.24 in sun. Fixed at the
colour and not in the shader, because `SILVER` is also the wheel hubs and those are on the tyre mesh,
which gets no shader.

🔴 **The tail lens is still not fixed, and `P3-11c` did not fix it.** It is marked as a lens and
takes the lens roughness, which separates it only where light falls on it — at both audit cameras the
rear face takes none, and lamp pixels moved `L*` +0.77 in shade and +0.41 in sun. **Both obvious
fixes are closed**: recolouring the lens is the earlier bug and a white tail lamp besides, and the
bezel that bought the contrast was removed on request with the trade understood. Faking that bezel in
the shader is the same reversal wearing a different hat. This wants a decision, not more tuning.

⚠️ **The palette is at seven and the table above says 3–5.** Red, silver, black glazing, amber,
white plate, yellow plate and badge green. Each was granted for a stated reason and the count is
recorded rather than enforced — but it is now the standing exception, not a one-off, and the table
should either move or start being applied.

**Vehicle roster for the slice:** player taxi, private car (2 variants), red taxi (AI), double-decker
bus, green minibus, tram.

**The player-side roster is real models, not generic cars**, because the **drive layout differs
across them** — which makes it an architecture constraint rather than an art note. See
`ARCHITECTURE.md` for how the layout is expressed.

| Vehicle | Drivetrain | Notes |
|---|---|---|
| Old Toyota Crown (Comfort) | LPG, **rear-wheel drive** | The iconic HK red taxi |
| New Toyota Crown | Hybrid, **front-wheel drive** | |
| Toyota Hiace | CVT | Van proportions — tall, high centre of mass |

⚠️ **Transmission character is not modelled.** `engine_force` is a flat constant with no gears or
torque curve, so an LPG Crown, a hybrid and a CVT accelerate identically. Flag it before the roster
work in Phase 5.

**The vehicles are generated, not modelled — `P3-11`.** `tools/make_vehicle.py` emits each `.glb`
into `game/assets/authored/vehicles/` from the numbers in this table plus named proportions
(wheelbase, track, greenhouse height, arch flare, **screen rake**, colour list). They are committed:
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

⚠️ **Two cascades, not one, and the difference is measured.** One is cheaper — 55% off the frame's
primitives against 35% for two — and unusable: it has a distinct artefact at every distance, a
visible shadow cutoff mid-street at 150 m, banding on large soft shadows at 250 m, and off-screen
casters dropping out entirely at 400 m. Two gives a fine near split and a coarse far one and shows
none of them.

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
sky paints the `#42403d` asphalt blue while leaving the sunlit white facades alone — the *road* looks
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
and is due a pass — `Q26` owns the look, and the measured starting point is in `Q27`.

⚠️ **The rig's pass is now overdue and the audit says what to grade it on: the shadow value, not the
key.** Post-`Q27` the frames that fail are the two shot in shade — 51.4% and 28.9% of their pixels
under `L*` 10, with almost nothing between 10 and 30 — while every sunlit frame grades clean and
clips nowhere. Shadow is where the whole city converges: in `build/driver/art_taxi` t01.20 the
soffit, the walls and the pavement under the HKCEC deck are one narrow blue-grey band and the
massing is simply gone. ⚠️ **The correction is *not* the fill, and that was measured rather than
argued.** `adjustment_contrast` — never in `Q27`'s ablation list — is the dominant term: 1.14 → 1.00
takes `kerb` from 51.3% to 0.9% and `taxi` t01.20 from 28.9% to 0.8%, while a 65% lift of
`ambient_light_energy` leaves the shadow mass *still under `L*` 10* and costs more massing flatness
than the contrast change does. The fill is upstream of the tone curve and is re-crushed by it. Change
one at a time and grade with `tools/frame_stats.py`; `Q31` owns the pair.

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

## The audit viewpoints

**Seven cameras, fixed, so a look change is judged against the last change rather than against a
fresh camera.** `Q27` established that two viewpoints can disagree sharply about whether the city
reads white and that the disagreement is itself the finding, so the set covers every mesh class the
pipeline ships rather than the two that raised the question. All run through
`.claude/skills/run-hk-taxi-q/drive.sh` and all are deterministic to the centimetre.

| Name | Scene | Camera → look | What it is the evidence for |
|---|---|---|---|
| `street` | preview | `270,5.5,691` → `30,4.5,719` | Hennessy Road canyon. Façade colour at eye level, the shipping viewpoint |
| `skyline` | preview | `520,130,180` → `520,45,640` | Massing and silhouette over the harbour. Where "the city reads white" was judged |
| `kerb` | preview | `283,6,684` → `300,3.2,700` | Causeway Bay in shade. The value gap, and the chroma tail at its loudest |
| `ground` | preview | `400,45,300` → `250,0,60` | The waterfront reclamation. Terrain as an expanse, and the region edge |
| `infra` | preview | `1010,9,890` → `930,13,800` | Canal Road flyover from beneath. Deck, soffit, pier |
| `taxi` | drive | `--seconds=6 --shots=1.2,4.5 --hold=accelerate@0.3+4` | The car in shade at 1.2 s and in sun at 4.5 s |
| `aerial` | preview | `850,620,1750` → `850,10,400` | The whole region. Chiefly a fog check — at this range fog erases most of it |

⚠️ **Use `--debug-view=off` on every one of them.** The overlay's opaque text block is several per
cent of the frame and lands in any statistic taken from the PNG.

⚠️ **Preview shots carry `road_preview.gd`'s overlay whatever the debug flag says** — coloured
polylines and 1,125 direction arrows, drawn by the scene rather than by the debug view. Thin blue
lines lying on the ground in `art_infra` are that, not art. `city_drive.tscn` puts the same overlay
behind `--debug-view`, which is why the `taxi` rows are clean.

⚠️ **A run can stall the renderer, and it is intermittent — retry before believing it.** `Q43`'s
re-shoot lost 3 of 5 attempts at one viewpoint to `no frame drawn in 600 ticks — the renderer
stopped`, while the identical command at the same camera passed on the others. It fails **loudly**
(the driver exits 1 and writes no frame), so nothing silently enters the set; it just costs runs.
Retry the viewpoint rather than concluding anything about the look, and note that the frames are
compared byte for byte afterwards, so a retried run is not a weaker one.

⚠️ **A verdict pending on a screenshot has an expiry date that nothing in the repo records.** `Q29`
lost a day to shots taken one palette commit before they were read. Re-shoot before comparing, and
say which commit a shot is of.

⚠️ **A preview frame can be shot from the wrong camera with nothing anywhere reporting it.** The run
window steals focus, and a click on it puts `free_look_camera.gd` into captured-mouse mode, after
which any mouse movement rotates the audit camera. **Position survives and only the aim moves**, so
the result is a plausible-looking frame of the wrong thing rather than an obvious failure. The run
exits `DRIVER OK` and the `camera:` log line reports the requested transform either way. Two of
eighteen frames were ruined this way while measuring `Q26`'s tone-curve stability, and only a
byte-comparison against an archived shot caught them. **Leave the machine alone for the length of a
shoot, and shoot each viewpoint twice and `cmp`.** See `Q26`.

✅ **These viewpoints are static by `t=0.8`** — `t=0.8`, `t=1.5` and `t=3.0` are byte-identical, so
the longer runs earlier shots used bought nothing, and an early capture is less likely to hit the
renderer stall that comes with an obscured window.

---

## Anti-goals

⚠️ **These are anti-goals, not hard rules.** CLAUDE.md's eight numbered rules are settled; this list
is art direction and is revisable with evidence. **Each entry's stated reason is load-bearing** — a
wrong reason changes what would become possible if the entry were ever lifted, so the reasons below
are the part to read before proposing anything against this list.

- No photorealism, PBR metalness workflow, or reflection probes
- No photogrammetry textures in the bundle. **Reading one at build time to *derive* a flat colour is
  not the same thing, is allowed, and is how the ground is coloured**
- No per-building unique textures; the window shader replaces them
- **No texture atlas for buildings.** `merge` refuses textured meshes and two textures cannot share
  one primitive — one primitive per tile is what holds draw calls at 53 of 150 (`Q16`)
- No realistic weather or wet-road reflections in the slice
- **No baked illumination** — flat shading plus one directional light is the look

⚠️ **"No PBR" is not anti-physics.** `Q33`'s cited `reflectance` table *is* PBR's albedo discipline,
done as data instead of as texture maps, and all three shaders — both façades and now the vehicle —
already write `ROUGHNESS` and a fresnel term. What is refused is the texture-map workflow — and
**metalness specifically has nothing to reflect**, because the Mobile renderer has no SSR and no
probes, so a metal surface renders as sky-coloured plastic.

⚠️ **That last clause stopped being an argument and became a measurement** (`P3-11c`). Uniform gloss
on the shipped taxi moved the red bodywork `C*` **79.06 → 70.08** and its hue **−7.9°** in sun, while
*raising* `L*` — the signature of light the albedo did not ask for. So the cost of gloss here is
paid in **chroma**, on whatever object is carrying the frame's colour, and it is not recoverable by
tuning: with nothing to reflect, a specular lobe returns ambient. Gloss is affordable exactly where
the surface is *supposed* to read as a dark mirror — glazing — and nowhere else.

⚠️ **Three reasons that do *not* support the photogrammetry entry, and must not be cited for it.**
Not **size**: a 45 MP sheet compresses to ~1 MB against a 128 MB texture budget and ~167 MB of unused
bundle, so "compress it smaller" answers an objection nobody made. Not **trademark** in the legal
sense — *signature look* is what is meant, and calling it trademark reads as an IP claim beside hard
rule 8's SEGA one; the imagery is CSDI / DATA.GOV.HK open data. Not **licence**: `LICENSING.md`
records that commercial use is explicit and that an exported build already ships derived government
data. What holds it up is the photogrammetry *look*, a real mismatch with flat shading, and the
structural blockers.

⚠️ **The atlas entry's reason is `merge`, not memory and not UVs.** UVs are the second problem and
the soluble one — see "What buildings will *not* get" for why they are not even the first obstacle.

⚠️ **Baked *occlusion* is a different question, and is not refused here.** AO is sun-independent,
survives both rigs and a night mode without a rebake, and is the only occlusion the mobile tier can
have on **static geometry**, which ships no realtime shadow maps at all. What blocks a *lightmap* is
**texel budget** — 2.143 km² of terrain alone is 2.1 M texels at one per m², before a single façade —
plus the baked sun `Q26` has not chosen, and LOD1 carrying no lightmap across the 250 m tier switch.
⚠️ **It is not "UVs do not survive clustering"**, because Godot's importer generates its own UV2
unwrap. ⚠️ **And that importer behaviour is now an armed hazard rather than a curiosity**: since
schema 6 the tiles' UV2 *is* the façade-survey payload, so raising `meshes/light_baking` to Static
Lightmaps would silently overwrite 1,600 buildings' measured verdicts with an unwrap.
`verify_tiles.gd` asserts the import setting and the payload's integer exactness, so the regression
fails the check instead of shipping.
