// Yellow box junctions, drawn as their own geometry (`P3-18`, `Q53`).
//
// `arrows.gdshader` with the yellow, and the sameness is the argument: the
// mesh's every vertex is already where `pipeline/boxjunctions.py` decided,
// so there is nothing to place, no codec to decode, and no junction fade —
// the box *is* the junction marking, drawn over the cap the ribbon markings
// fade away from.
//
// ⚠️ **The hatch is geometry, not a procedural stripe field, and opacity is
// why.** A shader-hatched fill would have to show asphalt between the stripes,
// and this surface floats 12 mm above the road — there is no albedo underneath
// a fragment to mix into. The two exits are alpha blend (a sorted transparent
// pass; `arrows.gdshader` records why paint is opaque) or alpha scissor
// (re-aliases every stripe edge). So the stripes are triangles and this shader
// paints everything it is given.
//
// ⚠️ **`boxjunctions.glb` carries no `COLOR_0`**, so there is no vertex colour
// to convert and `colour.gdshaderinc` is deliberately not included.
//
// ⚠️ **Opaque**, for `arrows.gdshader`'s stated reason: real road paint is
// opaque, and a lifted second surface given `ALPHA` models thermoplastic as
// tinted glass while dropping the depth prepass.

shader_type spatial;

// ⚠️ **`cull_back`, so winding decides visibility and the normal attribute does
// not.** `pipeline/boxjunctions.py` winds every polygon to face `+Y` and
// `boxjunctions.json` publishes `inverted`, which must be 0 — the tramway
// shipped 5,111 of 5,112 triangles facing the ground and simply was not in the
// city.
render_mode cull_back;

group_uniforms paint;
// The yellow `road_markings.tres` paints its kerbside restrictions with,
// authored a third time because Godot has no mechanism to share a value
// between `.tres` files. What holds the copies together is that a mismatch is
// visible in one frame: a box a different yellow from the no-stopping line at
// its own kerb is the first thing anyone would notice.
uniform vec4 paint_colour : source_color = vec4(0.86, 0.68, 0.13, 1.0);
// Thermoplastic holds a sheen the asphalt around it does not. Against the
// road's 0.95, as `road_markings.tres` and `arrows.tres` both set it.
uniform float paint_roughness : hint_range(0.0, 1.0) = 0.7;

void fragment() {
	ALBEDO = paint_colour.rgb;
	ROUGHNESS = paint_roughness;
}
