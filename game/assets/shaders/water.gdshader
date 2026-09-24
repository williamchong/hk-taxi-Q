// The harbour's water: a vertex-coloured plane under the rig's exposure, with
// waves faked in the fragment (2026-09-25, the user's call).
//
// The plane is 213 triangles a region at `basemap.simplify_m`, so there is no
// vertex to displace and no texture to scroll — the bundle carries none (`Q63`,
// `mesh_contract.gd` refuses an undeclared image). The trick is procedural: two
// crossed sine wave trains in world plan, moved by `TIME`, tilt the shading
// NORMAL per pixel so the sky's reflection breaks into moving bands, and their
// product lifts the albedo a little on the crests. Every number is a uniform
// read from `tuning/water.tres` (CLAUDE.md hard rule 4); the shader carries no
// look of its own.
//
// Started from `vertex_albedo.gdshader` and deliberately NOT a change to it: that
// file's header forbids growing it, because the two props that share it are
// graded against a shipped frame. This is the water's own shader for the same
// reason `tramway.gdshader` is the rail's.
//
// `cull_back`: the plane faces the sky and is never seen from beneath on purpose.
// `diffuse_burley` and `specular_schlick_ggx` stated for `vertex_albedo.gdshader`'s
// reason — the language defaults are not `BaseMaterial3D`'s.
shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

#include "res://assets/shaders/colour.gdshaderinc"

// The rig's exposure (`Q38`), multiplied in after `vertex_srgb_to_linear` and
// nowhere else — `vertex_albedo.gdshader`'s paragraph.
global uniform float exposure_anchor;

group_uniforms surface;
uniform float roughness_value : hint_range(0.0, 1.0) = 0.45;

group_uniforms waves;
// Crest-to-crest of the first train, metres. The second runs at `wave_ratio`
// of it across the first, so the two never line up into one stripe.
uniform float wave_length_m : hint_range(0.5, 50.0) = 6.0;
uniform float wave_ratio : hint_range(0.2, 1.0) = 0.6;
// Crests passing a point per second.
uniform float wave_speed_hz : hint_range(0.0, 3.0) = 0.25;
// How far the shading normal tilts: the slope of the wave, rise over run.
uniform float wave_slope : hint_range(0.0, 1.0) = 0.12;
// How much a crest brightens the albedo, as a share of it.
uniform float crest_lift : hint_range(0.0, 1.0) = 0.12;
// Compass bearing of the first train's travel, degrees; the second crosses it.
uniform float wave_bearing_deg : hint_range(0.0, 360.0) = 20.0;

varying vec3 albedo_linear;
varying vec2 plan;

void vertex() {
	albedo_linear = vertex_srgb_to_linear(COLOR.rgb);
	// World plan metres, so the pattern is anchored to the harbour and not to
	// the region node or the camera. North is -Z (`crs.py`).
	plan = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
}

void fragment() {
	float bearing = radians(wave_bearing_deg);
	vec2 first = vec2(sin(bearing), -cos(bearing));
	vec2 second = vec2(-first.y, first.x) * 0.8 + first * 0.6;
	float k = TAU / wave_length_m;
	float phase = TIME * wave_speed_hz * TAU;
	float a = dot(plan, first) * k - phase;
	float b = dot(plan, second) * k / wave_ratio + phase * 0.7;
	// The height field is sin(a) + sin(b) scaled; its plan gradient is the
	// slope the normal leans back from.
	vec2 slope = (first * cos(a) + second * cos(b) * wave_ratio) * wave_slope;
	vec3 world_normal = normalize(vec3(-slope.x, 1.0, -slope.y));
	NORMAL = normalize((VIEW_MATRIX * vec4(world_normal, 0.0)).xyz);
	float crest = 0.5 + 0.5 * sin(a) * sin(b);
	ALBEDO = albedo_linear * exposure_anchor * (1.0 + crest_lift * (crest - 0.5));
	METALLIC = 0.0;
	ROUGHNESS = roughness_value;
}
