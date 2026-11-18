// The signboards' lettering (`P3-103` step 2, `Q260`): a generic shop name,
// one quad a character, cut out of its quad by the atlas.
//
// The atlas is a coverage mask, one cell a character
// (`etl/pipeline/signboard_text.py`), so one image serves every board whatever
// its colour: the ink rides `COLOR_0`, picked by the ETL to stand out from the
// board. An alpha scissor rather than a blend keeps the lettering in the opaque
// pass; a board's characters are metres tall, where `sign_text.py`'s 0.1 m
// glyphs stay opaque (`Q63`). `COLOR_0` alpha 0 is the
// lantern convention: the lettering burns with its board at night (`Q160`).
shader_type spatial;

render_mode cull_back, diffuse_burley, specular_schlick_ggx;

#include "res://assets/shaders/colour.gdshaderinc"

global uniform float exposure_anchor;
global uniform float night_lights;

group_uniforms lettering;
uniform sampler2D glyph_atlas : hint_default_black, filter_linear_mipmap_anisotropic;
uniform float roughness_value : hint_range(0.0, 1.0) = 0.6;
// The coverage under which a texel is not ink.
uniform float cut : hint_range(0.0, 1.0) = 0.5;

group_uniforms night;
// How bright the lettering burns at full night, times its ink.
uniform float ink_glow : hint_range(0.0, 8.0) = 2.0;

varying vec3 ink_linear;
varying float lit;

void vertex() {
	ink_linear = vertex_srgb_to_linear(COLOR.rgb);
	lit = 1.0 - COLOR.a;
}

void fragment() {
	ALBEDO = ink_linear * exposure_anchor;
	ROUGHNESS = roughness_value;
	EMISSION = ink_linear * (ink_glow * night_lights * lit);
	ALPHA = texture(glyph_atlas, UV).r;
	ALPHA_SCISSOR_THRESHOLD = cut;
}
