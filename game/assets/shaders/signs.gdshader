// Traffic signs, drawn as their own geometry (`P3-16`).
//
// Simple for `arrows.gdshader`'s reason — `pipeline/signs.py` has already decided
// where every vertex goes, so there is nothing to place — with one difference
// that runs the other way.
//
// ⚠️ **This one DOES read `COLOR_0`, and `arrows.gdshader` deliberately does
// not.** An arrow is one paint, so its colour is authored next door in
// `road_markings.tres` where the two can be read side by side. A sign plate is
// up to four colours — red ring, white field, black glyph, grey back — and the
// whole region's signs are **one draw call**, so the colour has to travel on the
// vertex. `hong_kong.yaml`'s `signs.colours` is where it is authored, because a
// sign's livery is a *city* fact (hard rule 3) rather than an art call: TD prints
// those colours, and a second city prints its own.
//
// ⚠️ **So `colour.gdshaderinc` is mandatory here, exactly as `arrows.gdshader`
// warned.** That file says: *"If the ETL ever ships per-vertex arrow colour, this
// needs `vertex_srgb_to_linear` the way every other shader here does — the
// conversion is never free."* This is the shader that shipped per-vertex colour.
// `Q27` measured what skipping it costs: sRGB read as linear adds
// albedo-independent brightness, and a NO ENTRY red would arrive pale and
// washed-out rather than obviously wrong.
//
// ⚠️ **Opaque, and there is no opacity dial** — the same refusal `railings.tres`
// records. A sign plate is painted aluminium. An `ALPHA` uniform here would
// repeat `arrows.gdshader`'s recorded misreading of `paint_opacity`, which cost a
// sorted alpha pass to model thermoplastic as tinted glass.

shader_type spatial;

#include "res://assets/shaders/colour.gdshaderinc"

// ⚠️ **`cull_back`, so winding decides visibility and the normal attribute does
// not** — and this is the opposite call from `railings.gdshader`, which is the
// bundle's only `cull_disabled` mesh. `Q61` made it so because a fence is one
// quad thick and has no back. A sign **does** have a back: `pipeline/signs.py`
// draws every plate twice, the face forward and a grey reverse behind it, so
// culling is free and correct. `signs.json` publishes `facing_away` and it must
// be 0 — the first build read 3,200, every pole triangle in the region, because
// the prism ring was wound the plate's way round.
render_mode cull_back;

group_uniforms plate;
// Painted aluminium holds more sheen than thermoplastic on asphalt and much less
// than the galvanised steel of `railings.tres`. Signs are the one street object
// the player is meant to read at speed, so this stays low enough that a red disc
// does not blow out under the golden-hour rig.
uniform float plate_roughness : hint_range(0.0, 1.0) = 0.55;
// A sign face is retroreflective sheeting, which reads as *slightly* self-lit at
// dusk rather than as a flat paint chip. Kept small on purpose: this is a cue,
// not an emissive sign, and pushing it turns every NO ENTRY into a lamp.
uniform float sheeting_glow : hint_range(0.0, 1.0) = 0.06;

void fragment() {
	vec3 albedo_linear = vertex_srgb_to_linear(COLOR.rgb);
	ALBEDO = albedo_linear;
	ROUGHNESS = plate_roughness;
	// Tinted by the plate's own colour rather than added white, so the glow
	// cannot desaturate the livery it is meant to lift.
	EMISSION = albedo_linear * sheeting_glow;
}
