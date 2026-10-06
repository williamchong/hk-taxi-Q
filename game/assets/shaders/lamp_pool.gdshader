// The light a street lamp throws on the road (`Q160`, the user's ask: "can the
// street light actually light up the road?").
//
// ⚠️ **Not a light, because the renderer cannot pay for one.** Forward Mobile
// pairs 8 spot lights with an object and a road chunk is one object
// (`tuning/beams.md`); Wan Chai stands 1,077 columns, about sixteen a chunk,
// and the taxis' beams already ration those eight. So each lantern draws a
// cylinder of air under itself instead, and this shader lights whatever the
// depth buffer says is standing inside it — the road, the kerb, a fence, the
// car — by adding to the frame already drawn. One `MultiMesh` a 300 m cell,
// the lamps' own cells (`P3-67`), so a street of pools is one draw.
//
// ⚠️ **`cull_front` with the depth test off, so the pool survives the camera
// driving through it.** The back faces are drawn wherever the cylinder covers
// the screen, in front of the scene or behind it, and the fragment decides
// from the reconstructed position whether anything is in the light.
//
// ⚠️ **By day the cylinder collapses to a point**, in `vertex()`: a pool the
// rig has not lit rasterises nothing, so the daylight frame pays the draw and
// no fill.
shader_type spatial;
render_mode unshaded, blend_add, cull_front, depth_test_disabled, depth_draw_never,
		shadows_disabled, fog_disabled;

// The rig's hour (`scripts/world/lighting_rig.gd`): 0 by day, 1 at full night.
global uniform float night_lights;

uniform sampler2D depth_texture : hint_depth_texture, filter_nearest, repeat_disable;
uniform sampler2D screen_texture : hint_screen_texture, filter_nearest, repeat_disable;

group_uniforms pool;
uniform vec3 pool_colour : source_color = vec3(1.0, 0.86, 0.62);
// How much of what is already on screen the lamp adds back, at the foot of
// the column: a lit surface is its own colour brighter, not a wash of lamp.
uniform float pool_gain : hint_range(0.0, 16.0) = 4.0;
// And a little that does not depend on the surface, so near-black asphalt
// under a lamp still reads as lit.
uniform float pool_floor : hint_range(0.0, 1.0) = 0.02;
// 🔴 The cylinder's own size, read by `lamp_pools.gd` to build the mesh: the
// radius the light reaches on the ground, and how far under the lantern it
// looks for one — past the column's height, so a road that falls away under
// the arm is still inside.
uniform float radius_m : hint_range(1.0, 40.0) = 9.0;
uniform float drop_m : hint_range(1.0, 40.0) = 11.0;

// The lantern, in world space: the top centre of this instance's cylinder.
varying flat vec3 lantern;

void vertex() {
	lantern = (MODEL_MATRIX * vec4(0.0, drop_m * 0.5, 0.0, 1.0)).xyz;
	if (night_lights <= 0.0) {
		// Collapsed to a point: every triangle is degenerate and none is filled.
		// ⚠️ Not a write to `POSITION` — naming it at all switches off the
		// engine's own projection, on the lit branch too, and the pool then
		// draws nowhere at night either.
		VERTEX = vec3(0.0);
	}
}

void fragment() {
	float raw = texture(depth_texture, SCREEN_UV).r;
#if CURRENT_RENDERER == RENDERER_COMPATIBILITY
	raw = raw * 2.0 - 1.0;
#endif
	vec4 view = INV_PROJECTION_MATRIX * vec4(SCREEN_UV * 2.0 - 1.0, raw, 1.0);
	vec3 world = (INV_VIEW_MATRIX * vec4(view.xyz / view.w, 1.0)).xyz;

	float below = lantern.y - world.y;
	float out_m = length(world.xz - lantern.xz);
	// A cone: nothing above the lantern, the full radius only at the ground.
	float reach = radius_m * clamp(below / (drop_m * 0.75), 0.0, 1.0);
	float lit = 1.0 - clamp(out_m / max(reach, 0.001), 0.0, 1.0);
	lit *= lit * step(0.0, below) * (1.0 - smoothstep(drop_m * 0.9, drop_m, below));
	if (lit <= 0.0) {
		discard;
	}
	vec3 surface = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	ALBEDO = (surface * pool_gain + pool_floor) * pool_colour * (lit * night_lights);
}
