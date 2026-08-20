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

group_uniforms wear;
// The head of a rail is polished by traffic and its flanks are not. `UV.x` is a
// fraction across the strip — 0 and 1 on the two edges, 0.5 down the middle —
// so this darkens and roughens the outer part of a rail without needing a
// second material or a texture.
//
// It is applied to the bed as well, and it does something different there: a
// track bed is worn most where the wheels run, and the bed's own UV puts that
// at its edges rather than its middle. So `flank_wear` narrows the rail and
// widens the bed, which is why the two are separate uniforms rather than one.
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
	albedo_linear = vertex_srgb_to_linear(COLOR.rgb);
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

	ALBEDO = albedo_linear * (1.0 - flank * flank_darkening);
	// ⚠️ **This is the line that makes a rail read as a rail.** Both surfaces
	// are shaded by the same fragment and only `is_rail` separates them; a
	// single roughness here makes the bed as sharp as the rail and the whole
	// reserve reads as a wet strip down the middle of the road.
	ROUGHNESS = mix(bed_roughness, rail_roughness, is_rail);
	METALLIC = rail_metallic * is_rail;
	SPECULAR = 0.5;
}
