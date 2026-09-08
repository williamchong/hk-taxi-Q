// A vertex-coloured surface under the rig's exposure, and nothing else
// (`P5-28b`).
//
// 🔴 **This exists because a `BaseMaterial3D` cannot read a global shader
// parameter.** The two authored props in the bundle — `landmark_vertex` for
// `tools/make_landmark.py`'s heroes and `barrier_vertex` for
// `tools/make_barrier.py`'s prop — used to fall through
// `generated_scene_import.gd`'s last branch, which sets
// `vertex_color_use_as_albedo` and `vertex_color_is_srgb` on the imported
// material and is the `Q27` fix in its `BaseMaterial3D` form. That branch is
// correct and stays for anything else; what it cannot do is scale an albedo by
// `exposure_anchor`, so once the ETL stops baking the anchor into `COLOR_0`
// (`P5-28c`) a prop left on it renders at reflectance level — pale, plausible,
// and wrong by the same factor everywhere.
//
// ⚠️ **So this is deliberately the smallest shader in the project.** It is the
// `BaseMaterial3D` branch written as GLSL plus one multiply, and it must stay
// that: anything it grows — a wash, a jitter, a fresnel — is a look the props
// were not reviewed with, and both of them are committed binaries whose
// generators are graded against a shipped frame.
//
// ⚠️ **`roughness_value` matches what the glTF asks for**, `gltf.py::_material`'s
// `roughnessFactor` 0.9, so the surface this replaces and the surface this draws
// are the same surface. Read from a `.tres` rather than hard-coded because
// CLAUDE.md hard rule 4 says a tuning value is data — and the two `.tres` that
// share this file differ in nothing else today, which is `Q61`'s and `Q71`'s
// rule again: a layer is a parameterisation, not a shader.

shader_type spatial;

// `cull_back`, matching the `BaseMaterial3D` default these props imported with.
// Both are closed volumes, so nothing is lost and the back faces are free.
//
// 🔴 **`diffuse_burley` and `specular_schlick_ggx` are STATED because the shader
// language's defaults are not `BaseMaterial3D`'s, and that is worth 10,133
// pixels.** A `StandardMaterial3D` reports `diffuse_mode = 0` (Burley) and
// `specular_mode = 0` (Schlick-GGX) and writes both into the shader it generates;
// a hand-written spatial shader that names neither gets the *language's* default,
// which is a different lighting model. Measured, replacing the props' material
// with this one and changing nothing else: 10,234 px of the `Q31` skyline moved
// at up to 4 codes with the modes unstated, and **101 px at up to 2** with them
// stated. ⚠️ **Do not delete them as redundant** — they are the only line here
// that makes this shader the surface it replaced.
render_mode cull_back, diffuse_burley, specular_schlick_ggx;

#include "res://assets/shaders/colour.gdshaderinc"

// The rig's exposure (`Q38`, `P5-28b`). One global shader parameter, declared in
// `project.godot` `[shader_globals]` and set by `scripts/world/lighting_rig.gd`
// from an export on the rig scene, so the time of day is a number in a scene
// rather than a value baked into every vertex of every asset at build time.
//
// ⚠️ **Multiplied in AFTER `vertex_srgb_to_linear` and nowhere else.** Exposure
// is a linear-light scale on the surface's albedo; applied to sRGB bytes it is a
// different operation.
//
// ⚠️ **It ships at 1.0 and is inert until `P5-28c` un-bakes the ETL side.**
// Both halves of a `reflectance x anchor` product must move in one commit or the
// city renders at the square of the anchor, or at none of it.
global uniform float exposure_anchor;

group_uniforms surface;
uniform float roughness_value : hint_range(0.0, 1.0) = 0.9;

// 🔴 **Linearised in the VERTEX stage and interpolated, which is NOT where every
// other shader in this project does it — and the difference is measurable.**
// `BaseMaterial3D`'s `vertex_color_is_srgb` converts in the vertex stage and
// interpolates the linear result; converting in the fragment stage instead
// interpolates the sRGB bytes and converts once, and sRGB-to-linear is convex, so
// by Jensen the fragment-stage form is uniformly **darker** across any triangle
// whose corners differ. Measured on the shipped hero: Central Plaza alone moved,
// 10,758 px at up to 4 codes, every channel negative, ~0.67 `L*`.
//
// That is not tolerable here, because `P5-28b` is the commit whose whole claim is
// that nothing moves. So this file reproduces the material it replaces rather
// than the convention of its neighbours. ⚠️ **Do not "restore consistency" with
// `city_facade.gdshader`** — those shaders replaced a `BaseMaterial3D` in a
// commit that was allowed to move the frame and was graded on the move; this one
// is not.
//
// ⚠️ The anchor may be applied on either side: a scalar commutes with
// interpolation. It is here so the fragment stage says what it draws.
varying vec3 albedo_linear;

void vertex() {
	albedo_linear = vertex_srgb_to_linear(COLOR.rgb);
}

void fragment() {
	ALBEDO = albedo_linear * exposure_anchor;
	METALLIC = 0.0;
	ROUGHNESS = roughness_value;
}
