// The far shore (`P3-100`, `Q249`): `backdrop.glb`'s skyline and the ground it
// stands on, a vertex-coloured surface under the rig's exposure drawn past the
// camera's far plane. `vertex_albedo.gdshader` with one more line, and its own
// file because that one is held to the two props it was graded with.

shader_type spatial;

// The modes `vertex_albedo.gdshader` states, for its reason: a `BaseMaterial3D`
// lights by them and the shader language's defaults are different ones.
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

#include "res://assets/shaders/colour.gdshaderinc"
#include "res://assets/shaders/far_shore.gdshaderinc"

// The rig's exposure (`Q38`): `colour.gdshaderinc` has the account.
global uniform float exposure_anchor;

group_uniforms surface;
uniform float roughness_value : hint_range(0.0, 1.0) = 0.9;

varying vec3 albedo_linear;

void vertex() {
	albedo_linear = vertex_srgb_to_linear(COLOR.rgb);
	POSITION = far_shore_clip(PROJECTION_MATRIX, (MODELVIEW_MATRIX * vec4(VERTEX, 1.0)).xyz);
}

void fragment() {
	ALBEDO = albedo_linear * exposure_anchor;
	METALLIC = 0.0;
	ROUGHNESS = roughness_value;
}
