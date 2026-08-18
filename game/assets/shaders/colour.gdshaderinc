// Colour conversions every shader reading `COLOR_0` needs (`Q27`).
//
// ⚠️ **This file exists because a fourth copy appeared, and `city_facade.gdshader`
// said in advance that that was the trigger** — *"three call sites still do not
// earn a fourth file … If a fourth appears, that is the point to stop copying
// and add the include."* `P3-12`'s road markings were the fourth. The rule fired
// as written, which is the whole value of having written it down.
//
// Included by `city_facade`, `city_facade_clean`, `vehicle_body` and
// `road_markings`. `docs/ARCHITECTURE.md`'s `COLOR_0` row names them.

// sRGB bytes to linear, which every shader reading `COLOR` has to do for itself.
//
// ⚠️ **Godot 4 dropped the `vertex_color_is_srgb` render mode.** It survives only
// as a `BaseMaterial3D` flag — which is what `generated_scene_import.gd` sets on
// anything that does *not* name a shader — so a `ShaderMaterial` that skips this
// renders pale. That is the loud half. The quiet half is worse: sRGB read as
// linear adds brightness the albedo did not ask for, and brightness that does not
// vary with albedo destroys albedo *contrast*. Measured under `Q27` — 57% of a lit
// facade pixel's luminance was albedo-independent, and a per-building colour
// difference reached the screen at a third of its size, which is why the measured
// facade colour looked invisible and why no ambient or tonemap tuning moved it.
//
// The exact IEC 61966-2-1 curve rather than `pow(c, 2.2)`: `etl/pipeline/colour.py`
// uses the exact one, and the two sides disagreeing is what that bug *was*.
vec3 vertex_srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}
