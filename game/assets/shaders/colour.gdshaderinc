// Colour conversions every shader reading `COLOR_0` needs (`Q27`).
//
// ⚠️ **This file exists because a fourth copy appeared, and `city_facade.gdshader`
// said in advance that that was the trigger** — *"three call sites still do not
// earn a fourth file … If a fourth appears, that is the point to stop copying
// and add the include."* `P3-12`'s road markings were the fourth. The rule fired
// as written, which is the whole value of having written it down.
//
// Included by `city_facade`, `city_facade_clean` (and through its body
// `city_facade_cel`), `vehicle_body`, `road_markings`, `tramway`, `signs`,
// `signs_text`, `vertex_albedo` and `water`. `docs/ARCHITECTURE.md`'s `COLOR_0`
// row names them.

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

// ---------------------------------------------------------------------------
// The rig's exposure, `exposure_anchor` (`Q38`, `P5-28b`) — the one account of
// it; every shader that declares the global points here.
//
// One global shader parameter, declared in `project.godot` `[shader_globals]`
// and set by `scripts/world/lighting_rig.gd` from an export on the rig scene, so
// the time of day is a number in a scene rather than a value baked into every
// vertex of every tile at build time. The project default is 1.0; both rigs set
// 0.52 since `P5-28c` un-baked the ETL side, and a shipped colour is a
// material's reflectance.
//
// ⚠️ **Multiplied in AFTER `vertex_srgb_to_linear` and nowhere else.** Exposure
// is a linear-light scale on the surface's albedo; applied to sRGB bytes it is a
// different operation and applied to a `.tres` colour it would move paint,
// glazing and rail colour that are authored at their rendered value already.
// Only `COLOR_0` — the ETL's `materials:` table, which is what `Q33`'s
// `reflectance x exposure_anchor` rule is about — passes through it.
//
// ⚠️ **The declaration stays in each shader, not here**: `vehicle_body` and
// `signs_text` include this file and must not scale, and `signs` scales one of
// its three layers.
