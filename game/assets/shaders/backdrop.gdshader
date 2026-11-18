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
// 0 by day, 1 at full night (`Q160`): every lit layer multiplies by it.
global uniform float night_lights;

group_uniforms surface;
uniform float roughness_value : hint_range(0.0, 1.0) = 0.9;

group_uniforms night;
// The floodlights at the far shore's level of detail (`Q252`): Wan Chai's
// (`city_facade_clean.gdshaderinc`) without the cones, which are under a
// pixel wide from across the harbour and would shimmer. A lit wall takes one
// wash of `night_spot_colour` on its own colour, `night_spot_strength` at the
// foot dimming to `night_spot_top` of it by `night_spot_reach_m`. Walls only.
// Strength 0 is `Q249`'s dark skyline.
uniform vec3 night_spot_colour : source_color = vec3(1.0, 0.86, 0.66);
uniform float night_spot_strength : hint_range(0.0, 8.0) = 0.0;
// The share of walls lit. The mesh carries no building, so the seed is the
// wall's own plane — its bearing and its offset, constant over the face — and
// the draw is per wall, not per building. From 600 m off a block shows one or
// two walls, so it reads as some buildings lit and some not.
uniform float night_spot_share : hint_range(0.0, 1.0) = 0.6;
// Heights are mPD, read off the world `y`: the shore's slab stands at
// `backdrop.ground_level_m` 4.5, which is noise against the reach.
uniform float night_spot_reach_m : hint_range(2.0, 500.0) = 120.0;
uniform float night_spot_top : hint_range(0.0, 1.0) = 0.3;
// How near vertical a face must be to be lit, as `abs(normal.y)`. Under 1, so
// a roof never passes and leaves no plan bearing to normalise.
uniform float wall_normal_max : hint_range(0.0, 0.9) = 0.3;

varying vec3 albedo_linear;
// The wash on this wall at full height, 0 when it is unlit. Decided per vertex:
// `ColouredBuilder.polygon` gives each face its own vertices and one normal, so
// every corner of a wall reads the same plane and the same draw. `flat` because
// it is a per-face value; a per-fragment decision could split a wall along the line
// where float rounding can carry its offset across a metre.
varying flat float wall_lit;
// Height over the reach, 0 to 1: linear in `y`, so it interpolates exactly.
varying float climb;

void vertex() {
	albedo_linear = vertex_srgb_to_linear(COLOR.rgb);
	wall_lit = 0.0;
	climb = 0.0;
	// Uniforms decide the branch, so by day it is coherent and free.
	if (night_lights > 0.0 && night_spot_strength > 0.0) {
		vec3 normal = normalize(MODEL_NORMAL_MATRIX * NORMAL);
		if (abs(normal.y) < wall_normal_max) {
			vec3 world = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
			// The wall's plane: its bearing to the degree and its offset to the
			// metre, both constant over a flat face. Reduced before the hash so
			// `sin`'s argument stays under about 10k, where mobile keeps it.
			vec2 outward = normalize(normal.xz);
			float bearing = floor(degrees(atan(outward.y, outward.x)) + 180.5);
			float offset = mod(floor(dot(outward, world.xz) + 0.5), 97.0);
			float drawn = fract(sin(bearing * 12.9898 + offset * 78.233) * 43758.5453);
			wall_lit = step(drawn, night_spot_share - 1e-6) * night_spot_strength * night_lights;
			climb = clamp(world.y / night_spot_reach_m, 0.0, 1.0);
		}
	}
	POSITION = far_shore_clip(PROJECTION_MATRIX, (MODELVIEW_MATRIX * vec4(VERTEX, 1.0)).xyz);
}

void fragment() {
	vec3 albedo = albedo_linear * exposure_anchor;
	ALBEDO = albedo;
	METALLIC = 0.0;
	ROUGHNESS = roughness_value;
	if (wall_lit > 0.0) {
		EMISSION = albedo * night_spot_colour * (wall_lit * mix(1.0, night_spot_top, climb));
	}
}
