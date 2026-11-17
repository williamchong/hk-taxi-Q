// The black line round a vehicle (`Q248`): the body drawn a second time, grown
// and inside out, so only its rim shows past the body in front of it.
//
// Not on `vehicle_body.tres` since the city's screen line went black and drew
// this line itself (`Q248`'s amendment); kept as the line a vehicle takes back
// as a `next_pass` if that pass is hidden.
//
// ⚠️ **Grown along the vertex's place on the body, never along `NORMAL`.** The
// bodies are flat-shaded, so each face carries its own normal and a hull pushed
// along them opens at every fold: the line came out dashed. A vertex's place
// is the same on every face that shares it, so the hull stays closed.
shader_type spatial;

render_mode unshaded, cull_front, shadows_disabled;

uniform vec3 outline_colour : source_color = vec3(0.02, 0.02, 0.02);
uniform float outline_m : hint_range(0.0, 0.1) = 0.03;
// The height the hull grows away from (`vehicle_body.gdshader`'s
// `crown_height_m`: the one middle of the body), and how near the body's middle a vertex
// has to be before it grows by less than the whole width.
uniform float outline_height_m : hint_range(0.0, 3.0) = 0.7;
uniform float outline_soft_m : hint_range(0.01, 1.0) = 0.1;

#ifdef VEHICLE_BATCHED
// The line leaves with its car.
#include "res://assets/shaders/vehicle_fade.gdshaderinc"
#endif

void vertex() {
#ifdef VEHICLE_BATCHED
	faded = fade_of(floor(INSTANCE_CUSTOM.a + 0.5));
#endif
	// The line casts nothing: the body's own shadow is already there, and a
	// `next_pass` is drawn into every shadow cascade unless it folds itself up.
	if (IN_SHADOW_PASS) {
		VERTEX = vec3(0.0);
	} else {
		vec3 from = VERTEX - vec3(0.0, outline_height_m, 0.0);
		vec3 grow = clamp(from / outline_soft_m, vec3(-1.0), vec3(1.0));
		// A face turned back toward the middle stays where it is on that axis: a
		// bumper is a closed box sunk in the body, and its buried back face, grown
		// outward with the rest, came out through the grille.
		grow *= step(vec3(-0.3), NORMAL * sign(from));
		// An underside is drawn in, not out: the floor runs across the wheel
		// arches, and its grown rim drew a line over each wheel.
		if (NORMAL.y < -0.5) {
			grow.xz = -grow.xz;
		}
		VERTEX += grow * outline_m;
	}
}

void fragment() {
#ifdef VEHICLE_BATCHED
	if (fade_drops(faded, FRAGCOORD.xy)) {
		discard;
	}
#endif
	ALBEDO = outline_colour;
}
