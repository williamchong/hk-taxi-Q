// Road paint drawn as its own lifted geometry — turn arrows (`P3-15`), box
// junctions (`P3-18`) and stop / give-way lines (`P3-23`).
//
// 🔴 **One shader, three materials, and the merge is the repo's own rule rather
// than a tidy-up** (`Q71`). `arrows.gdshader`, `boxjunctions.gdshader` and
// `roadmarks.gdshader` were byte-identical but for the default colour, and
// `mesh_contract.gd` states the trigger: *"a third copy should force it"*
// (`Q58`). That file had already applied it to this same trio — `check_faces_up`
// was extracted the day `verify_arrows.gd`, `verify_boxjunctions.gd` and
// `verify_roadmarks.gd` held three copies of it. This is the other half.
//
// ⚠️ **A layer is a parameterisation, not a shader** — `railings.gdshader`'s
// phrasing, and its precedent: one shader serves `railings`, `bollards` and
// `barriers`, which differ only in their `.tres`. What tells an arrow from a box
// from a stop line is the geometry the ETL built and the colour in
// `arrows.tres` / `boxjunctions.tres` / `roadmarks.tres`, never a shader of its
// own.
//
// ⚠️ **The dispatch is still checked per layer, and merging did not weaken it.**
// `MeshContract.check_shader_material` compares the material's `resource_path`
// against the `.tres` each verify tool names, not the shader — so a box junction
// handed `roadmarks.tres` still fails. `check_shader_source`, which *does* look
// at the shader, is for the duplicated sign lettering and must not be reached
// for here.
//
// ---
//
// This is the simplest shader in the project, and the simplicity is the whole
// argument of `P3-15`. `road_markings.gdshader` has to *place* its markings in
// lane space, because it paints a ribbon drawn 1.6x too wide and the paint has
// to survive the widening. This one places nothing: the ETL has already decided
// where every vertex goes. There is no codec to decode, no lane coordinate to
// reconstruct, and no junction fade.
//
// ⚠️ **No fade, and each of the three refuses it for its own reason.**
// `road_markings.tres` carries `fade_m = 6.0`, priced against the measured
// junction cap overlap, and `ARCHITECTURE.md` records that it "blanks exactly
// the approach an arrow is about". An arrow is a whole object rather than a
// length of line, and half an arrow is not a marking. A box junction *is* the
// junction marking, drawn over the cap the ribbon markings fade away from. A
// stop line does not merely approach the junction — it is the junction's edge,
// drawn on the cap, inside the fade and on top of the 6,051 m² overlap. Painted
// on the ribbon it would be invisible by construction.
//
// ⚠️ **The patterns are geometry, not procedural fields.** A shader-hatched box
// or a shader-dashed give-way line would have to show asphalt between the marks,
// and these surfaces float 12-16 mm above the road — there is no albedo
// underneath a fragment to mix into. The two exits are alpha blend (a sorted
// transparent pass; see below) and alpha scissor (which re-aliases every stripe
// and dash end). So the stripes and marks are triangles and this shader paints
// everything it is given. The 600/300 give-way module and the hatch angles live
// in `hong_kong.yaml`, off TD's own sheet, and never in here.
//
// ⚠️ **None of these meshes carries `COLOR_0`**, so there is no vertex colour to
// convert and `colour.gdshaderinc` is deliberately not included. If the ETL ever
// ships per-vertex paint colour, this needs `vertex_srgb_to_linear` the way
// every other shader here does — the conversion is never free.
//
// 🔴 **Opaque, and the first draft of `arrows.gdshader` was not.** It reached for
// `ALPHA` to copy `road_markings.tres`'s `paint_opacity = 0.85`, which is the
// wrong reading of what that value does: next door the paint is *mixed into the
// road's own albedo* on one opaque surface, so the 0.15 is asphalt showing
// through the paint. Here the marking is a second surface above the road, and
// the same number would be asphalt showing through by transparency — which costs
// a sorted alpha pass, drops the depth prepass, and models thermoplastic as
// though it were tinted glass. Real road paint is opaque. So is this.
//
// ⚠️ **That misreading is cited across the repo as `arrows.gdshader`'s, and this
// file is where it now lives.** `Q61` records the one place the objection does
// *not* transfer — a railing is 60-75% air, so `railings.gdshader`'s `ALPHA` is
// coverage rather than translucency. Closed `DECISIONS.md` entries still name
// `arrows.gdshader` and are left as written; they mean this file.

shader_type spatial;

// ⚠️ **`cull_back`, so winding decides visibility and the normal attribute does
// not.** `arrows.py`'s `_ccw` winds every polygon in the glyph's own frame and
// `_place` maps that frame with a negative determinant, which is what turns
// counter-clockwise there into up-facing here; `boxjunctions.py` and
// `roadmarks.py` wind to face `+Y` directly. All three publish `inverted` and it
// must be **0** — the tramway shipped 5,111 of 5,112 triangles facing the ground
// with everything else correct and simply was not in the city.
//
// ⚠️ **The engine-side and ETL-side winding tests have opposite signs**, because
// Godot winds front faces clockwise and glTF counter-clockwise. Do not "fix" one
// to agree with the other; `Q59` records how that was settled and against which
// meshes.
render_mode cull_back;

group_uniforms paint;
// 🔴 **A default, not the value.** All three `.tres` set `paint_colour`
// explicitly, so this is reached only by a material that omits it. It is the
// white because that is what two of the three layers paint; the merge removed
// one authored copy of the white and one of the yellow, taking the ledger from
// ten copies to eight. `roadmarks.tres` keeps the count, because a stale ledger
// is worse than the duplication it describes.
//
// There is no mechanism in Godot to share a value between two `.tres` files, or
// between a shader default and a `.tres`. What holds them together instead is
// that a mismatch is visible in one frame: an arrow a different white from the
// dashes on either side of it is the first thing anyone would notice.
uniform vec4 paint_colour : source_color = vec4(0.91, 0.91, 0.87, 1.0);
// Thermoplastic holds a sheen the asphalt around it does not, which is the cue
// that it is paint rather than a lighter patch of road. Against the road's 0.95,
// as `road_markings.tres` sets it.
uniform float paint_roughness : hint_range(0.0, 1.0) = 0.7;

void fragment() {
	ALBEDO = paint_colour.rgb;
	ROUGHNESS = paint_roughness;
}
