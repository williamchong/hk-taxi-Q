// The car's own outline while it drifts (`P3-65`, `Q158`, the user's ask): a
// thin rim round the body in the car's own outline colour — each part's paint
// darkened as `cel_outline.gdshader` darkens it — that seeps in when a slide
// counts, drains when it ends, and trails a short light tail behind the slide
// ("drains a little without breaking the shape of car", "like a light tail
// when drifting but much shorter", the user, 2026-10-07). `CarOutline` eases
// the width and feeds the drag.
//
// A hull — the body drawn again bigger, back faces only — so the rim shows only
// outside the silhouette and never over the paint.
//
// ⚠️ **Grown by the mesh's box, not along its normals.** The taxi is flat-shaded,
// so a corner's vertices carry one normal per face; pushed out along those, the
// faces part at every edge. Scaled about the box's centre so each side moves
// out by `hull_width_m`, the faces stay joined — exact for the boxy toy body,
// a few millimetres off on its raked screens.
//
// Its own shader rather than a pass on `vehicle_body.tres`: that material is
// shared by the roster, and a `next_pass` there would rim every car.
shader_type spatial;
render_mode unshaded, cull_front, shadows_disabled, fog_disabled, blend_mix, depth_draw_never;

#include "res://assets/shaders/colour.gdshaderinc"

// Set by `CarOutline` every tick while the rim shows: this, `trail_width_m`,
// `smear_dir` and `smear_m`. The rest are set once.
uniform float hull_width_m = 0.0;
// More rim on the trailing side, the side the car slides away from — the
// afterimage, 飄移殘影 (the user, 2026-10-07) — at most this much more, scaled
// with the rim as it seeps and drains.
uniform float trail_width_m = 0.0;
// The way the tail is dragged, in the mesh's own space (unit), and how far it
// reaches behind, metres.
uniform vec3 smear_dir = vec3(0.0, 0.0, 1.0);
uniform float smear_m = 0.0;
// `cel_outline.tres`'s `surface_darkness`, handed on by `CarOutline` so the
// rim is the line's colour by construction.
uniform float ink_darkness = 0.5;
// The body mesh's box, set by `CarOutline` once from `Mesh.get_aabb()`.
uniform vec3 hull_centre = vec3(0.0);
uniform vec3 hull_half = vec3(1.0);

// How far into the tail a vertex sits: 0 on the rim, 1 at the tail's end.
varying float tail;

void vertex() {
	vec3 from_centre = VERTEX - hull_centre;
	// How far round to the trailing side, box-normalised so the long car is not
	// all "side". Linear for the rim's lean, so it thickens without a step;
	// squared for the tail, so only the back of the slide reaches out.
	float behind = clamp(dot(normalize(from_centre / hull_half), smear_dir), 0.0, 1.0);
	float width = hull_width_m + trail_width_m * behind;
	vec3 grown = hull_centre + from_centre * (hull_half + width) / hull_half;
	tail = behind * behind;
	VERTEX = grown + smear_dir * smear_m * tail;
}

void fragment() {
	ALBEDO = vertex_srgb_to_linear(COLOR.rgb) * ink_darkness;
	// The tail fades as it reaches back, so it reads as light and not as body.
	ALPHA = 1.0 - smoothstep(0.1, 1.0, tail) * step(0.001, smear_m);
}
