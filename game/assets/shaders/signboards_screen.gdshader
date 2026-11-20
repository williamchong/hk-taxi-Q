// The signboards' screens (`P3-103` step 3, `Q260`): an LED face playing a
// generic, unbranded loop. No texture and no brand: a field of colour that
// drifts, cut to a slide every `slide_s`, seen through an LED dot grid.
//
// UV is metres across and down the face (`signboards.screen`), so the LED
// pitch is the same on a 12 m screen and a 73 m one. `COLOR_0`'s red is a seed
// from the board's id, so two screens do not show the same frame. A screen is
// lit by day as well as by night: it is a light, not paint, so it emits
// `day_glow` under the sun and `night_glow` at night (`Q160`'s rig).
shader_type spatial;

render_mode cull_back, diffuse_burley, specular_schlick_ggx;

global uniform float night_lights;

group_uniforms screen;
// The LED pitch, in metres.
uniform float pixel_m : hint_range(0.05, 2.0) = 0.3;
// How fast the field drifts, and how long a slide holds.
uniform float drift : hint_range(0.0, 2.0) = 0.25;
uniform float slide_s : hint_range(1.0, 60.0) = 7.0;
// The dark between LEDs, where they are drawn large enough to see.
uniform float gap_dark : hint_range(0.0, 1.0) = 0.45;
uniform float day_glow : hint_range(0.0, 8.0) = 1.2;
uniform float night_glow : hint_range(0.0, 8.0) = 2.2;
// On, the screen shows `plain_colour` and nothing moves; the loop stays for
// when it is switched back.
uniform bool plain = false;
uniform vec3 plain_colour : source_color = vec3(0.0, 0.2, 1.0);

varying float seed;

void vertex() {
	seed = COLOR.r;
}

// The loop: a drifting colour field, cut to a new slide every `slide_s`.
vec3 loop_colour(vec2 metres, float time, float phase) {
	vec2 led = (floor(metres / pixel_m) + 0.5) * pixel_m;
	float slide = floor(time / slide_s + phase * 7.0);
	float t = time * drift + phase * 31.0;
	// A slide's own direction and scale, so a cut reads as a new picture.
	vec2 heading = vec2(cos(slide * 2.4), sin(slide * 2.4));
	float scale = 0.08 + 0.06 * fract(slide * 0.618);
	float field = sin(dot(led, heading) * scale * 6.0 + t * 3.0)
		+ sin(led.y * scale * 4.0 - t * 2.0)
		+ sin(length(led - vec2(20.0, 5.0) * heading) * scale * 3.0 - t);
	vec3 colour = 0.5 + 0.5 * cos(6.2831 * (vec3(0.0, 0.33, 0.67) + field * 0.2 + slide * 0.37));
	return colour * colour;
}

void fragment() {
	vec2 metres = UV;
	// `plain` is a uniform, so the branch is coherent and a plain screen pays
	// nothing for the loop.
	vec3 colour = plain ? plain_colour : loop_colour(metres, TIME, seed);
	// The dot grid, faded to its mean where an LED is smaller than a pixel.
	vec2 cell = fract(metres / pixel_m) - 0.5;
	float dot_mask = smoothstep(0.5, 0.3, length(cell));
	float far = clamp(fwidth(metres.x) / pixel_m * 2.0, 0.0, 1.0);
	float grid = mix(mix(1.0 - gap_dark, 1.0, dot_mask), 1.0 - 0.5 * gap_dark, far);
	ALBEDO = vec3(0.02);
	ROUGHNESS = 0.3;
	EMISSION = colour * grid * mix(day_glow, night_glow, night_lights);
}
