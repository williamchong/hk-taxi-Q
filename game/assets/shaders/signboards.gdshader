// The Buildings Department's signboards (`P3-103`, `Q260`): a box in one
// colour whose two faces glow at night.
//
// `vertex_albedo.gdshader` plus one term. The colour rides `COLOR_0` — the
// board's surveyed or palette colour from `etl/pipeline/signboards.py`, a
// printed ground rather than a `materials:` reflectance — and the rig's
// exposure scales it like any surface. The ETL marks a board's two faces with
// `COLOR_0` alpha 0 (`signboards.LIT_ALPHA`, `lamps.py`'s lantern convention);
// those emit their own colour times `face_glow` times the rig's `night_lights`,
// so nothing lights by day (`Q160`).
shader_type spatial;

// `diffuse_burley` and `specular_schlick_ggx` stated for `vertex_albedo`'s
// reason: the language's defaults are not `BaseMaterial3D`'s.
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

#include "res://assets/shaders/colour.gdshaderinc"

global uniform float exposure_anchor;
global uniform float night_lights;

group_uniforms surface;
uniform float roughness_value : hint_range(0.0, 1.0) = 0.6;

group_uniforms night;
// How bright a board's face burns at full night, times its own colour.
uniform float face_glow : hint_range(0.0, 8.0) = 1.5;

// Linearised in the vertex stage, `vertex_albedo`'s reason.
varying vec3 albedo_linear;
varying float lit;

void vertex() {
	albedo_linear = vertex_srgb_to_linear(COLOR.rgb);
	lit = 1.0 - COLOR.a;
}

void fragment() {
	ALBEDO = albedo_linear * exposure_anchor;
	METALLIC = 0.0;
	ROUGHNESS = roughness_value;
	EMISSION = albedo_linear * (face_glow * night_lights * lit);
}
