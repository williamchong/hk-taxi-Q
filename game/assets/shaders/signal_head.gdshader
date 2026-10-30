// The signal heads, lit by `SignalController` (`P3-3e`, `Q173`).
//
// One `MultiMesh` holds every head in the city (`signal_heads.gd`), so a head's
// light cannot be an `instance uniform`: `SignalHeads` writes it into
// `INSTANCE_CUSTOM.a` as the `SignalController.Light` enum — 0 NONE, 1 RED,
// 2 RED_AMBER, 3 GREEN, 4 AMBER — `vehicle_body.gdshader`'s pattern for the
// moving cars' lamps. A head with no custom data reads 0, and every lens stays
// dark: never a head lit at a guess.
//
// The lens circuit is the mesh's (`tools/make_signal_heads.py`): `UV.x` is 0 on
// the housing and `k + 1` on lens `k`, top to bottom red, amber, green —
// `vehicle_body.gdshader`'s lamp circuits. ⚠️ **Not `COLOR_0` alpha**: the
// Compatibility renderer (the web build) reads it as 0 on every vertex here, and
// every lens went dark there (measured 2026-10-30).
//
// 🔴 **Lit by day.** A signal is a lamp a driver reads at noon, so the emission
// does NOT multiply `night_lights` — the cars' brake lens is the precedent
// (`vehicle_body.gdshader`: braking is full, day or night). The night may only
// raise it (`lamp_night_gain`). ⚠️ **`colour.gdshaderinc` is mandatory**: the
// housing and the unlit glass are sRGB on the vertex (`Q27`).

shader_type spatial;

#include "res://assets/shaders/colour.gdshaderinc"

// ⚠️ `cull_back`: the head is a closed box and the post a capped prism, so
// winding decides visibility (`test_make_signal_heads.py` holds it).
render_mode cull_back;

global uniform float night_lights;

// Painted cast housing: duller than a sign plate.
uniform float body_roughness : hint_range(0.0, 1.0) = 0.7;
// The lit lamp of each aspect. The vertex carries the unlit glass.
uniform vec3 lamp_red : source_color = vec3(1.0, 0.1, 0.06);
uniform vec3 lamp_amber : source_color = vec3(1.0, 0.55, 0.05);
uniform vec3 lamp_green : source_color = vec3(0.1, 1.0, 0.55);
// How bright a lit lens burns by day, and how much the night multiplies it.
// Zero defaults: an unparameterised material shows a dark head, which is
// visible, rather than a lamp at a guess.
uniform float lamp_emission : hint_range(0.0, 16.0) = 0.0;
uniform float lamp_night_gain : hint_range(1.0, 8.0) = 1.0;

varying flat int light;

void vertex() {
	light = int(INSTANCE_CUSTOM.a + 0.5);
}

void fragment() {
	vec3 albedo = vertex_srgb_to_linear(COLOR.rgb);
	// 0 the housing, 1 red, 2 amber, 3 green.
	int circuit = int(UV.x + 0.5);
	bool red = circuit == 1 && (light == 1 || light == 2);
	bool amber = circuit == 2 && (light == 2 || light == 4);
	bool green = circuit == 3 && light == 3;
	bool lit = red || amber || green;
	vec3 lamp = vec3(0.0);
	if (red) {
		lamp = lamp_red;
	} else if (amber) {
		lamp = lamp_amber;
	} else if (green) {
		lamp = lamp_green;
	}
	ALBEDO = lit ? lamp : albedo;
	ROUGHNESS = lit ? 0.2 : body_roughness;
	EMISSION = lamp * lamp_emission * mix(1.0, lamp_night_gain, night_lights);
}
