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
// of it — shorter, and lower by the same ratio, so both trains have the same
// steepness — turned `wave_cross_deg` off the first, so the two never line
// up into one stripe.
uniform float wave_length_m : hint_range(0.5, 50.0) = 6.0;
uniform float wave_ratio : hint_range(0.2, 1.0) = 0.6;
uniform float wave_cross_deg : hint_range(0.0, 180.0) = 53.0;
// Crests passing a point per second, and the second train's share of it,
// run the other way.
uniform float wave_speed_hz : hint_range(0.0, 3.0) = 0.25;
uniform float wave_speed_ratio : hint_range(0.0, 2.0) = 0.7;
// How far the shading normal tilts: the slope of the wave, rise over run.
uniform float wave_slope : hint_range(0.0, 1.0) = 0.12;
// How much a crest brightens the albedo, as a share of it.
uniform float crest_lift : hint_range(0.0, 1.0) = 0.12;
// Compass bearing of the first train's travel, degrees; the second crosses it.
uniform float wave_bearing_deg : hint_range(0.0, 360.0) = 20.0;

// 🔴 **Everything that is the same for every pixel is computed per VERTEX**, and
// the plane is 213 triangles under a fragment count that can be most of the
// frame: the bearing's trig, the wave numbers, the phase and the tilt
// directions are per draw, and a driver cannot be relied on to hoist them.
// `wave_a` and `wave_b` are affine in world position, so interpolating them is
// exact — they replace a world-position varying outright. The tilts are baked
// into VIEW space here because `NORMAL` in `fragment()` is view space: a
// world normal would need `VIEW_MATRIX` per pixel, and it is a rigid rotation,
// so rotating the two directions once is the same normal. `flat`, because they
// are the same at every corner. `albedo` folds the exposure in, as
// `tramway.gdshader` does — still after `vertex_srgb_to_linear`, which is the
// order that matters.
varying flat vec3 albedo;
varying flat vec3 up_view;
varying flat vec3 tilt_a;
varying flat vec3 tilt_b;
varying float wave_a;
varying float wave_b;

void vertex() {
	albedo = vertex_srgb_to_linear(COLOR.rgb) * exposure_anchor;
	float bearing = radians(wave_bearing_deg);
	vec2 first = vec2(sin(bearing), -cos(bearing));
	float cross = radians(wave_cross_deg);
	vec2 second = vec2(
		first.x * cos(cross) - first.y * sin(cross), first.x * sin(cross) + first.y * cos(cross)
	);
	float k = TAU / wave_length_m;
	// `fract` keeps the argument small over a session: `TIME` wraps at the
	// project's rollover, and a whole cycle a wrap is what makes that seamless.
	float phase = fract(TIME * wave_speed_hz) * TAU;
	// World plan metres, so the pattern is anchored to the harbour and not to
	// the region node or the camera. North is -Z (`crs.py`).
	vec2 plan = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xz;
	wave_a = dot(plan, first) * k - phase;
	wave_b = dot(plan, second) * k / wave_ratio + phase * wave_speed_ratio;
	// The height field is `slope / k * (sin(a) + ratio * sin(b))`: the second
	// train is shorter by `ratio` and lower by `ratio`, so its gradient
	// `(k / ratio) * ratio * cos(b)` carries the same `slope` as the first —
	// the normal leans `slope` back from each crest whichever train it is on.
	mat3 view = mat3(VIEW_MATRIX);
	up_view = view[1];
	tilt_a = view * vec3(-first.x, 0.0, -first.y) * wave_slope;
	tilt_b = view * vec3(-second.x, 0.0, -second.y) * wave_slope;
}

void fragment() {
	NORMAL = normalize(up_view + tilt_a * cos(wave_a) + tilt_b * cos(wave_b));
	// `0.5 * lift * sin(a) * sin(b)` is `lift * (crest - 0.5)` for a crest of
	// `0.5 + 0.5 * sin(a) * sin(b)`: a crest is `lift / 2` lighter, a trough darker.
	ALBEDO = albedo * (1.0 + 0.5 * crest_lift * sin(wave_a) * sin(wave_b));
	METALLIC = 0.0;
	ROUGHNESS = roughness_value;
}
