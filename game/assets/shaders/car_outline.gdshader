// The car's afterimage while it drifts (`P3-65`, `Q158`, the user's ask): the
// end of the car that is moving most — in a slide, the tail swinging out — is
// grown and dragged out behind its own motion as a band in one colour — the
// car's outermost outline colour, its paint darkened as `cel_outline.gdshader`
// darkens it — fading toward its tip; the rest of the car keeps only the city's
// line ("only drag the end of car which moves most instead of whole car rim",
// then "having the whole car body as after image is strange, can we just do
// outline color for the car outermost rim", the user, 2026-10-07). It seeps in when a slide counts and drains when it ends.
// `CarOutline` picks the end, eases the width and feeds the drag.
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

// Set by `CarOutline` every tick while the afterimage shows: this, `end_axis`,
// `smear_dir` and `smear_m`. The rest are set once.
//
// The afterimage's width at the moving end; none short of `drag_from`.
uniform float hull_width_m = 0.0;
// Which end moves most: the mesh's length axis, signed toward that end (unit).
uniform vec3 end_axis = vec3(0.0, 0.0, 1.0);
// Where along the half-length the drag starts: 0 the middle, 1 the very end.
uniform float drag_from : hint_range(0.0, 1.0) = 0.3;
// The afterimage's strength at its tip; 1 is as solid as the line.
uniform float ghost : hint_range(0.0, 1.0) = 0.35;
// The way the end is dragged, in the mesh's own space (unit) — against that
// end's own velocity, so it follows the arc the tail swings through — and how
// far its tip reaches, metres.
uniform vec3 smear_dir = vec3(0.0, 0.0, 1.0);
uniform float smear_m = 0.0;
// The car's paint, and `cel_outline.tres`'s `surface_darkness`, both handed on
// by `CarOutline`: the band is the colour the city's line draws the car's edge.
uniform vec3 rim_colour : source_color = vec3(0.78, 0.13, 0.16);
uniform float ink_darkness = 0.5;
// The body mesh's box, set by `CarOutline` once from `Mesh.get_aabb()`.
uniform vec3 hull_centre = vec3(0.0);
uniform vec3 hull_half = vec3(1.0);

// How far toward the moving end a vertex sits: 0 short of `drag_from`, 1 at
// the end.
varying float drag;

void vertex() {
	vec3 from_centre = VERTEX - hull_centre;
	// Box-normalised, so -1 and 1 are the two ends whatever the car's length.
	float along = dot(from_centre / hull_half, end_axis);
	drag = smoothstep(drag_from, 1.0, along);
	vec3 grown = hull_centre + from_centre * (hull_half + hull_width_m * drag) / hull_half;
	// Squared, so the tip reaches out and the flanks only lean.
	VERTEX = grown + smear_dir * smear_m * drag * drag;
}

void fragment() {
	// Short of the moving end the hull lies on the body itself: nothing to draw.
	if (drag < 0.01) {
		discard;
	}
	ALBEDO = rim_colour * ink_darkness;
	ALPHA = mix(1.0, ghost, smoothstep(0.5, 1.0, drag));
}
