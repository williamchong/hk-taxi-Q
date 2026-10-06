// The light tail (`P3-70`, `Q158` reversed on the user's ask): the streak the
// tail lamps leave while a slide counts — "instead of the whole car tail for
// drifting after image, what if we only drag the lights? literally lighttail"
// (the user, 2026-10-07). `LightTrail` lays it as a ring of pieces, each corner
// stamped in `UV.x` with the clock when it was laid; this fades each corner
// against the clock now, so a streak dies on time whether or not the car has
// moved on. One colour, the lamp's lit red by default (`light_tail.tres`).
//
// Unshaded and drawn over everything at its depth without writing it: a streak
// is light, not a surface, and two pieces crossing must not z-fight.
shader_type spatial;
render_mode unshaded, cull_disabled, shadows_disabled, fog_disabled, blend_mix, depth_draw_never;

// The clock the pieces were laid against, written by `LightTail` every tick.
uniform float now_s = 0.0;
// How long a piece lives, and the shape of its fade (1 linear).
uniform float life_s = 0.4;
uniform float fade_power = 1.0;
// The streak's colour; its alpha scales the whole fade.
uniform vec4 colour : source_color = vec4(1.0, 0.16, 0.2, 1.0);

// How much life this corner has left, 1 just laid to 0 gone.
varying float left;

void vertex() {
	left = 1.0 - (now_s - UV.x) / life_s;
}

void fragment() {
	// A dead corner is alpha 0 under blend_mix: no discard, which costs on a
	// tile-based mobile GPU.
	ALBEDO = colour.rgb;
	ALPHA = colour.a * pow(clamp(left, 0.0, 1.0), fade_power);
}
