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
// The inputs are `city_facade`'s, unchanged and documented there in full,
// plus the survey channel this shader alone consumes (schema 6):
//
//   UV.x   metres above this object's own base
//   UV.y   `floor()` is the surface marker, `fract()` is a per-object phase
//   UV2.x  packed per-building survey state (`Q40`/`Q41`): glazed verdict,
//          glass-tint bin and grammar, each field 0 = refused → the hash
//   UV2.y  reserved for `Q42`'s riders, 0.0 in schema 6
//
// ⚠️ Like its sibling, this replaces a `BaseMaterial3D` that had
// `vertex_color_use_as_albedo` set at import, so it must apply `COLOR` itself.
//
// ⚠️ **The defaults below are this shader's first pass, not what ships**, and
// several were corrected after they were judged on real geometry — the bay is
// 5.5 m rather than 9, the glazing spans one storey rather than two, and the
// fade ends inside the LOD1 switch. `tuning/city_facade.tres` is what the city
// actually loads and is where retuning belongs (CLAUDE.md hard rule 4); these
// exist so the shader is usable on its own. Read a number here as the argument
// that produced it, and the `.tres` as the verdict.

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

// The `TEXCOORD_1` survey codec (schema 6). ⚠️ **Contract constants, not
// tuning** — mirrors of `facade_state` in `etl/pipeline/buildings.py`, recorded
// in `docs/ARCHITECTURE.md`'s channel table, the same standing as `PHASE_STEPS`:
// a one-sided change decodes every surveyed building silently wrong. The codes
// are integers well under float32's 2^24 exact ceiling, so unlike the phase
// there is no rounding case — decode still `floor(x + 0.5)`s first.
const float SURVEY_TINT_FIELD = 4.0;
const float SURVEY_GRAMMAR_FIELD = 1024.0;
const float SURVEY_TINT_L_MIN = 5.0;
const float SURVEY_TINT_L_STEP = 4.0;
const float SURVEY_TINT_B_MIN = -16.0;
const float SURVEY_TINT_B_STEP = 2.0;
const float SURVEY_TINT_B_BINS = 16.0;
// Grammar codes 1-5, pinned to `GRAMMAR_STATES` order in `buildings.py`.
const float SURVEY_CURTAIN = 1.0;
const float SURVEY_PUNCHED = 2.0;
const float SURVEY_FIN = 3.0;
const float SURVEY_BLANK = 4.0;
const float SURVEY_MIXED = 5.0;

group_uniforms massing;
// How far the ETL's vertex colour is pulled toward `base_colour`. Not 1.0: the
// vertex colour carries the city's per-building variation and washing it out
// entirely throws away real information for no gain.
//
// ⚠️ **It is *not* an old-below / new-above grain, which is what this comment
// claimed until `Q34`.** That reading was tested and refused: height explains
// 0.9% of measured facade lightness. What the colour does carry is the measured
// hue from `facade_hue`, the per-building jitter, and a material drawn from that
// hue — see `etl/config/cities/hong_kong.yaml`'s `material_assignment`.
//
// ⚠️ **A trial home for the palette, not its home.** The palette lives in the
// city config (CLAUDE.md hard rule 4); this exists so a level can be judged
// before anyone pays for a rebuild, and is expected to sit at 0 once whatever it
// proved has been written back into the bands. The `.tres` has the verdict.
uniform vec3 base_colour : source_color = vec3(0.91, 0.92, 0.93);
uniform float base_wash : hint_range(0.0, 1.0) = 0.82;
// Per-building brightness spread, from the phase seed. `colour_jitter` in the
// city config does the same job in vertex colour; this one exists because it can
// be judged without a rebuild. Seeded, so it is stable frame to frame.
// ⚠️ **Measured, not chosen** — see the 2026-08-06 probe in `docs/PROGRESS.md`.
// Across 140 buildings of one sheet the between-building spread is ΔE 17, and it
// is lopsided: **L\* sd 18.05 against b\* 7.44 and a\* 3.50**. So the fabric
// varies a lot in *lightness*, a little along **warm-cool**, and almost not at
// all in hue — 69% of buildings are perceptually near-neutral. ±7% was roughly
// ±3 L\*, several times smaller than what the photographs show, which is why a
// block read as one mass.
//
// ⚠️ That photographic spread is an *upper* bound and this stays well under it:
// a quarter of the survey's `L*` variance tracks nothing but how many pixels the
// building covered, so it overstates how much real albedo varies.
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

group_uniforms survey;
// The measured-survey overrides (`Q40`/`Q41`): at 1.0 a building whose
// `TEXCOORD_1` state commits a verdict draws that verdict — glazed, grammar and
// glass tint — and only refusals fall to the hash. **Ships at 0.0** (user's
// call, 2026-08-09): the parked 2026-08-06 look stays byte-identical, and the
// `Q26` re-shoot grades 1.0 together with the seven un-parked fabric values.
uniform float survey_apply : hint_range(0.0, 1.0) = 0.0;
// The a* the tint encoding dropped — `Q40`'s PCA left 6.5% of the measured
// glass variance on a*, so the reconstruction assumes one value for the city.
// Slightly green, as HK curtain glass reads. Retuned, if at all, at `Q26`.
uniform float glass_astar : hint_range(-12.0, 12.0) = -2.0;

group_uniforms night;
// Reserved and shipped at zero, as in the sibling. `ART_DESIGN.md` calls night a
// strong later variant and says to plan the emissive channel now.
uniform vec3 lit_window_colour : source_color = vec3(1.0, 0.85, 0.55);
uniform float lit_window_share : hint_range(0.0, 1.0) = 0.0;
uniform float emission_strength : hint_range(0.0, 4.0) = 0.0;

varying float height_m;
// ⚠️ **`flat`, and it is load-bearing** (`Q28`). Both are *per-object* values —
// `marker` says what a surface is, `phase` is the building's seed — and a plain
// varying interpolates them. Where a triangle's corners disagree, which
// `collapse` produces whenever a cluster spans two buildings (measured: 2.7% of
// LOD0 triangles, worst spread 0.43), `phase` becomes a ramp; `seed` below
// quantises it to 1/256 and `draw()` hashes each step to an unrelated value, so
// a single flat wall fills with random bright and dark bands at `value_jitter`'s
// full amplitude.
varying flat float phase;
varying flat float marker;
// The decoded survey fields: x glazed (0 refused / 1 solid / 2 glazed), y tint
// code (0 refused, else 1..240), z grammar (0 refused, else the codes above).
// `flat` for `phase`'s reason exactly — a per-building value interpolated
// across a cluster-spanning triangle would blend two codes into a third,
// meaningless one.
varying flat vec3 survey_state;
// The surveyed pane colour, decoded once per vertex rather than per glazed
// fragment — the tint is per-building constant, so the fragment stage would
// re-run the whole CIELAB conversion for an answer that never varies within
// the draw. Garbage when `survey_state.y` is 0; the fragment guards on that.
varying flat vec3 survey_pane;
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

// CIELAB to *linear* sRGB — the inverse of `etl/pipeline/colour.py`'s
// `srgb_to_lab`: the same D65 white point and IEC 61966-2-1 primaries, minus
// the transfer curve because the shader works in linear. Mirrored by hand for
// `vertex_srgb_to_linear`'s reason — GLSL cannot import the Python one, and
// the two sides disagreeing is what `Q27` was. Clamped: a measured tint can
// sit outside the gamut, and clipping here matches `lab_to_srgb`'s behaviour.
vec3 lab_to_linear(vec3 lab) {
	float fy = (lab.x + 16.0) / 116.0;
	vec3 f = vec3(fy + lab.y / 500.0, fy, fy - lab.z / 200.0);
	vec3 cubed = f * f * f;
	// (6/29)^3 and the 24389/27 linear-segment slope, exactly as the ETL.
	vec3 xyz = mix((116.0 * f - 16.0) / 903.2962963, cubed, step(vec3(0.0088564517), cubed));
	xyz *= vec3(0.95047, 1.0, 1.08883);
	mat3 from_xyz = mat3(
		vec3(3.2404542, -0.9692660, 0.0556434),
		vec3(-1.5371385, 1.8760108, -0.2040259),
		vec3(-0.4985314, 0.0415560, 1.0572252)
	);
	return clamp(from_xyz * xyz, vec3(0.0), vec3(1.0));
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

	// The packed survey verdicts (`Q40`/`Q41`). Bit fields by division: glazed
	// in bits 0-1, tint in 2-9, grammar in 10-12. An absent channel reads as
	// (0, 0), which decodes to all-refused — the correct state by construction.
	float survey_code = floor(UV2.x + 0.5);
	survey_state = vec3(
		mod(survey_code, SURVEY_TINT_FIELD),
		mod(floor(survey_code / SURVEY_TINT_FIELD), SURVEY_GRAMMAR_FIELD / SURVEY_TINT_FIELD),
		floor(survey_code / SURVEY_GRAMMAR_FIELD)
	);

	// The measured glass (`Q40`): bin centres back to (L*, b*), with the a*
	// the encoding dropped assumed from `glass_astar`. Linear out — no
	// transfer curve, the shader works in linear.
	float tint_code = survey_state.y - 1.0;
	float tint_l = SURVEY_TINT_L_MIN
		+ (floor(tint_code / SURVEY_TINT_B_BINS) + 0.5) * SURVEY_TINT_L_STEP;
	float tint_b = SURVEY_TINT_B_MIN
		+ (mod(tint_code, SURVEY_TINT_B_BINS) + 0.5) * SURVEY_TINT_B_STEP;
	survey_pane = lab_to_linear(vec3(tint_l, glass_astar, tint_b));

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
	// ⚠️ **The ground arrives smooth-shaded, and it is the only surface here that
	// does.** LandsD ships terrain flat — all three normals agree on every one of
	// its 83,637 source triangles — but `mesh.collapse` runs it with
	// `height_field=True`, which drops the facing term from the cluster key and
	// then averages the normals of whatever shares a cell. Measured at the shipped
	// 4 m cell: mean error **8.72°**, with **27.5%** of vertices off by more than
	// 10°. That is what makes an open expanse read as plaster dunes in a city
	// whose every other surface is faceted.
	//
	// The facing key cannot simply come back: it tore the sheet open where a slope
	// crossed a bucket boundary — 99.61% region coverage against 99.84% without —
	// which is the reason `collapse` drops it. So the normal is rebuilt here from
	// the derivatives of view-space position, which is exact for a flat triangle
	// and costs no geometry. Per-face normals from the ETL would have to unweld
	// the ground into ~219k more vertices, about 8 MB against a 32.3 MB PCK, to
	// buy the same lighting.
	//
	// ⚠️ **Computed unconditionally, not inside the branch.** Derivatives are
	// undefined where a pixel quad straddles a non-uniform branch, and a quad on a
	// seam straddles two triangles whose `marker` differs.
	vec3 faceted = normalize(cross(dFdx(VERTEX), dFdy(VERTEX)));
	// Oriented against the interpolated normal rather than fixed by hand. Which
	// way the cross product points follows the winding and the projection's
	// handedness, and a sign that is asserted is a sign that is wrong on one
	// backend. Not `sign()`: it returns zero on a perpendicular pair and would
	// hand the mix below a zero vector to light with.
	faceted = dot(faceted, NORMAL) < 0.0 ? -faceted : faceted;
	NORMAL = normalize(mix(NORMAL, faceted, 1.0 - step(0.5, abs(marker - MARKER_GROUND))));

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
	// bounce and the night mask, so it is computed once whatever the treatment —
	// and only on a facade, because that is its only consumer. The road deck and
	// the ground fill much of a street frame and were paying a `pow` plus two
	// `normalize` each for a term multiplied out at the end of the function.
	float fresnel = 0.0;

	float roughness = wall_roughness;

	if (is_facade) {
		fresnel = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), fresnel_power);

		if (upness >= wall_normal_max) {
			// Roofs and soffits: no grid, but not untouched. See `roof_darkness`.
			albedo *= 1.0 - roof_darkness * upness;
		} else {
			// The three per-building draws, taken once and hoisted because the
			// guard below reads them: whether this building has a curtain wall at
			// all, whether its podium has shopfronts, and whether it takes an
			// accent colour. Between them they are what stops a block reading as
			// one wallpapered surface.
			float glazed = step(solid_share, draw(seed, 1.0));
			float has_shop = step(1.0 - shopfront_share, draw(seed, 10.0));
			bool accented = draw(seed, 2.0) < accent_share;

			// The survey overrides, applied *upstream* of the guard below on
			// purpose: the reader's verdict replaces the hash draw where one was
			// committed (`Q41`), and everything downstream — the guard included —
			// reads the overridden value. A surveyed `blank` wall is solid
			// whatever the glazed axis refused; the merge nulls a glazed-true
			// blank, so the two lines cannot fight a committed verdict.
			bool survey_on = survey_apply > 0.5;
			if (survey_on && survey_state.x > 0.5) {
				glazed = survey_state.x > 1.5 ? 1.0 : 0.0;
			}
			if (survey_on && abs(survey_state.z - SURVEY_BLANK) < 0.5) {
				glazed = 0.0;
			}

			// ⚠️ **Every element below is drawn *into* the albedo, so a tuning that
			// zeroes all of them leaves a no-op that still runs.** `city_facade.tres`
			// ships exactly that today, and without this guard every facade fragment
			// pays ten `sin`, seven `fwidth` and a `reflect()` to be multiplied by
			// zero. The predicate is uniform across the draw when the elements are
			// off, so the branch is coherent rather than divergent — and it still
			// pays when they are on, because `solid_share` of every block is mass
			// with no grid on it at all.
			//
			// ⚠️ **It is derived, so it has to be kept honest.** Anything added below
			// that can reach the albedo while all five of these are off must be added
			// here too. `mullion_darkness` and `emission_strength` are deliberately
			// absent: both reach it only through `glazed` or `has_shop`, which are
			// already tested. The survey overrides need no term either, and for the
			// same reason — they are applied *above*, so `glazed` here is already the
			// overridden value, and the surveyed tint reaches albedo only through
			// `glass`, which needs `glazed`. At `survey_apply = 0.0` the predicate,
			// and the parked look it guards, are byte-identical to schema 5.
			bool draws_detail = glazed > 0.5
				|| has_shop > 0.5
				|| accented
				|| cornice_darkness > 0.0
				|| floor_line_darkness > 0.0;

			if (draws_detail) {
				// Everything the grid draws fades together, so a hairline does not
				// survive out where the surface it belongs to has gone flat.
				float fade = 1.0 - smoothstep(fade_start_m, fade_end_m, length(VERTEX));

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

				// Which grammar this building is built in. One grid, four sets of
				// ratios: 0 ribbon (the default), 1 fin, 2 curtain, 3 punched.
				// Hashed by default; the reader's verdict replaces the draw where
				// one was committed (`Q41`). `mixed` takes the ribbon — "two or
				// more each covering a substantial share" names no single grammar
				// to draw — and `blank` was already handled through `glazed`.
				float kind = draw(seed, 5.0);
				float treatment = 0.0;
				if (kind < fin_share) {
					treatment = 1.0;
				} else if (kind < fin_share + curtain_share) {
					treatment = 2.0;
				} else if (kind < fin_share + curtain_share + punched_share) {
					treatment = 3.0;
				}
				if (survey_on && survey_state.z > 0.5) {
					if (abs(survey_state.z - SURVEY_FIN) < 0.5) {
						treatment = 1.0;
					} else if (abs(survey_state.z - SURVEY_CURTAIN) < 0.5) {
						treatment = 2.0;
					} else if (abs(survey_state.z - SURVEY_PUNCHED) < 0.5) {
						treatment = 3.0;
					} else {
						treatment = 0.0;
					}
				}
				float h_ratio = glass_ratio;
				float pier = mullion_ratio;
				float horizontal = 1.0;
				if (treatment == 1.0) {
					// Vertical fin: continuous piers the full height, no horizontal cut.
					horizontal = 0.0;
					pier = fin_pier_ratio;
				} else if (treatment == 2.0) {
					// Full curtain wall: both masks nearly open, a hairline grid.
					h_ratio = 0.92;
					pier = 0.05;
				} else if (treatment == 3.0) {
					// Punched windows in solid wall — the older stock.
					h_ratio = glass_ratio * 0.62;
					pier = punched_pier_ratio;
				}

				// --- the podium, which is the only part a driver ever meets ---------

				// The shopfront's height varies as well as whether it is there at
				// all — a lobby is double height and a shop is not.
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
				if (survey_on && survey_state.y > 0.5) {
					// The measured glass, decoded in `vertex()` — the hash pick
					// above stays the refusal fallback.
					pane_colour = survey_pane;
				}
				vec3 glazing = mix(
					pane_colour, mirrored, glass_reflect * mix(glass_face_on, 1.0, fresnel)
				);
				albedo = mix(albedo, glazing, glass);
				roughness = mix(wall_roughness, glass_roughness, glass);
				albedo *= 1.0 - mullion_darkness * reveal * (1.0 - glass);

				if (emission_strength > 0.0 && lit_window_share > 0.0) {
					// Per pane, and stable: hashed from the pane's own course and bay
					// plus the building seed, so a lit pane stays lit as the camera
					// moves instead of sparkling per fragment. `pane` is the mirror's,
					// which is the same pane — it was redeclared here and shadowed it.
					float hashed = fract(sin(dot(pane, vec2(12.9898, 78.233)) + seed * 0.37) * 43758.5453);
					EMISSION = lit_window_colour
						* (glass * step(1.0 - lit_window_share, hashed) * emission_strength);
				}
			}
		}
	}

	// Sky bounce on everything the grid did not turn into glass. Applied last so
	// it lifts the accent bands and the podium too — a white city without it
	// reads as grey card wherever the sun is not directly on it. `fresnel` is
	// zero off a facade, so it needs no marker test of its own.
	albedo = mix(albedo, sky_reflection, fresnel * wall_sky_tint);

	ALBEDO = albedo;
	METALLIC = 0.0;
	ROUGHNESS = roughness;
}
