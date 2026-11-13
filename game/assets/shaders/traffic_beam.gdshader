// The light a moving vehicle's headlamps throw on the road at night (the user's
// ask, 2026-11-13: "all traffic cars not parked in road should have big lamps
// turned on at night so that player can see nearby and incoming traffic also via
// lighting").
//
// ⚠️ **Not a light, for `lamp_pool.gdshader`'s reason.** Forward Mobile pairs 8
// spot lights with an object, a road chunk is one object, and the taxi's own
// beams already ration those eight (`tuning/beams.md`): a fleet of forty would
// light four cars and leave the rest dark. So each vehicle draws a box of air
// ahead of its nose, and this shader lights whatever the depth buffer says is
// standing inside the box's cone — the road, the kerb, the car in front — by
// adding to the frame already drawn. One `MultiMesh` a fleet, so a street of
// beams is one draw (`scripts/traffic/traffic_beams.gd`).
//
// ⚠️ **`cull_front` with the depth test off**, as the pool: the back faces are
// drawn wherever the box covers the screen, so the beam survives the camera
// driving through it, and the fragment decides whether anything is in the light.
//
// ⚠️ **By day the box collapses to a point**, in `vertex()`, and past `draw_m`
// from the camera likewise: a beam nobody can see rasterises nothing.
shader_type spatial;
render_mode unshaded, blend_add, cull_front, depth_test_disabled, depth_draw_never,
		shadows_disabled, fog_disabled;

// The rig's hour (`scripts/world/lighting_rig.gd`): 0 by day, 1 at full night.
global uniform float night_lights;

uniform sampler2D depth_texture : hint_depth_texture, filter_nearest, repeat_disable;
uniform sampler2D screen_texture : hint_screen_texture, filter_nearest, repeat_disable;

group_uniforms beam;
uniform vec3 beam_colour : source_color = vec3(1.0, 0.96, 0.88);
// What the lamp adds back of the surface it lands on, and what it adds whatever
// the surface: `lamp_pool.gdshader`'s pair.
uniform float beam_gain : hint_range(0.0, 16.0) = 4.0;
uniform float beam_floor : hint_range(0.0, 1.0) = 0.04;
// 🔴 The box's own size, read by `traffic_beams.gd` to build the mesh: how far
// ahead the light carries, how wide it opens past the body's own width, how far
// under the lamps it looks for a road, and how far above them it lights.
uniform float reach_m : hint_range(1.0, 60.0) = 24.0;
uniform float spread_deg : hint_range(0.0, 45.0) = 14.0;
uniform float drop_m : hint_range(0.5, 10.0) = 3.0;
uniform float rise_m : hint_range(0.0, 5.0) = 1.2;
// How high the lamps stand over the ground under the body: read by
// `traffic_beams.gd` alone, which stands each box from it.
uniform float lamp_height_m : hint_range(0.2, 2.0) = 0.7;
// Past this from the camera the beam fades out and then is not drawn at all.
uniform float draw_m : hint_range(10.0, 400.0) = 140.0;

// The lamps, in world space: the box's near face, at lamp height.
varying flat vec3 lamps;
varying flat vec3 ahead;
varying flat vec3 across;
varying flat vec3 up;
// Half the vehicle's width, from `INSTANCE_CUSTOM.r`: the beam's width at the glass.
varying flat float half_width;
// How much wider the cone grows a metre ahead, once an instance, not a fragment.
varying flat float opening;
varying flat float shown;

void vertex() {
	// `traffic_beams.gd` builds the box around the lamps: they are the origin.
	lamps = (MODEL_MATRIX * vec4(0.0, 0.0, 0.0, 1.0)).xyz;
	ahead = normalize((MODEL_MATRIX * vec4(0.0, 0.0, -1.0, 0.0)).xyz);
	across = normalize((MODEL_MATRIX * vec4(1.0, 0.0, 0.0, 0.0)).xyz);
	up = normalize((MODEL_MATRIX * vec4(0.0, 1.0, 0.0, 0.0)).xyz);
	half_width = INSTANCE_CUSTOM.r;
	opening = tan(radians(spread_deg));
	float far = length(lamps - CAMERA_POSITION_WORLD);
	shown = night_lights * (1.0 - smoothstep(draw_m * 0.75, draw_m, far));
	if (shown <= 0.0) {
		// Collapsed to a point, as the pool's. ⚠️ Not a write to `POSITION`:
		// naming it switches off the engine's own projection on the lit branch too.
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

	vec3 rel = world - lamps;
	float d = dot(rel, ahead);
	float x = abs(dot(rel, across));
	float h = dot(rel, up);
	// A cone opening from the body's width: soft at its edge, brightest near the
	// glass, nothing behind it, and faded in over the first metre so the
	// vehicle's own bonnet is not lit.
	float width = half_width + max(d, 0.0) * opening;
	float lit = 1.0 - smoothstep(width * 0.55, width, x);
	float fall = clamp(1.0 - d / reach_m, 0.0, 1.0);
	lit *= fall * fall * smoothstep(0.0, 1.0, d);
	// Dipped: the light reaches a little above the lamps far out, so a car
	// ahead is lit to its boot and a wall to its knee, never a façade.
	float top = rise_m * clamp(d / reach_m, 0.0, 1.0) + 0.2;
	lit *= (1.0 - smoothstep(top - 0.25, top + 0.25, h)) * step(-drop_m, h);
	if (lit <= 0.0) {
		discard;
	}
	vec3 surface = textureLod(screen_texture, SCREEN_UV, 0.0).rgb;
	ALBEDO = (surface * beam_gain + beam_floor) * beam_colour * (lit * shown);
}
