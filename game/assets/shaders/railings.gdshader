// Pedestrian railings, drawn as their own geometry (`P3-19`, `Q60`).
//
// `boxjunctions.gdshader` with two differences, and both come from the fence
// being a *vertical* surface the player sees from either side.
//
// ⚠️ **`cull_disabled`, where every other generated mesh in this bundle is
// `cull_back`.** A fence has two faces and the car drives past both of them —
// along the kerb on the road side, and, wherever a ribbon runs beside a
// footway, from the pavement side too. Drawn `cull_back` at one quad per
// station the fence would simply vanish from half the approaches, which is
// `Q58`'s failure-to-nothing wearing a different hat. The alternative is two
// quads per station and twice the triangles for a surface 40 mm thick, which
// buys nothing a driver can see.
//
// ⚠️ **So the winding no longer decides visibility — it decides *lighting*.**
// `pipeline/railings.py` winds every quad to look at the carriageway and
// `railings.json` publishes `facing_away`, which must be 0. A flipped quad
// still draws; it draws with its normal pointing into the pavement, which reads
// as a black panel in full sun. That is why the counter survives the switch to
// `cull_disabled` rather than being retired with the culling.
//
// The back face is lit by negating the normal rather than by leaving it alone:
// an unflipped back face takes its light from the wrong hemisphere, and the
// fence on the far side of a street would darken as the sun crossed it.
//
// ⚠️ **`railings.glb` carries no `COLOR_0`**, so there is no vertex colour to
// convert and `colour.gdshaderinc` is deliberately not included.
//
// ⚠️ **Opaque.** Real railings are hollow — vertical balusters with air between
// them — and the honest way to draw that is alpha, which `arrows.gdshader`
// records the mobile-budget objection to: a sorted transparent pass on the
// device floor, or a scissor that re-aliases every baluster. So this is a solid
// panel, and the divergence is recorded in `ART_DESIGN.md` rather than hidden.

shader_type spatial;

render_mode cull_disabled;

group_uniforms paint;
// Hong Kong's street railings are painted a pale institutional grey-green that
// reads almost white in sun and almost grey in shade. Authored here rather than
// in `hong_kong.yaml`'s `materials:` table for the reason `Q53` gives for the
// marking colours: street furniture is not cladding, so it sits outside `Q33`'s
// exposure rule.
uniform vec4 rail_colour : source_color = vec4(0.78, 0.80, 0.76, 1.0);
// Painted steel, against the road's 0.95 and the markings' 0.7. Lower than
// paint on tarmac because a railing is a smooth tube rather than thermoplastic
// pressed into aggregate.
uniform float rail_roughness : hint_range(0.0, 1.0) = 0.55;
// Deliberately 0.0, and the reason is measured: `P3-14` shipped the tram rails
// at `metallic` 0.65 and they rendered **sky blue**, because metal reflects its
// environment and the only environment here is sky. A railing is painted steel,
// which is a dielectric surface over metal, so 0.0 is also the truthful value.
uniform float rail_metallic : hint_range(0.0, 1.0) = 0.0;

void fragment() {
	ALBEDO = rail_colour.rgb;
	ROUGHNESS = rail_roughness;
	METALLIC = rail_metallic;
	// The mesh gives every vertex the normal that looks at the carriageway; the
	// back face needs the other hemisphere or it lights as if the sun were
	// behind the street.
	NORMAL = FRONT_FACING ? NORMAL : -NORMAL;
}
