// Window bands on the city's massing, drawn procedurally (`P3-7`).
//
// Dense repetitive window grids are the defining visual signature of Hong Kong
// residential towers, and this is the cheapest way to have them: no texture, no
// texture memory, no UV atlas, and no second draw call. `docs/ART_DESIGN.md`
// makes the case; what is worth knowing here is how it gets its inputs.
//
// Two of them cannot be derived from geometry, so `etl/pipeline/buildings.py`
// ships them in `TEXCOORD_0`:
//
//   UV.x  metres above this object's own base. A vertex knows its world Y, and
//         Wan Chai's ground moves 40 m across the region — so world Y says
//         nothing about which floor a wall vertex is on. Metres rather than a
//         0-1 fraction because the floor *count* is the signature: normalised, a
//         3-storey shophouse and a 40-storey tower get the same number of rows.
//   UV.y  `floor()` is the surface marker, `fract()` is a per-object phase.
//         A tile is one merged primitive, so nothing else tells a facade from a
//         viaduct soffit from the pavement, and without a phase every tower in
//         a block lines its window rows up.
//
// ⚠️ The horizontal coordinate is deliberately *not* shipped. It is derivable
// here from world position and the wall normal, and a payload carrying what the
// geometry already knows costs bytes on every vertex of every tile forever.
//
// ⚠️ This replaces a `BaseMaterial3D` that had `vertex_color_use_as_albedo` set
// at import, so it must apply `COLOR` itself. Drop that and the city renders
// white — the exact failure `tools/generated_scene_import.gd` exists to prevent.
//
// The defaults below are the measured ones, but `tuning/city_facade.tres` is
// what the city actually loads and is where retuning belongs — CLAUDE.md hard
// rule 4. These exist so the shader is usable on its own.

shader_type spatial;

// Deliberately not `diffuse_lambert`, tempting as that is on the mobile tier.
// This replaces a `BaseMaterial3D` on geometry that has already been reviewed
// and screenshotted, and changing the shading model in the same commit would put
// a lighting change and the bands into one before/after comparison.
render_mode cull_back;

// Marker values, matching `SurfaceClass` in `etl/pipeline/config.py`. Part of
// `city.json`'s `schema_version` rather than a private enumeration: renumber
// either side and a viaduct silently grows windows.
const float MARKER_FACADE = 0.0;
const float MARKER_GROUND = 1.0;
const float MARKER_STRUCTURE = 2.0;

group_uniforms floors;
// Storey height. Measured off the source facade textures rather than guessed:
// 227 walls on 219 buildings of one individualised sheet, height-weighted median
// **2.77 m** — Hong Kong's domestic floor-to-floor is among the tightest
// anywhere, and a guessed 3.2 would have put a storey too few on every tower.
// docs/PROGRESS.md carries the distribution.
uniform float floor_height_m : hint_range(2.0, 6.0) = 2.8;
// Share of each storey the glazing occupies, and of each column bay.
uniform float window_height_ratio : hint_range(0.0, 1.0) = 0.55;
// Measured the same way, turned ninety degrees: p50 2.42 m over 88 walls.
uniform float column_pitch_m : hint_range(1.0, 12.0) = 2.4;
uniform float window_width_ratio : hint_range(0.0, 1.0) = 0.62;
// Height below which no windows are drawn. A podium is shopfront and plant, not
// flats, and banding it is the giveaway that the effect is procedural.
// ⚠️ Authored, not measured — the probe recovers a period, and where a facade
// *stops* being periodic is a different question it could not answer.
uniform float podium_height_m : hint_range(0.0, 40.0) = 12.0;

group_uniforms appearance;
uniform vec3 window_colour : source_color = vec3(0.24, 0.26, 0.30);
uniform float window_opacity : hint_range(0.0, 1.0) = 0.62;
// A floor line reads where a window does not, and it is what keeps a blank
// podium looking like the same material as the tower above it.
uniform float floor_line_darkness : hint_range(0.0, 1.0) = 0.12;
// Grounding a wall where it meets the pavement does more for perceived quality
// than per-building colour accuracy, and costs nothing now that UV.x exists.
uniform float grounding_height_m : hint_range(0.0, 12.0) = 3.0;
uniform float grounding_darkness : hint_range(0.0, 1.0) = 0.22;

group_uniforms surface;
// Matches the `BaseMaterial3D` these tiles imported with before this shader.
uniform float roughness_value : hint_range(0.0, 1.0) = 0.9;
// How near vertical a face must be to carry windows. Roofs and soffits are
// excluded by this rather than by their marker, because a roof belongs to a
// facade object and shares its marker.
uniform float wall_normal_max : hint_range(0.0, 1.0) = 0.5;

group_uniforms distance_fade;
// Bands are a few metres across, so past the near band they go sub-pixel and
// alias into moire. LOD1 sits at 250-400 m and is specified as silhouette-only
// flat colour, which is what fading to nothing delivers.
uniform float fade_start_m : hint_range(0.0, 400.0) = 90.0;
uniform float fade_end_m : hint_range(0.0, 600.0) = 240.0;

group_uniforms night;
// Reserved, and shipped at zero. `ART_DESIGN.md` calls night a strong later
// variant and says to plan the emissive channel now — having the uniforms makes
// that mode a parameter change rather than a second shader.
uniform vec3 lit_window_colour : source_color = vec3(1.0, 0.85, 0.55);
uniform float lit_window_share : hint_range(0.0, 1.0) = 0.0;
uniform float emission_strength : hint_range(0.0, 4.0) = 0.0;

varying float height_m;
// ⚠️ **`flat`** — see `city_facade_clean.gdshader` for the measurement (`Q28`).
// Both are per-object, a plain varying interpolates them, and an interpolated
// `phase` hashes into random banding on a flat wall. `height_m` above is the
// one that genuinely varies within a face and stays interpolated.
varying flat float phase;
varying flat float marker;
varying float upness;
varying float along_m;

// One repeat of `u`, antialiased against how fast `u` changes on screen.
//
// ⚠️ **The derivative is taken before the wrap, and that is the whole reason
// this is a function.** `fwidth(fract(u))` spikes to ~1 at every repeat
// boundary, so each storey line would render as a wide grey smear — an artefact
// that looks like a lighting bug and is really a sampling one. `fwidth(u)` is
// smooth across the seam because `u` is.
float band(float u, float low, float high) {
	float w = fwidth(u) * 0.5 + 1e-5;
	float x = fract(u);
	return smoothstep(low - w, low + w, x) - smoothstep(high - w, high + w, x);
}

void vertex() {
	height_m = UV.x;
	marker = floor(UV.y);
	phase = fract(UV.y);

	vec3 world_normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
	upness = abs(world_normal.y);

	// Distance along the wall, in metres, from an arbitrary but *consistent*
	// origin: the plan-perpendicular of the face normal. Two faces of one
	// building that share a normal therefore share a column grid, and a corner
	// is where the grid changes — which is what a real building does.
	vec3 world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec2 tangent = vec2(-world_normal.z, world_normal.x);
	float span = length(tangent);
	along_m = span > 1e-4 ? dot(world.xz, tangent / span) : 0.0;
}

// ⚠️ **`COLOR_0` is authored in sRGB and has to be converted here**, exactly as
// in `city_facade_clean.gdshader` — see that file for the measurement. Godot 4
// has no `vertex_color_is_srgb` render mode, so every shader reading `COLOR`
// converts it or silently renders a pale, low-contrast city. Duplicated rather
// than shared through a `.gdshaderinc`: two call sites do not earn a third file,
// and both are named in `docs/ARCHITECTURE.md`'s `COLOR_0` row.
vec3 vertex_srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

void fragment() {
	vec3 albedo = vertex_srgb_to_linear(COLOR.rgb);
	bool is_facade = marker < MARKER_FACADE + 0.5;

	// Grounded before the windows, so a ground-floor pane is darkened with the
	// wall it sits in rather than punched through it.
	if (is_facade) {
		albedo *= mix(
				1.0 - grounding_darkness, 1.0, smoothstep(0.0, grounding_height_m, height_m)
			);
	}

	if (is_facade && upness < wall_normal_max && height_m > podium_height_m) {
		// The phase offsets the grid rather than scaling it: two neighbouring
		// towers must not share a row, and must still have the same storey
		// height as each other and as the real city.
		float storey = (height_m - podium_height_m) / floor_height_m + phase;
		float column = along_m / column_pitch_m + phase;

		// Everything the grid draws fades together. Fading only the glazing would
		// leave the floor lines at full strength for ever, and `ART_DESIGN.md`
		// specifies the 250-400 m tier as silhouette-only flat colour — a hairline
		// grid surviving out there is both off-spec and the part that aliases
		// worst, being one pixel wide by definition.
		float fade = 1.0 - smoothstep(fade_start_m, fade_end_m, length(VERTEX));

		// A slab edge sits at the storey boundary; the glazing is centred in the
		// bay above it. Centred rather than flush to the top so neither mask
		// straddles the wrap, where `fract` would split one window into two.
		albedo *= 1.0 - floor_line_darkness * band(storey, 0.0, 0.08) * fade;

		float glass = band(storey, 0.5 - window_height_ratio * 0.5, 0.5 + window_height_ratio * 0.5)
			* band(column, 0.5 - window_width_ratio * 0.5, 0.5 + window_width_ratio * 0.5);
		glass *= fade;

		albedo = mix(albedo, window_colour, glass * window_opacity);

		if (emission_strength > 0.0 && lit_window_share > 0.0) {
			// Per window, and stable: hashed from the pane's own row and column
			// plus the object phase, so a lit window stays lit as the camera
			// moves instead of sparkling per fragment.
			vec2 pane = vec2(floor(storey), floor(column));
			float hashed = fract(sin(dot(pane, vec2(12.9898, 78.233)) + phase * 91.0) * 43758.5453);
			EMISSION = lit_window_colour
				* (glass * step(1.0 - lit_window_share, hashed) * emission_strength);
		}
	}

	ALBEDO = albedo;
	METALLIC = 0.0;
	ROUGHNESS = roughness_value;
}
