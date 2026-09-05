// The lettering on a sign plate (`P3-20`) — and the only shader in this bundle
// that samples a texture.
//
// 🔴 **`Texture memory` stops being 0 here, and `Q63` is why that is allowed.**
// `mesh_contract.gd` used to fail any shader uniform holding a `Texture`. It now
// fails one whose call site declares no pixel budget, fails a declared texture
// that overruns its budget, and — the half that matters most — fails a declared
// texture that never *arrives*. That last case is this shader's specific hazard:
// a missing sampler reads white, `COLOR_0` still reaches the pixel, and every
// other check passes while the city renders exactly as it did before the atlas
// existed. `verify_signs.gd` is what refuses to let that be silent.
//
// ⚠️ **THERE IS NO ALPHA HERE AND THERE MUST NOT BE ONE.** The atlas is opaque
// RGB: `pipeline/sign_text.py` bakes the glyph's colour over the *plate's own
// field colour*, so the quad sits inside the white triangle it matches and its
// edges are invisible without any blending at all. The two alternatives were a
// coverage mask read into `ALPHA` and a `discard` cutout, and both were refused
// — one puts the sign layer into a transparency pass for a glyph a few pixels
// tall, the other thins the strokes away as the mip chain runs. Either would
// also have made `ALPHA` a dial on a mesh whose sibling `signs.gdshader` records
// that it must not have one, which is `marking_paint.gdshader`'s misreading of
// `paint_opacity` waiting to happen a third time.
//
// ⚠️ **`source_color` on the sampler is doing the `Q27` conversion**, and it is
// the reason there is no `vertex_srgb_to_linear` call on the texture path. The
// ETL writes the atlas in sRGB like every other colour it emits; the hint makes
// the hardware decode it. `COLOR_0` still needs the function, because Godot has
// no such render mode for vertex colour — which is the whole reason
// `colour.gdshaderinc` exists.

shader_type spatial;

#include "res://assets/shaders/colour.gdshaderinc"

// ⚠️ **`cull_back` like `signs.gdshader`, so winding decides visibility.** A
// lettering quad is one-sided and sits `layer_lift_m` in front of the plate's
// face, so there is nothing behind it to see; and `signs.json` publishes
// `text_facing_away`, which must be 0. A quad wound the wrong way here is not a
// word written backwards — it is no word at all, which is the failure this whole
// layer cannot see in a frame.
render_mode cull_back;

group_uniforms lettering;
// The baked atlas, arriving on the glTF material and rewired onto this shader by
// `tools/generated_scene_import.gd`. ⚠️ **Its size is the declared budget** —
// `generated_layer.gd` names the number and `signs.json` publishes what shipped.
uniform sampler2D glyph_atlas : source_color, filter_linear_mipmap_anisotropic;
// The same two surface numbers as `signs.tres`, because this quad is the same
// painted aluminium as the plate a millimetre behind it. Split from that file
// rather than shared so the two cannot silently drift apart in one direction:
// a plate and its own lettering catching the light differently is exactly the
// kind of wrong that reads as a rendering bug rather than as a data one.
uniform float plate_roughness : hint_range(0.0, 1.0) = 0.55;
uniform float sheeting_glow : hint_range(0.0, 1.0) = 0.06;

void fragment() {
	// ⚠️ **Multiplied, not replaced.** `COLOR_0` on this mesh is white, which is
	// the identity — so the product is the atlas exactly. It is written this way
	// so that a bundle whose texture went missing renders the *vertex* colour
	// rather than a hard-coded one, which is the state `check_shader_material`
	// is written against and the state a reader should be able to reach.
	vec3 lettering = texture(glyph_atlas, UV).rgb * vertex_srgb_to_linear(COLOR.rgb);
	ALBEDO = lettering;
	ROUGHNESS = plate_roughness;
	EMISSION = lettering * sheeting_glow;
}
