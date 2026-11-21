// The signboards' neon (`P3-103`, `Q260`): a glowing tube round a board's lit
// face, in the board's own hue, drawn at night only.
//
// One quad over the face (`signboards.neon`), its UVs metres from the face's
// centre, so a vertex's `abs(UV)` is the face's half-size and the tube is a
// rounded rectangle `tube_inset_m` in from the rim, `tube_width_m` across, on a
// 1 m board and a 30 m one alike. The rest of the quad is cut away, so the
// board's own face, colour and glow show through it unchanged.
//
// The hue is `COLOR_0` (the board's colour), its chroma pushed by `saturation`
// and scaled until its brightest channel is 1: most surveyed boards are muted,
// and a muted hue at neon brightness reads white, not the board's colour. It
// emits that times `neon_glow` times the rig's `night_lights`, at the glow
// pass's threshold so the tube blooms. Its albedo is the board's own, so the
// tube that appears as `night_lights` leaves 0 at dusk matches the face and
// glows in from there; by day the whole quad is cut away (`Q160`).
shader_type spatial;

render_mode cull_back, diffuse_burley, specular_schlick_ggx;

#include "res://assets/shaders/colour.gdshaderinc"

global uniform float exposure_anchor;
global uniform float night_lights;

group_uniforms tube;
// How far in from the face's rim the tube's centre runs, and how wide it is.
// A board too small for the inset takes a quarter of its shorter half-side.
uniform float tube_inset_m : hint_range(0.0, 1.0) = 0.15;
uniform float tube_width_m : hint_range(0.01, 0.5) = 0.06;
// The radius the tube bends round a corner.
uniform float corner_m : hint_range(0.0, 1.0) = 0.2;
uniform float roughness_value : hint_range(0.0, 1.0) = 0.3;

// How far the board's colour is pushed from grey for the tube; 1 is as it is.
uniform float saturation : hint_range(1.0, 8.0) = 1.0;

group_uniforms night;
// How bright the tube burns at full night, times its hue.
uniform float neon_glow : hint_range(0.0, 16.0) = 4.0;

// Every vertex of a face carries the same `abs(UV)` and colour.
varying flat vec2 half_size;
varying flat vec3 albedo_linear;
varying flat vec3 hue;

void vertex() {
	half_size = abs(UV);
	albedo_linear = vertex_srgb_to_linear(COLOR.rgb);
	float grey = dot(albedo_linear, vec3(0.2126, 0.7152, 0.0722));
	vec3 pushed = max(mix(vec3(grey), albedo_linear, saturation), vec3(0.0));
	hue = pushed / max(max(pushed.r, pushed.g), max(pushed.b, 1e-4));
}

void fragment() {
	float inset = min(tube_inset_m, 0.25 * min(half_size.x, half_size.y));
	vec2 inner = max(half_size - inset, vec2(0.0));
	float radius = min(corner_m, min(inner.x, inner.y));
	vec2 q = abs(UV) - (inner - radius);
	// Signed metres from the tube's centre line.
	float sdf = length(max(q, vec2(0.0))) + min(max(q.x, q.y), 0.0) - radius;
	// Never thinner than a pixel, so a far tube thins to a line, not to gaps.
	float half_width = max(0.5 * tube_width_m, fwidth(sdf));
	ALBEDO = albedo_linear * exposure_anchor;
	METALLIC = 0.0;
	ROUGHNESS = roughness_value;
	EMISSION = hue * (neon_glow * night_lights);
	ALPHA = step(abs(sdf), half_width) * step(1e-3, night_lights);
	ALPHA_SCISSOR_THRESHOLD = 0.5;
}
