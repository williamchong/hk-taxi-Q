// `city_facade_clean` under a banded sun: the cel half of the city's cel look
// (`P3-64`, `Q158`, the user's ask). The surface is the clean shader's, byte
// for byte — its body is `city_facade_clean.gdshaderinc` — and only the light
// is new. Bound by swapping `tuning/city_facade.tres`'s shader for this one, the
// way the three `Q26` looks switch, so the shipped shader carries no `light()`.
//
// ⚠️ **Why a sibling and not a uniform on the clean shader.** A `light()`
// function replaces the engine's lighting outright: there is no value of a
// uniform under which it reproduces Godot's own Burley diffuse and GGX
// highlight to the byte. A switch inside the shipped shader would move every
// frame of the shipped look with the switch off.
//
// ⚠️ **On this city the ramp alone moves little, and that is the geometry, not
// the shader.** The buildings are flat-shaded, so under one sun every face is
// already one value. What the ramp changes is which of a handful of steps each
// face lands on, the soft edge of a cast shadow, and the curved façades, whose
// facets band. The line that makes the look read as cel is `cel_outline`.
//
// Lambert, not Burley: a step function over a Lambert term is the textbook
// ramp, and Burley's roughness term only blurs the steps it is about to cut.
// The ambient (the sky) is not a light and never reaches `light()`, so the
// shaded side keeps the rig's sky as it is.
shader_type spatial;

render_mode cull_back;

#include "res://assets/shaders/city_facade_clean.gdshaderinc"

group_uniforms cel;
// How many lit steps between the shaded side and full sun. 1 is two-tone.
uniform float cel_steps : hint_range(1.0, 6.0) = 2.0;
// The width of a step's edge, in steps, so a cast shadow's filtered edge
// steps cleanly rather than in a stair per shadow texel. No `fwidth` for it:
// derivatives are a fragment-stage tool and `light()` runs per light.
uniform float cel_softness : hint_range(0.01, 0.5) = 0.05;
// The highest surface marker the ramp applies to: 0 façades only, 1 also the
// ground, 2 also the structures. Past it the light is plain Lambert.
uniform float cel_max_marker : hint_range(0.0, 2.0) = 0.0;
// A hard-edged sun highlight on top, in the light's own colour. 0 is none.
uniform float cel_highlight : hint_range(0.0, 1.0) = 0.0;
uniform float cel_highlight_size : hint_range(0.01, 1.0) = 0.15;

float cel_band(float lit) {
	float scaled = lit * cel_steps;
	float base = floor(scaled);
	return (base + smoothstep(0.5 - cel_softness, 0.5 + cel_softness, scaled - base)) / cel_steps;
}

void light() {
	float lit = clamp(dot(NORMAL, LIGHT), 0.0, 1.0) * ATTENUATION;
	// `marker` is the body's vertex varying; `light()` reads it as `fragment()` does.
	bool banded = marker < cel_max_marker + 0.5;
	float diffuse = banded ? cel_band(lit) : lit;
	DIFFUSE_LIGHT += diffuse * LIGHT_COLOR / PI;

	if (cel_highlight > 0.0) {
		float facing = clamp(dot(NORMAL, normalize(LIGHT + VIEW)), 0.0, 1.0);
		float spot = smoothstep(1.0 - cel_highlight_size, 1.0 - cel_highlight_size * 0.9, facing);
		SPECULAR_LIGHT += spot * ATTENUATION * cel_highlight * (1.0 - ROUGHNESS) * LIGHT_COLOR;
	}
}
