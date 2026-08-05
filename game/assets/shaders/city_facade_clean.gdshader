// The city's massing in a clean high-key idiom, drawn procedurally.
//
// A variant of `city_facade.gdshader`, reading the **same** `TEXCOORD_0` payload
// and the same surface markers — so it is a look change, not a data change, and
// swapping between the two is one `ext_resource` line in `tuning/city_facade.tres`
// with no rebuild. The measured shader is kept beside this one for that reason.
//
// ⚠️ **The complaint this answers was "the repeating window looks dull", and the
// fault was scale rather than colour.** `city_facade` draws at the *measured*
// pitch — 2.8 m storeys by 2.4 m columns — which is honest and, at 30 m from a
// moving car, about four pixels across. Too fine to read as architecture and too
// regular to read as material, so it becomes noise that the 90 m fade then
// deletes. Everything here is drawn an order of magnitude larger: a glazing
// ribbon spans a group of storeys, a bay is ~9 m, and the unit of variation is
// the **building**, not the window.
//
// The three renderer tricks doing the work, none of which needs a texture:
//
//   1. **Per-building treatment.** `fract(UV.y)` is already a stable seed
//      quantised to 1/256 by the ETL. Hashed, it picks whether a building is a
//      solid white mass, a glazed curtain wall, or an accent-banded one. Two in
//      five buildings therefore repeat *nothing*, which is what stops a block
//      reading as one wallpapered surface.
//   2. **Fresnel sky reflection.** `pow(1 - dot(NORMAL, VIEW), p)` mixed toward a
//      sky colour is a mirrored tower for a few ALU instructions — no reflection
//      probe, which `ART_DESIGN.md` lists as an anti-goal, and no cubemap.
//   3. **Grazing sky bounce on white walls.** The same term at low strength on
//      solid walls is what keeps a white city from reading as grey cardboard,
//      and it cools the shadowed faces the way the reference art does.
//
// The inputs are `city_facade`'s, unchanged and documented there in full:
//
//   UV.x  metres above this object's own base
//   UV.y  `floor()` is the surface marker, `fract()` is a per-object phase
//
// ⚠️ Like its sibling, this replaces a `BaseMaterial3D` that had
// `vertex_color_use_as_albedo` set at import, so it must apply `COLOR` itself.

shader_type spatial;

render_mode cull_back;

// Marker values, matching `SurfaceClass` in `etl/pipeline/config.py`.
const float MARKER_FACADE = 0.0;
const float MARKER_GROUND = 1.0;
const float MARKER_STRUCTURE = 2.0;

// The ETL quantises the phase to `k / 256` (`_PHASES` in `buildings.py`), so the
// integer seed round-trips exactly. Hashing the integer rather than the fraction
// keeps neighbouring seeds far apart in every derived decision.
const float PHASE_STEPS = 256.0;

group_uniforms massing;
// How far the ETL's vertex colour is pulled toward `base_colour`. Not 1.0: the
// five `height_bands` in `etl/config/cities/hong_kong.yaml` encode the city's
// old-below / new-above grain, and washing them out entirely throws away real
// information for no gain. At 0.82 they survive as a tint under the white.
//
// ⚠️ This is the *trial* home for the palette. If the look is kept, the bands
// themselves should be re-authored pale in the city config — CLAUDE.md says the
// palette lives there — and this drops back toward 0. It is a uniform so the
// look can be judged before anyone pays for a rebuild.
uniform vec3 base_colour : source_color = vec3(0.91, 0.92, 0.93);
uniform float base_wash : hint_range(0.0, 1.0) = 0.82;
// Per-building brightness spread, from the phase seed. `colour_jitter` in the
// city config does this in vertex colour, and `base_wash` is exactly what
// flattens it — so the wash has to put back what it takes out, or a whitened
// block reads as a single mass. Seeded, so it is stable frame to frame.
// ⚠️ **Measured, not chosen** — see the 2026-08-06 probe in `docs/PROGRESS.md`.
// Across 140 buildings of one sheet the between-building spread is ΔE 17, and it
// is lopsided: **L\* sd 18.05 against b\* 7.44 and a\* 3.50**. So the fabric
// varies a lot in *lightness*, a little along **warm-cool**, and almost not at
// all in hue — 69% of buildings are perceptually near-neutral. ±7% was roughly
// ±3 L\*, several times smaller than what the photographs show, which is why a
// block read as one mass.
//
// ⚠️ The photographic L\* also confounds reflectance with illumination, so the
// measured spread is an *upper* bound and this is deliberately under it.
uniform float value_jitter : hint_range(0.0, 0.6) = 0.2;
// The warm-cool axis, per building. `b*` varies twice as much as `a*` in the
// photographs, which is cream against grey-blue — so this shifts red against
// blue and leaves green alone rather than rotating hue properly.
uniform float warm_cool_jitter : hint_range(0.0, 0.3) = 0.07;

group_uniforms panels;
// The measured storey height, still: the massing is real and the floor rhythm
// should be. What changes is that glazing spans a *group* of storeys.
uniform float floor_height_m : hint_range(2.0, 6.0) = 2.8;
uniform float band_storeys : hint_range(1.0, 6.0) = 2.0;
// Share of each band the glazing ribbon occupies.
uniform float glass_ratio : hint_range(0.0, 1.0) = 0.52;
// Structural bay, not a window column. ~9 m is a real curtain-wall module and,
// unlike a 2.4 m one, it is still several pixels wide at the far plane — which
// is why the fade below can run four times further out than the sibling's.
uniform float bay_width_m : hint_range(2.0, 24.0) = 9.0;
uniform float mullion_ratio : hint_range(0.0, 0.5) = 0.08;
uniform float mullion_darkness : hint_range(0.0, 1.0) = 0.35;
// Where the tower grid starts. A podium is shopfront and plant, not flats.
// Authored, not measured.
uniform float podium_height_m : hint_range(0.0, 40.0) = 12.0;

group_uniforms street;
// ⚠️ **The podium is the only part of a facade a driver ever meets, and masking
// it is what made the first screenshot of this shader read as blank card.** The
// tower grid is invisible from a car at 1.5 m of eyeline; everything below
// `podium_height_m` is what fills the frame. So the podium gets its own
// elements rather than being a hole in the mask: a shopfront ribbon, a cornice
// where it ends, and — on an accent building — the colour, down here where it
// is seen rather than forty storeys up.
uniform float shopfront_base_m : hint_range(0.0, 4.0) = 0.7;
uniform float shopfront_top_m : hint_range(1.0, 12.0) = 4.6;
// ⚠️ **Not every building, which is what this used to be.** "At street level even
// a solid mass has shops in it" is true of Hennessy Road and false of a
// convention centre, an MTR entrance or a waterfront podium — and applied
// unconditionally at one height and one pitch it draws the same dark ribbon
// along an entire street, which is the most repetitive thing in the frame
// precisely because it is the part a driver is closest to.
//
// ⚠️ **This cannot be made *correct*, only varied.** The massing dataset is
// geometry: no land use, no building use, no ground-floor attribute. The shader
// knows height above base, a surface marker and a seed, so which buildings
// really have shopfronts is not knowable here or anywhere else in the pipeline.
// Fixing that means a land-use source and a schema bump; see `docs/PROGRESS.md`.
uniform float shopfront_share : hint_range(0.0, 1.0) = 0.55;
// Podium piers are structural and much heavier than a curtain-wall mullion, so
// a shopfront is discrete openings rather than a continuous band of glass.
uniform float shopfront_pier_ratio : hint_range(0.0, 0.9) = 0.46;
// The line where the podium stops and the tower starts. Thin, and in metres
// rather than as a ratio so it stays one architectural element at any height.
uniform float cornice_thickness_m : hint_range(0.0, 2.0) = 0.5;
uniform float cornice_darkness : hint_range(0.0, 1.0) = 0.28;

group_uniforms treatment;
// Share of buildings that carry no glazing at all — a plain white mass. The
// single most important number here: it is what makes the city read as composed
// solids rather than as one repeating surface.
uniform float solid_share : hint_range(0.0, 1.0) = 0.38;
// Share that take a saturated colour. Sparing on purpose; the reference art
// uses one bold colour against a lot of white, and raising this reads as a
// theme park rather than as a city.
uniform float accent_share : hint_range(0.0, 1.0) = 0.22;
// Share of a storey band the accent spandrel occupies, measured from the edge
// of the glazing. A *course* rather than all the remaining solid: colouring
// every non-glazed strip makes the building read as the accent with white
// stripes, which is the wrong way round.
uniform float accent_course_ratio : hint_range(0.0, 0.5) = 0.15;

group_uniforms archetypes;
// ⚠️ **One grammar for every building is what reads as "repeated", and the phase
// does not fix it** — offsetting the same grid still leaves the same grid. A
// street photograph of Hong Kong has three or four *different* architectural
// grammars in one frame: vertical-fin towers with continuous piers and no
// horizontal banding at all, full mirror curtain wall, punched windows in solid
// stone, and horizontal ribbon. So the seed picks a grammar, not just an offset.
//
// They are one grid with different ratios rather than four code paths: a fin is
// the horizontal cut switched off and the piers widened, curtain wall is both
// masks nearly open, punched is both nearly closed.
uniform float fin_share : hint_range(0.0, 1.0) = 0.24;
uniform float curtain_share : hint_range(0.0, 1.0) = 0.16;
uniform float punched_share : hint_range(0.0, 1.0) = 0.22;
uniform float fin_pier_ratio : hint_range(0.0, 0.9) = 0.36;
uniform float punched_pier_ratio : hint_range(0.0, 0.9) = 0.52;
// Bay width and glazing pitch vary per building too. Real towers differ in
// structural module; only `floor_height_m` is a constant of the city, and it
// stays the measured one.
uniform float bay_scale_min : hint_range(0.4, 1.0) = 0.72;
uniform float bay_scale_max : hint_range(1.0, 2.5) = 1.45;
uniform float two_storey_share : hint_range(0.0, 1.0) = 0.22;

group_uniforms glass;
uniform vec3 glass_colour : source_color = vec3(0.16, 0.21, 0.26);
// Two more, hashed per building. Hong Kong's curtain walls run from near-black
// bronze through blue-green to pale blue, and one glass colour across a district
// is as flat as one wall colour would be.
uniform vec3 glass_tint_b : source_color = vec3(0.13, 0.22, 0.21);
uniform vec3 glass_tint_c : source_color = vec3(0.44, 0.55, 0.63);
// What the glazing reflects. ⚠️ **A single `sky_reflection` colour is why the
// glass reads as a swatch rather than as a mirror** — real glass shows the sky
// *gradient*, so the reflected ray's own elevation has to pick between these.
// Below the horizon it reflects the city, which is darker than either.
uniform vec3 sky_zenith : source_color = vec3(0.24, 0.47, 0.78);
uniform vec3 sky_horizon : source_color = vec3(0.85, 0.91, 0.96);
uniform vec3 ground_reflection : source_color = vec3(0.32, 0.33, 0.35);
// Curtain-wall panes are never flat — each one bows slightly, which is exactly
// what makes the wavy light and dark bands running down a real glazed facade.
// Bowing the *reflected ray* per pane costs two hashes and is the single
// cheapest thing here that reads as "alive".
uniform float pane_bow : hint_range(0.0, 1.5) = 0.45;
uniform float pane_jitter : hint_range(0.0, 0.5) = 0.1;
// Reflectance head-on, as a share of the grazing value. Mirror glass is not
// nearly transparent when faced squarely, and treating it as though it were is
// what left every wall facing the camera a flat dark colour.
uniform float glass_face_on : hint_range(0.0, 1.0) = 0.34;
// What the fresnel term reflects. Matched to the environment's sky by hand
// rather than sampled, because sampling the radiance map is a reflection probe
// by another name and the anti-goals rule it out.
uniform vec3 sky_reflection : source_color = vec3(0.62, 0.78, 0.92);
uniform float glass_reflect : hint_range(0.0, 1.0) = 0.85;
uniform float fresnel_power : hint_range(1.0, 8.0) = 4.0;
uniform float glass_roughness : hint_range(0.0, 1.0) = 0.12;

group_uniforms accent;
// Three, hashed per building. Flat and saturated, and applied to whole spandrel
// bands rather than to window-sized areas — the area is what makes the colour
// register at speed.
uniform vec3 accent_a : source_color = vec3(0.85, 0.19, 0.16);
uniform vec3 accent_b : source_color = vec3(0.11, 0.45, 0.72);
uniform vec3 accent_c : source_color = vec3(0.95, 0.62, 0.09);
uniform float accent_opacity : hint_range(0.0, 1.0) = 0.9;

group_uniforms walls;
// Sky bounce at grazing angles on solid wall. Low, and the reason a white city
// does not read as grey card.
uniform float wall_sky_tint : hint_range(0.0, 1.0) = 0.18;
// A floor line reads where a window does not, and keeps a blank podium looking
// like the same material as the tower above it.
uniform float floor_line_darkness : hint_range(0.0, 1.0) = 0.07;
// Grounding a wall where it meets the pavement does more for perceived quality
// than per-building colour accuracy, and costs nothing now that UV.x exists.
uniform float grounding_height_m : hint_range(0.0, 12.0) = 3.0;
uniform float grounding_darkness : hint_range(0.0, 1.0) = 0.16;
uniform float wall_roughness : hint_range(0.0, 1.0) = 0.82;
// How near vertical a face must be to carry the panel grid. Roofs and soffits
// are excluded by this rather than by their marker, because a roof belongs to a
// facade object and shares its marker.
uniform float wall_normal_max : hint_range(0.0, 1.0) = 0.5;
// ⚠️ **Excluded from the grid is not the same as excluded from the look**, and
// leaving roofs at the full wash is what blew out every downward view: a roof
// takes the 48° sun nearly head-on, so a white one clips where the wall beside
// it does not. Real roofs are darker than their walls anyway — tar, plant rooms
// and water tanks — so this is cheaper than it is a correction. It is the whole
// roof treatment: nothing up there is seen from a car, and `P3-6`'s landmarks
// are the answer if a rooftop ever needs to be looked at.
uniform float roof_darkness : hint_range(0.0, 1.0) = 0.2;

group_uniforms distance_fade;
// ⚠️ **The fade must finish before the LOD switch, and that is a hard constraint
// rather than a taste.** `tuning/streaming.tres` swaps to LOD1 at **250 m**,
// where buildings are vertex-clustered at 4 m cells — and `TEXCOORD_0.x` comes
// from a *cluster representative*, so out there "metres above the base" is wrong
// by up to a storey and a half and neighbouring triangles disagree about it. Draw
// a grid on that and it shatters into blocky patches and coloured streaks.
//
// `P3-7` faded 90-240 and was safe by accident of being conservative. This was
// briefly set to 260-420 on the reasoning that a 9 m bay survives to the far
// plane — true about *aliasing*, and it ignored the tier entirely.
uniform float fade_start_m : hint_range(0.0, 600.0) = 140.0;
uniform float fade_end_m : hint_range(0.0, 800.0) = 244.0;

group_uniforms night;
// Reserved and shipped at zero, as in the sibling. `ART_DESIGN.md` calls night a
// strong later variant and says to plan the emissive channel now.
uniform vec3 lit_window_colour : source_color = vec3(1.0, 0.85, 0.55);
uniform float lit_window_share : hint_range(0.0, 1.0) = 0.0;
uniform float emission_strength : hint_range(0.0, 4.0) = 0.0;

varying float height_m;
varying float phase;
varying float marker;
varying float upness;
varying float along_m;
// The reflection needs a world-space frame, and both are already computed in the
// vertex stage for `upness` and `along_m` — so carrying them costs interpolators
// rather than work.
varying vec3 world_pos;
varying vec3 world_n;

// One repeat of `u`, antialiased against how fast `u` changes on screen.
//
// ⚠️ **The derivative is taken before the wrap, and that is the whole reason
// this is a function.** `fwidth(fract(u))` spikes to ~1 at every repeat
// boundary, so each line would render as a wide grey smear — an artefact that
// looks like a lighting bug and is really a sampling one. `fwidth(u)` is smooth
// across the seam because `u` is.
// ⚠️ **`COLOR_0` is authored in sRGB and has to be converted here.** The ETL
// picks facade colours in CIELAB and writes the sRGB bytes, while every colour
// uniform above carries `: source_color`, which Godot converts to linear for us.
// `COLOR` gets no such treatment: Godot 4 dropped the `vertex_color_is_srgb`
// render mode (it survives only as a `BaseMaterial3D` flag, which is how
// `generated_scene_import.gd` fixes the road), so a shader must do it itself.
//
// Skipping it does not merely lighten the city — it destroys albedo *contrast*.
// Measured under `Q27`: 57% of a lit facade pixel's luminance was coming from
// albedo-independent light, and a per-building albedo difference reached the
// screen at a third of its size. That is why the measured facade colour looked
// invisible, and why no amount of ambient or tonemap tuning moved it — the loss
// is upstream of the light. The ablation is in `docs/PROGRESS.md`.
//
// The exact IEC 61966-2-1 curve rather than `pow(c, 2.2)`: `etl/pipeline/colour.py`
// uses the exact one, and the two sides disagreeing is what this bug *was*.
vec3 vertex_srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

float band(float u, float low, float high) {
	float w = fwidth(u) * 0.5 + 1e-5;
	float x = fract(u);
	float value = smoothstep(low - w, low + w, x) - smoothstep(high - w, high + w, x);

	// ⚠️ **Past about a quarter of a period per pixel the smoothstep pair stops
	// meaning anything**, and the grid turns into diagonal moire on any wall seen
	// at a shallow angle — which in a street of towers is most of them. The
	// correct value there is the band's own **duty cycle**: what an infinite
	// number of samples inside one pixel would average to. Converging on it is
	// analytic antialiasing rather than a fudge, and it is why this does not need
	// the distance fade to hide it.
	return mix(value, high - low, smoothstep(0.25, 0.5, w));
}

// A band on a value that does **not** wrap, antialiased the way `band` is.
// Separate from it rather than a mode of it because `fract` is simply wrong
// here: a shopfront happens once up the building, not once per storey.
float slab(float u, float low, float high) {
	float w = fwidth(u) * 0.5 + 1e-5;
	return smoothstep(low - w, low + w, u) - smoothstep(high - w, high + w, u);
}

// Everything above `at`, with the same antialiasing. A bare `step` here shows as
// a stair-stepped podium line on any wall seen at a shallow angle.
float over(float u, float at) {
	float w = fwidth(u) * 0.5 + 1e-5;
	return smoothstep(at - w, at + w, u);
}

// Decorrelated draws from one building's seed. `n` selects the draw; the seed is
// the integer the ETL quantised to, so two neighbouring buildings share nothing.
float draw(float seed, float n) {
	return fract(sin(seed * 12.9898 + n * 78.233) * 43758.5453);
}

void vertex() {
	height_m = UV.x;
	marker = floor(UV.y);
	phase = fract(UV.y);

	vec3 world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
	upness = abs(world_normal.y);

	// Distance along the wall, in metres, from a consistent origin.
	//
	// ⚠️ **Not the plan-perpendicular of the face normal, which is what this used
	// to be and what broke every curved podium.** Deriving the tangent from the
	// face normal gives each triangle of a *curved* facade its own grid origin,
	// so the bays shatter into per-triangle strips — chevrons and streaks
	// wherever Hong Kong puts a round corner on a mall. It survived in `P3-7`
	// only because a 2.4 m column pitch made the seams read as noise.
	//
	// Projecting onto a world axis *chosen* by the normal is continuous as the
	// normal turns: a wall facing X runs along Z, and vice versa. The blend band
	// stretches the bays slightly near 45°, which is far cheaper than a seam.
	vec3 world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	float faces_x = abs(world_normal.x);
	float faces_z = abs(world_normal.z);
	float pick = faces_x / max(faces_x + faces_z, 1e-4);
	along_m = mix(world.x, world.z, smoothstep(0.35, 0.65, pick));

	world_pos = world;
	world_n = world_normal;
}

void fragment() {
	bool is_facade = marker < MARKER_FACADE + 0.5;
	float seed = floor(phase * PHASE_STEPS + 0.5);

	vec3 albedo = mix(vertex_srgb_to_linear(COLOR.rgb), base_colour, is_facade ? base_wash : 0.0);
	if (is_facade) {
		// Put back the per-building variation the wash just flattened, and
		// ground the wall where it meets the pavement.
		albedo *= 1.0 + (draw(seed, 3.0) - 0.5) * 2.0 * value_jitter;
		float warm = (draw(seed, 12.0) - 0.5) * 2.0 * warm_cool_jitter;
		albedo *= vec3(1.0 + warm, 1.0, 1.0 - warm);
		albedo *= mix(
				1.0 - grounding_darkness, 1.0, smoothstep(0.0, grounding_height_m, height_m)
			);
	}

	// Grazing-angle terms. One fresnel serves the glass reflection, the wall sky
	// bounce and the night mask, so it is computed once whatever the treatment.
	float facing = clamp(dot(normalize(NORMAL), normalize(VIEW)), 0.0, 1.0);
	float fresnel = pow(1.0 - facing, fresnel_power);

	float roughness = wall_roughness;

	// Roofs and soffits: no grid, but not untouched. See `roof_darkness`.
	if (is_facade && upness >= wall_normal_max) {
		albedo *= 1.0 - roof_darkness * upness;
	}

	if (is_facade && upness < wall_normal_max) {
		// Everything the grid draws fades together, so a hairline does not
		// survive out where the surface it belongs to has gone flat.
		float fade = 1.0 - smoothstep(fade_start_m, fade_end_m, length(VERTEX));

		// Per-building draws, taken once. `glazed` decides whether this building
		// has a curtain wall at all — 38% do not, and that share is what stops a
		// block reading as one wallpapered surface.
		float glazed = step(solid_share, draw(seed, 1.0));
		bool accented = draw(seed, 2.0) < accent_share;
		float which = draw(seed, 4.0);
		vec3 accent = which < 0.34 ? accent_a : (which < 0.67 ? accent_b : accent_c);

		// The phase offsets the grids and the seed now *scales* them too: two
		// towers with the same rhythm at different offsets still read as one
		// wallpaper. `floor_height_m` stays the measured constant of the city —
		// what varies is the structural module and how many storeys a glazing
		// band spans, both of which really do differ building to building.
		float bay_scale = mix(bay_scale_min, bay_scale_max, draw(seed, 6.0));
		float band_mult = draw(seed, 7.0) < two_storey_share ? 2.0 : 1.0;

		float band_pitch_m = floor_height_m * band_storeys * band_mult;
		float storey = (height_m - podium_height_m) / floor_height_m + phase;
		float ribbon = (height_m - podium_height_m) / band_pitch_m + phase;
		float bay = along_m / (bay_width_m * bay_scale) + phase;
		float above = over(height_m, podium_height_m);

		// Which grammar this building is built in. One grid, four sets of ratios.
		float kind = draw(seed, 5.0);
		float h_ratio = glass_ratio;
		float pier = mullion_ratio;
		float horizontal = 1.0;
		if (kind < fin_share) {
			// Vertical fin: continuous piers the full height, no horizontal cut.
			horizontal = 0.0;
			pier = fin_pier_ratio;
		} else if (kind < fin_share + curtain_share) {
			// Full curtain wall: both masks nearly open, a hairline grid.
			h_ratio = 0.92;
			pier = 0.05;
		} else if (kind < fin_share + curtain_share + punched_share) {
			// Punched windows in solid wall — the older stock.
			h_ratio = glass_ratio * 0.62;
			pier = punched_pier_ratio;
		}

		// --- the podium, which is the only part a driver ever meets ---------

		// A shopfront on *some* buildings, at a height that varies: a lobby is
		// double height, a shop is not, and a podium may have neither.
		float has_shop = step(1.0 - shopfront_share, draw(seed, 10.0));
		float shop_top = shopfront_top_m * mix(0.8, 1.5, draw(seed, 11.0));
		float shop = slab(height_m, shopfront_base_m, shop_top) * fade * has_shop;
		// The plinth between the shopfront and the cornice. On an accent
		// building it takes the colour — down here, where it is seen.
		if (accented) {
			float plinth = slab(height_m, shopfront_top_m, podium_height_m - cornice_thickness_m);
			albedo = mix(albedo, accent, plinth * accent_opacity * fade);
		}
		// A cornice where the podium stops and the tower starts. It is what
		// makes the two read as one building with a base rather than as a tower
		// standing in a box.
		albedo *= (
			1.0
			- cornice_darkness
				* slab(height_m, podium_height_m - cornice_thickness_m, podium_height_m)
				* fade
		);

		// --- the tower ------------------------------------------------------

		// A slab edge at every storey, faint — it is the only thing left at the
		// old fine pitch, and it is what keeps the real floor count legible on a
		// building whose glazing spans two storeys at a time.
		albedo *= 1.0 - floor_line_darkness * band(storey, 0.0, 0.06) * fade * above;

		// Glazing centred in its band so neither mask straddles the wrap, where
		// `fract` would split one ribbon into two.
		float ribbon_mask = mix(
			1.0, band(ribbon, 0.5 - h_ratio * 0.5, 0.5 + h_ratio * 0.5), horizontal
		);

		// A spandrel course under each glazing ribbon carries the accent up the
		// tower. Bounded rather than "all the remaining solid": colouring every
		// non-glazed strip makes the building read as the accent with white
		// stripes, which is the wrong way round.
		if (accented && glazed > 0.5) {
			float course = band(
				ribbon,
				0.5 + glass_ratio * 0.5,
				0.5 + glass_ratio * 0.5 + accent_course_ratio
			);
			albedo = mix(albedo, accent, course * above * accent_opacity * fade);
		}

		// Mullions divide the glazing into bays. Drawn into the albedo after the
		// glass is mixed in so a mullion is opaque frame, not tinted glass.
		float tower = ribbon_mask * glazed * above * fade;
		// ⚠️ **A mullion is wall, not a dark line.** The pier between two panes is
		// the same pale concrete as the facade, so this cuts the glass away and
		// lets the wall through — it must not also darken what it reveals, which
		// is what made the first pass read as a black slot with scratches in it.
		// `mullion_darkness` is now only the thin shadow line at the reveal.
		// Tower and podium get their own pier width — a curtain-wall mullion and
		// a podium column are not the same member.
		float mullion = band(bay, 0.0, pier);
		float shop_mullion = band(bay, 0.0, shopfront_pier_ratio);
		float glass = clamp(
			tower * (1.0 - mullion) + shop * (1.0 - shop_mullion), 0.0, 1.0
		);
		float reveal = max(mullion * tower, shop_mullion * shop);

		// The mirror. A reflected ray's own elevation picks up the sky gradient,
		// so a wall's glazing changes as it turns and as the camera moves — which
		// is the difference between glass and a dark swatch. Below the horizon it
		// reflects the city rather than the sky.
		vec3 to_surface = normalize(world_pos - INV_VIEW_MATRIX[3].xyz);
		vec3 bounced = reflect(to_surface, normalize(world_n));
		// Per-pane bow, the thing that makes a real glazed facade ripple.
		vec2 pane = vec2(floor(ribbon), floor(bay));
		vec2 within = vec2(fract(ribbon), fract(bay)) - 0.5;
		float bowed = bounced.y
			+ within.x * pane_bow
			+ (draw(seed + dot(pane, vec2(3.0, 17.0)), 9.0) - 0.5) * pane_jitter;
		vec3 mirrored = mix(
			ground_reflection,
			mix(sky_horizon, sky_zenith, clamp(bowed, 0.0, 1.0)),
			smoothstep(-0.08, 0.08, bowed)
		);

		float tint = draw(seed, 8.0);
		vec3 pane_colour = tint < 0.34 ? glass_colour : (tint < 0.67 ? glass_tint_b : glass_tint_c);
		vec3 glazing = mix(
			pane_colour, mirrored, glass_reflect * mix(glass_face_on, 1.0, fresnel)
		);
		albedo = mix(albedo, glazing, glass);
		roughness = mix(wall_roughness, glass_roughness, glass);
		albedo *= 1.0 - mullion_darkness * reveal * (1.0 - glass);

		if (emission_strength > 0.0 && lit_window_share > 0.0) {
			// Per pane, and stable: hashed from the pane's own course and bay
			// plus the building seed, so a lit pane stays lit as the camera
			// moves instead of sparkling per fragment.
			vec2 pane = vec2(floor(ribbon), floor(bay));
			float hashed = fract(sin(dot(pane, vec2(12.9898, 78.233)) + seed * 0.37) * 43758.5453);
			EMISSION = lit_window_colour
				* (glass * step(1.0 - lit_window_share, hashed) * emission_strength);
		}
	}

	// Sky bounce on everything the grid did not turn into glass. Applied last so
	// it lifts the accent bands and the podium too — a white city without it
	// reads as grey card wherever the sun is not directly on it.
	albedo = mix(albedo, sky_reflection, fresnel * wall_sky_tint * (is_facade ? 1.0 : 0.0));

	ALBEDO = albedo;
	METALLIC = 0.0;
	ROUGHNESS = roughness;
}
