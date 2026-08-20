// Turn arrows, drawn as their own geometry (`P3-15`, `Q53`).
//
// The simplest shader in the project, and the reason it is simple is the whole
// argument of `P3-15`. `road_markings.gdshader` has to *place* its markings in
// lane space, because it paints a ribbon drawn 1.6x too wide and the paint has
// to survive the widening. This one places nothing: `pipeline/arrows.py` has
// already decided where every vertex goes. There is no codec to decode, no lane
// coordinate to reconstruct, and no junction fade — an arrow is a whole object
// rather than a length of line, so it is either drawn or it is not.
//
// ⚠️ **The colour lives here rather than in `hong_kong.yaml`'s `materials:`
// table, and that is deliberate.** `Q53` put the marking colours in
// `tuning/road_markings.tres`, outside `Q33`'s exposure rule, because paint is
// not cladding — and predicted that "the day a third road colour is authored
// somewhere else" would be the problem. `arrows.tres` is beside
// `road_markings.tres` for exactly that reason: an arrow is the same paint as
// the lane divider it stands between, and the two values have to be able to be
// read side by side.
//
// ⚠️ **`arrows.glb` carries no `COLOR_0`**, so there is no vertex colour to
// convert and `colour.gdshaderinc` is deliberately not included. If the ETL ever
// ships per-vertex arrow colour, this needs `vertex_srgb_to_linear` the way
// every other shader here does — the conversion is never free.
//
// ⚠️ **Opaque, and the first draft was not.** It reached for `ALPHA` to copy
// `road_markings.tres`'s `paint_opacity = 0.85`, which is the wrong reading of
// what that value does: next door the paint is *mixed into the road's own
// albedo* on one opaque surface, so the 0.15 is asphalt showing through the
// paint. Here the arrow is a second surface 15 mm above the road, and the same
// number would be asphalt showing through by transparency — which costs a sorted
// alpha pass, drops the depth prepass, and models thermoplastic as though it
// were tinted glass. Real road paint is opaque. So is this.

shader_type spatial;

// ⚠️ **`cull_back`, so winding decides visibility and the normal attribute does
// not.** `pipeline/arrows.py`'s `_ccw` winds every polygon in the glyph's own
// frame and `_place` maps that frame with a negative determinant, which is what
// turns counter-clockwise there into up-facing here. The tramway shipped 5,111
// of 5,112 triangles facing the ground with everything else correct and simply
// was not in the city, so `arrows.json` publishes `inverted` and it must be 0.
render_mode cull_back;

group_uniforms paint;
// The white `road_markings.tres` paints its lane lines with, authored a second
// time because Godot has no mechanism to share a value between two `.tres`
// files. What holds the two together is that a mismatch is visible in one frame:
// an arrow a different white from the dashes on either side of it is the first
// thing anyone would notice.
uniform vec4 paint_colour : source_color = vec4(0.91, 0.91, 0.87, 1.0);
// Thermoplastic holds a sheen the asphalt around it does not, which is the cue
// that it is paint rather than a lighter patch of road. Against the road's 0.95,
// as `road_markings.tres` sets it.
uniform float paint_roughness : hint_range(0.0, 1.0) = 0.7;

void fragment() {
	ALBEDO = paint_colour.rgb;
	ROUGHNESS = paint_roughness;
}
