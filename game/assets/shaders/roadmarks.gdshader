// Stop lines and give-way lines, drawn as their own geometry (`P3-23`, `Q53`).
//
// `arrows.gdshader` with a fifth copy of the white, and the sameness is the
// argument: `pipeline/roadmarks.py` has already decided where every vertex
// goes, so there is nothing to place, no codec to decode and no junction fade.
//
// ⚠️ **The fade is the reason this mesh exists at all, and it bites harder here
// than it did for arrows.** `road_markings.tres` carries `fade_m = 6.0`, priced
// against the measured junction cap overlap, and `ARCHITECTURE.md` records that
// it "blanks exactly the approach an arrow is about". A stop line does not
// merely approach the junction — it *is* the junction's edge, drawn on the cap,
// inside the fade and on top of the 6,051 m² overlap. Painted on the ribbon it
// would be invisible by construction.
//
// ⚠️ **The dashes of a give-way line are geometry, not a procedural pattern**,
// for `boxjunctions.gdshader`'s stated reason: a shader-dashed line would have
// to show asphalt between the marks, and this surface floats 16 mm above the
// road — there is no albedo underneath a fragment to mix into. The two exits
// are alpha blend (a sorted transparent pass; see below) and alpha scissor
// (re-aliases every dash end). So the marks are quads and this shader paints
// everything it is given. The 600/300 module is in `hong_kong.yaml`, off TD's
// own sheet, and never in here.
//
// ⚠️ **`roadmarks.glb` carries no `COLOR_0`**, so there is no vertex colour to
// convert and `colour.gdshaderinc` is deliberately not included.
//
// ⚠️ **Opaque**, for `arrows.gdshader`'s recorded reason: real road paint is
// opaque, and a lifted second surface given `ALPHA` models thermoplastic as
// tinted glass while dropping the depth prepass.

shader_type spatial;

// ⚠️ **`cull_back`, so winding decides visibility and the normal attribute does
// not.** `pipeline/roadmarks.py` winds every quad to face `+Y` and
// `roadmarks.json` publishes `inverted`, which must be 0 — the tramway shipped
// 5,111 of 5,112 triangles facing the ground with everything else correct and
// simply was not in the city.
render_mode cull_back;

group_uniforms paint;
// The white `road_markings.tres` paints its lane lines with — the **fifth**
// copy of the value, because Godot has no mechanism to share one between a
// shader and a `.tres`, or between two `.tres`. What holds them together is
// that a mismatch is visible in one frame, and this one is the most exposed of
// the set: a stop line meets the lane dividers of its own approach end-on, so a
// different white reads as a different marking rather than as a shade.
//
//   road_markings.gdshader  line_colour  (default)
//   road_markings.tres      line_colour
//   arrows.gdshader         paint_colour (default)
//   arrows.tres             paint_colour
//   — all four Color(0.91, 0.91, 0.87), and `roadmarks.tres` is the sixth
uniform vec4 paint_colour : source_color = vec4(0.91, 0.91, 0.87, 1.0);
// Thermoplastic holds a sheen the asphalt around it does not. Against the
// road's 0.95, as `road_markings.tres`, `arrows.tres` and `boxjunctions.tres`
// all set it.
uniform float paint_roughness : hint_range(0.0, 1.0) = 0.7;

void fragment() {
	ALBEDO = paint_colour.rgb;
	ROUGHNESS = paint_roughness;
}
