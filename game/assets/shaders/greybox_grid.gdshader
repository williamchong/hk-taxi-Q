// The skidpad's ground with a metre grid drawn on it (`P3-52`, the user's ask,
// 2026-09-29).
//
// A flat grey pad gives a driver nothing to read a slide against: no heading
// change, no drift of the tail, no sense of speed. Lines every `grid_m` in
// WORLD XZ — not in UV, so the grid is metres on the ground whatever mesh
// carries it — and a heavier line every `major_every` cells.
//
// ⚠️ **Paint only.** `GreyboxBuilder` puts this on the ground's material and
// nothing else changes: the box, its collider and its lift are the ones the
// skidpad's numbers are measured on. The pad stays a measuring instrument
// (`skidpad.md`); this is the human driver's readout, not the tool's.
//
// The minor grid fades out towards the horizon, where a cell is a few pixels
// and lines at every pixel would shimmer. `diffuse_burley` and
// `specular_schlick_ggx` stated for the same reason `vertex_albedo.gdshader`
// states them: they are `StandardMaterial3D`'s modes, and the ground this
// replaces was a `StandardMaterial3D`.

shader_type spatial;
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

group_uniforms grid;
uniform float grid_m = 5.0;
uniform float major_every = 4.0;
// The ground's flat colour; the lines are it lifted towards white, so the grid
// reads on any layout colour without a second authored value.
uniform vec3 base_colour : source_color = vec3(0.16, 0.17, 0.19);
uniform float line_lift : hint_range(0.0, 1.0) = 0.18;
uniform float major_lift : hint_range(0.0, 1.0) = 0.42;
// Matches `GreyboxBuilder._material`'s roughness, so the ground this replaces
// and the ground this draws are the same surface.
uniform float roughness_value : hint_range(0.0, 1.0) = 0.9;

varying vec3 world_pos;

void vertex() {
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
}

// 1 on a grid line in cell space `p`, 0 off it, anti-aliased over the pixel
// footprint `fw`.
float grid_line(vec2 p, vec2 fw) {
	vec2 d = abs(fract(p - 0.5) - 0.5) / fw;
	return 1.0 - min(min(d.x, d.y), 1.0);
}

void fragment() {
	vec2 p = world_pos.xz / grid_m;
	// One derivative serves both passes: the major grid's is this one over
	// `major_every`, the derivative being linear.
	vec2 fw = fwidth(p);
	// `length(fw)` is cells per pixel: the minor grid is whole at 6 px a cell
	// and gone at 2 px, where it would be noise.
	float minor = grid_line(p, fw) * (1.0 - smoothstep(1.0 / 6.0, 1.0 / 2.0, length(fw)));
	float major = grid_line(p / major_every, fw / major_every);
	vec3 colour = mix(base_colour, mix(base_colour, vec3(1.0), line_lift), minor);
	colour = mix(colour, mix(base_colour, vec3(1.0), major_lift), major);
	ALBEDO = colour;
	METALLIC = 0.0;
	ROUGHNESS = roughness_value;
}
