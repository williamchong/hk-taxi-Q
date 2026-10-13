// The tramway — rail heads and track bed (`P3-14`, `Q58`).
//
// Far simpler than `road_markings.gdshader`, and the difference is the whole
// argument of `Q58`. That shader has to *place* markings in lane space, because
// the ribbon it paints is drawn 1.6x too wide and the paint has to survive the
// widening. This one places nothing: `pipeline/tramway.py` puts every vertex at
// the position iB1000 publishes, so there is no codec to decode and no
// coordinate to reconstruct. All that is left is how metal catches light.
//
// Which is why it is worth having a shader at all rather than letting the mesh
// import as vertex-coloured `BaseMaterial3D`. A rail reads as a rail because of
// its **specular**, not its albedo: it is a polished strip in a matte street,
// and at a low sun the highlight running along it is the entire cue. A rail at
// road roughness is a grey line.

shader_type spatial;

render_mode cull_back;

#include "res://assets/shaders/colour.gdshaderinc"

// The rig's exposure (`Q38`): `colour.gdshaderinc` has the account. After
// `vertex_srgb_to_linear`, on `COLOR_0` only.
global uniform float exposure_anchor;

group_uniforms surface;
// ⚠️ **Roughness is the load-bearing value here, not colour.** `hong_kong.yaml`
// already places both albedos against published albedo under `Q33`'s palette
// rule — steel 35%, weathered concrete 22% — and moving them here would put a
// colour outside `materials:`, which is the one thing that table's totality
// depends on. What is *not* in the ETL, because it is not a colour, is how
// sharply each catches the sun.
uniform float rail_roughness : hint_range(0.0, 1.0) = 0.28;
uniform float bed_roughness : hint_range(0.0, 1.0) = 0.9;
// ⚠️ **Low on purpose, and the first value shipped was measured wrong.** A
// metallic surface reflects its environment, and the only environment this
// scene has is the sky — so at 0.65 the rails came out **sky blue**, reading as
// two painted lines rather than as steel. (The comment here previously
// predicted they would go *black*, from the no-reflection-probe fallback; that
// is what happens with no sky, and this scene has one.) The cue that actually
// works is roughness against the road's 0.95, not metalness.
uniform float rail_metallic : hint_range(0.0, 1.0) = 0.0;

group_uniforms mirror;
// What `rail_metallic` could not give: the car's painted sky (`P3-11c`), which
// the rig dims and warms with the hour (`Q160`), so a rail at dusk catches a
// dusk sky and at night goes dark with it. The three colours are the car's and
// the façades' noon sky, matched by hand so the city agrees about what the sky
// is. A rail lies flat and is seen from above, so its reflected ray always
// points up — `ground_reflection` is here for a rail on a tilted deck.
global uniform vec3 sky_light;
uniform vec3 sky_zenith : source_color = vec3(0.24, 0.47, 0.78);
uniform vec3 sky_horizon : source_color = vec3(0.85, 0.91, 0.96);
uniform vec3 ground_reflection : source_color = vec3(0.32, 0.33, 0.35);
// How much of the mirror a rail head takes at a grazing angle, and how much
// faced squarely. The bed takes none: it is weathered concrete.
uniform float rail_reflect : hint_range(0.0, 1.0) = 0.5;
uniform float rail_face_on : hint_range(0.0, 1.0) = 0.05;
uniform float fresnel_power : hint_range(1.0, 8.0) = 5.0;

group_uniforms wear;
// The head of a rail is polished by traffic and its flanks are not. `UV.x` is a
// fraction across the strip — 0 and 1 on the two edges, 0.5 down the middle —
// so this darkens and roughens the outer part of a rail without needing a
// second material or a texture.
//
// The rail only: `fragment()` multiplies it by `is_rail`, and says why the bed
// is left plain.
uniform float rail_head_fraction : hint_range(0.05, 1.0) = 0.55;
uniform float flank_darkening : hint_range(0.0, 1.0) = 0.35;

// ⚠️ **`flat`, and the ETL invariant behind it is the same one
// `road_markings.gdshader` records.** `tramway.py`'s `_Builder.strip`
// broadcasts one colour over a whole strip, so no triangle of this mesh spans
// two colours and `flat` is exactly equal to converting per fragment rather
// than an approximation of it. If the ETL ever ships per-vertex tramway colour,
// this has to come back down into `fragment`.
varying flat vec3 albedo_linear;
// Which of the two things this fragment is on, from `TEXCOORD_1.x`.
//
// ⚠️ **Shipped rather than derived, and the alternatives are both traps.**
// Inferring it from strip width works today and inverts silently the day
// `rail_width_m` and `bed_width_m` move towards each other; inferring it from
// vertex colour makes the `materials:` table load-bearing for shading rather
// than for colour. `etl/pipeline/tramway.py` carries the constants this must
// match, and `docs/ARCHITECTURE.md` is the tiebreak.
const float TRAMWAY_CLASS_RAIL = 1.0;
varying flat float is_rail;

void vertex() {
	albedo_linear = vertex_srgb_to_linear(COLOR.rgb) * exposure_anchor;
	// `floor(x + 0.5)` first, on the same promise `road_markings.gdshader`
	// decodes under: the field is a small exact integer in float32.
	is_rail = step(TRAMWAY_CLASS_RAIL - 0.5, floor(UV2.x + 0.5));
}

void fragment() {
	// Distance from the middle of the strip, 0 at the centre and 1 at either
	// edge. Everything below is a function of it.
	float across = abs(UV.x - 0.5) * 2.0;

	// The rail's polished head. `smoothstep` rather than a step because at any
	// distance the player is actually looking, a hard edge on a 14 cm strip
	// aliases into a dashed line.
	//
	// Only the rail is shaded across its width. The bed is a plain surface and
	// darkening its edges would draw two soft lines down the reserve that
	// nothing in the source puts there — the invented-marking failure `Q54`
	// records, in a place where it would be much harder to notice.
	float flank = smoothstep(rail_head_fraction, 1.0, across) * is_rail;

	vec3 albedo = albedo_linear * (1.0 - flank * flank_darkening);

	// The mirror, on the head only — a flank is the dull part. The reflected ray
	// is built in view space and turned into the world, so no varying is spent
	// on a strip this thin; `bounced.y` is its elevation, as on the car.
	//
	// Guarded on the bed, which is most of the tramway's fragments and would
	// discard all of it — the car's reason for guarding its glint. `is_rail` is
	// `flat`, so the branch is coherent across a triangle.
	if (is_rail > 0.5) {
		float fresnel = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), fresnel_power);
		vec3 bounced = mat3(INV_VIEW_MATRIX) * reflect(-VIEW, NORMAL);
		vec3 mirrored = mix(
			ground_reflection,
			mix(sky_horizon, sky_zenith, clamp(bounced.y, 0.0, 1.0)),
			smoothstep(-0.08, 0.08, bounced.y)
		) * sky_light;
		float head = 1.0 - flank;
		albedo = mix(albedo, mirrored, head * rail_reflect * mix(rail_face_on, 1.0, fresnel));
	}

	ALBEDO = albedo;
	// ⚠️ **This is the line that makes a rail read as a rail.** Both surfaces
	// are shaded by the same fragment and only `is_rail` separates them; a
	// single roughness here makes the bed as sharp as the rail and the whole
	// reserve reads as a wet strip down the middle of the road.
	ROUGHNESS = mix(bed_roughness, rail_roughness, is_rail);
	METALLIC = rail_metallic * is_rail;
	SPECULAR = 0.5;
}
