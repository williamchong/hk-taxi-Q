// An ink line round the city, drawn over the frame from the depth buffer
// (`P3-64`, `Q158`, the user's ask: a cel look for the buildings).
//
// ⚠️ **Why a pass over the frame and not a hull per mesh.** The classic outline
// is a second, inflated, front-culled copy of every mesh. The city sits at
// 136–150 draw calls against a budget of 150 (`PROGRESS.md`), and a hull is a
// second draw of every tile and a second pass over its triangles. This is one
// full-screen quad — one draw call, whatever the frame holds.
//
// ⚠️ **Depth only, because the Mobile renderer has no normal buffer**
// (`hint_normal_roughness_texture` is Forward+). Two faces meeting at a crease
// sit at the same depth along the crease, so a first difference of depth cannot
// see them. A second difference can: the edge test is the Laplacian of
// INVERSE depth, which is exactly zero across any plane — `1/z` is linear in
// screen space under a perspective projection, however steeply the plane is
// seen — and non-zero only where the surface folds (a crease) or breaks (a
// silhouette). Linear depth would put a false edge on every grazing road.
//
// The test is scaled by the centre pixel's own inverse depth, so a threshold
// is a ratio and means the same thing at 5 m and at 200 m.
//
// Every number is a uniform read from `tuning/cel_outline.tres` (CLAUDE.md hard
// rule 4). The quad is `CelOutline` in both rig scenes, so it inks every scene
// the rig lights; hiding it is the off switch.
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, depth_test_disabled, cull_disabled,
		fog_disabled, shadows_disabled;

uniform sampler2D depth_texture : hint_depth_texture, filter_nearest, repeat_disable;
uniform sampler2D screen_texture : hint_screen_texture, filter_nearest, repeat_disable;

group_uniforms ink;
uniform vec3 ink_colour : source_color = vec3(0.08, 0.08, 0.1);
// How much of the line is the surface's own colour, darkened, rather than
// `ink_colour`: 0 is flat ink, 1 is each building outlined in its own hue
// (the user's ask, 2026-10-07). The colour is read from the NEARER side of
// the edge, so a tower's silhouette is drawn in the tower's hue and not the
// sky's or the building behind it.
uniform float ink_from_surface : hint_range(0.0, 1.0) = 1.0;
// The surface colour's scale in linear light: 0.35 keeps the hue and drops
// the value by about half in L*.
uniform float surface_darkness : hint_range(0.0, 1.0) = 0.5;
// 1.0 draws the ink opaque; under it the line is a darkening.
uniform float ink_strength : hint_range(0.0, 1.0) = 1.0;
// How far apart the samples sit. The line is about twice this wide, because
// both the near and the far pixel of a break test positive.
uniform float line_width_px : hint_range(0.5, 4.0) = 1.0;

group_uniforms edge;
// The Laplacian ratio where the ink starts and where it is full. A crease
// between two walls reads in the thousandths; a silhouette against a building
// behind it reads in the tenths. `edge_start` must stay under `edge_full`.
uniform float edge_start : hint_range(0.0, 0.5) = 0.004;
uniform float edge_full : hint_range(0.0, 1.0) = 0.03;
// Both bars rise by one more of themselves every this many metres of
// distance. The depth buffer rounds, and on a plane seen at a grazing angle
// far off — the harbour — the rounding alone reads as a Laplacian in rows of
// stripes, growing with distance. 0 holds the bars flat.
uniform float edge_distance_m : hint_range(0.0, 500.0) = 40.0;

group_uniforms distance;
// The ink fades out with the distance of the nearer side of the edge, so the
// skyline is not drawn as a scribble and the line goes before the LOD1 switch
// (`tuning/streaming.tres`, 250 m) moves the geometry it traces.
uniform float fade_start_m : hint_range(0.0, 1000.0) = 120.0;
uniform float fade_end_m : hint_range(0.0, 1000.0) = 240.0;

void vertex() {
	// A 2 x 2 quad straight to clip space. z = 1 is the near plane under the
	// Mobile renderer's reverse Z and the far one under Compatibility's; either
	// draws, because the pass neither tests nor writes depth.
	POSITION = vec4(VERTEX.xy, 1.0, 1.0);
}

// The raw depth as normalised device z: Vulkan's [0, 1] as stored, OpenGL's
// [-1, 1] stretched from it.
float ndc_z(vec2 uv) {
	float raw = texture(depth_texture, uv).r;
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	return raw * 2.0 - 1.0;
#else
	return raw;
#endif
}

void fragment() {
	// Inverse view depth is a straight line in NDC z under a perspective
	// projection: unprojected, view z is the matrix's constant `[3][2]` and view
	// w is `[2][3] * z + [3][3]`. So the Laplacian is a sum of five taps and one
	// slope, with no per-tap unprojection — and no per-tap rounding either.
	mat4 inv = INV_PROJECTION_MATRIX;
	float slope = -inv[2][3] / inv[3][2];
	float offset = -inv[3][3] / inv[3][2];

	vec2 step_uv = line_width_px / VIEWPORT_SIZE;
	float centre = ndc_z(SCREEN_UV);
	float left = ndc_z(SCREEN_UV - vec2(step_uv.x, 0.0));
	float right = ndc_z(SCREEN_UV + vec2(step_uv.x, 0.0));
	float down = ndc_z(SCREEN_UV - vec2(0.0, step_uv.y));
	float up = ndc_z(SCREEN_UV + vec2(0.0, step_uv.y));

	float inv_centre = slope * centre + offset;
	float laplacian = slope * (left + right + down + up - 4.0 * centre);
	// The nearest of the five has the largest inverse depth, under either Z;
	// its UV is where the surface colour is read.
	float inv_nearest = inv_centre;
	vec2 near_uv = SCREEN_UV;
	vec4 taps[4] = {
		vec4(left, -step_uv.x, 0.0, 0.0), vec4(right, step_uv.x, 0.0, 0.0),
		vec4(down, 0.0, -step_uv.y, 0.0), vec4(up, 0.0, step_uv.y, 0.0)
	};
	for (int i = 0; i < 4; i++) {
		float inv_tap = slope * taps[i].x + offset;
		if (inv_tap > inv_nearest) {
			inv_nearest = inv_tap;
			near_uv = SCREEN_UV + taps[i].yz;
		}
	}
	float nearest = 1.0 / inv_nearest;

	float rise = edge_distance_m > 0.0 ? 1.0 + nearest / edge_distance_m : 1.0;
	float edge = smoothstep(edge_start * rise, edge_full * rise, abs(laplacian) / inv_centre);
	edge *= 1.0 - smoothstep(fade_start_m, fade_end_m, nearest);

	vec3 surface = texture(screen_texture, near_uv).rgb * surface_darkness;
	ALBEDO = mix(ink_colour, surface, ink_from_surface);
	ALPHA = edge * ink_strength;
}
