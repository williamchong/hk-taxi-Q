// Pedestrian railings, drawn as their own geometry (`P3-19`, `Q60`, `Q61`).
//
// `boxjunctions.gdshader` with three differences. Two come from the fence being
// a *vertical* surface the player sees from either side; the third is that a
// fence is mostly air, and it is the one this shader exists for.
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
// convert and `colour.gdshaderinc` is deliberately not included. It *does*
// carry `TEXCOORD_0`, and that is not a texture coordinate either: `UV.x` is
// metres along the run and `UV.y` is metres above the ribbon deck. Nothing
// samples an image here, and `mesh_contract.gd` walks every uniform and would
// refuse the bundle if anything did.
//
// ---------------------------------------------------------------------------
// ⚠️ **This is the first transparent material in the bundle, and `P3-19` shipped
// it opaque on an objection that turns out to belong to a different surface.**
//
// The recorded reason for the solid panel was `arrows.gdshader`'s: alpha costs
// "a sorted transparent pass on the device floor, or a scissor that re-aliases
// every baluster". That note is reasoning about **road paint**, and for road
// paint it is right — it concludes "Real road paint is opaque. So is this."
// A railing is the opposite physical case. It is 60-75% air, and the frames
// said so: `build/driver/railings_street` and `railings_hennessy` shipped
// reading as white concrete parapets flanking the carriageway.
//
// Both halves of the objection have an answer here that they did not have next
// door:
//
//   - **Sorting.** Every other shader in this bundle is opaque, so there is
//     exactly one transparent object in the scene and nothing to sort it
//     against. It depth-tests against all opaque geometry the ordinary way, so
//     a building in front of a fence still occludes it. What is left is the
//     fence blending with itself where two runs overlap on screen, and
//     `depth_prepass_alpha` is what removes that.
//   - **Aliasing.** The scissor aliases because it *samples* a stripe. This
//     integrates it instead — `bars()` below returns the exact average coverage
//     over the fragment's own footprint, so a baluster is crisp when it is
//     wider than a pixel and dissolves into a uniform alpha when it is not.
//     There is no distance at which it shimmers and none at which it vanishes.
//
// ⚠️ **`ALPHA` is coverage, not translucency.** Nothing here is tinted glass:
// the fence is opaque steel with gaps in it, and the alpha is what fraction of
// the fragment the steel covers. That is why it is computed geometrically from
// the authored dimensions rather than authored as an opacity dial — an opacity
// dial would be `arrows.gdshader`'s misreading of `paint_opacity` in a new
// place.
//
// ⚠️ **Every dimension below is authored and none is read.** No sheet in the
// bundle publishes a railing dimension — `Q60` establishes that, and the
// symbology correction strengthened it to "without qualification". So the
// baluster pitch is in the same position as `height_m`: declared as authored,
// in tuning data rather than in code (hard rule 4), and judged on the frames.

shader_type spatial;

// `depth_prepass_alpha` so the fence does not blend with itself where two runs
// cross on screen. `cull_disabled` stays, and `verify_railings.gd` pins it by
// substring — a one-word edit here would otherwise delete half the region's
// fences with every other check still passing.
render_mode cull_disabled, depth_prepass_alpha;

group_uniforms paint;
// Hong Kong's street railings are **galvanised steel, and they are grey**.
// Authored here rather than in `hong_kong.yaml`'s `materials:` table for the
// reason `Q53` gives for the marking colours: street furniture is not cladding,
// so it sits outside `Q33`'s exposure rule.
//
// ⚠️ **This said "a pale institutional grey-green" for two revisions and it was
// wrong** — the green was never read off anything, and every class inherited it
// (`bollards` 0.42/0.44/0.42, `barriers` 0.5/0.5/0.48, all with the green
// channel highest and blue lowest). Corrected on the user's report, which is the
// only instrument this value has ever had: `railings.tres` records that it is
// the one authored colour in the bundle with no second reading to check it
// against, and this is the second time that has cost something.
//
// ⚠️ **Dead neutral, and the cool cast is left to the sky.** Zinc is very
// slightly blue and the first correction put that in the albedo — which
// double-counts, because the environment is already in the render: measured on
// the `street` frame, the fence comes back **B−R +11.5** from a +0.03 albedo
// bias and **+5.7** from none at all — the sky supplies the cast on its own.
// That is `P3-14`'s metallic lesson wearing a different hat. The albedo says
// what the steel is; the sky says what it looks like.
//
// The same frame is what says the green is gone: **G−R +6.7** at `P3-19`'s
// value against **+0.6** now.
//
// ⚠️ **It also shipped at 0.78/0.80/0.76 and clipped.** At that value the fence
// was within a whisker of white before the sun reached it. Pale is the right
// reading of the street; there was no headroom left above it.
uniform vec4 rail_colour : source_color = vec4(0.64, 0.64, 0.64, 1.0);
// Painted steel, against the road's 0.95 and the markings' 0.7. Lower than
// paint on tarmac because a railing is a smooth tube rather than thermoplastic
// pressed into aggregate.
uniform float rail_roughness : hint_range(0.0, 1.0) = 0.55;
// Deliberately 0.0, and the reason is measured: `P3-14` shipped the tram rails
// at `metallic` 0.65 and they rendered **sky blue**, because metal reflects its
// environment and the only environment here is sky. A railing is painted steel,
// which is a dielectric surface over metal, so 0.0 is also the truthful value.
uniform float rail_metallic : hint_range(0.0, 1.0) = 0.0;

group_uniforms fence;
// ⚠️ **These six are what tell one class of street furniture from another, and
// they are the whole difference.** `Q61` draws the railing layer as three
// classes — `railings`, `bollards`, `barriers` — from one `.glb`, through this
// one shader, with a `.tres` each. A bollard is a strip whose mask keeps wide
// uprights at a large pitch and no rails; a vehicle barrier is a strip whose
// mask keeps two horizontal rails and no balusters. Nothing branches; the
// numbers do the work, which is what keeps the difference in tuning data where
// hard rule 4 wants it.
//
// **A member is switched off by giving it zero width**: `bars()` returns
// exactly 0.0 for a zero-width bar and `band()` exactly 0.0 for a zero-height
// band. That is the convention the bollard and barrier `.tres` files use, and it
// is why `baluster_width_m` is allowed down to 0.0 rather than to some small
// epsilon — an epsilon would leave faint ghost balusters on a bollard. The
// buried skirt is the exception and takes no width: it is not a member, it is
// the part of the strip that is under the pavement.
//
// The vertical members, in metres along the run. A Hong Kong pedestrian railing
// is a picket of narrow balusters at roughly a hand's width — close enough that
// a child cannot pass, which is what the fence is for.
uniform float baluster_pitch_m : hint_range(0.02, 1.0) = 0.11;
uniform float baluster_width_m : hint_range(0.0, 0.5) = 0.035;
// The heavier uprights the balusters hang between — and, on a bollard, the
// whole object. Pitched independently of `station_m`: the mesh's stations are
// where a run takes its height from the ribbon, which is a different question
// from where its posts are.
uniform float post_pitch_m : hint_range(0.1, 20.0) = 2.0;
uniform float post_width_m : hint_range(0.0, 1.0) = 0.09;
// The horizontal rails, as `(low, high)` in metres above the ribbon deck —
// `UV.y`'s own frame, so these are read off the street and mean what they say.
// The top rail is the one a fence is recognised by at distance; the bottom one
// is what stops the picket reading as loose bars. `vec2(0.0, 0.0)` is "no rail".
uniform vec2 top_rail_m = vec2(0.95, 1.10);
uniform vec2 bottom_rail_m = vec2(0.08, 0.18);
// ⚠️ **Below the deck the fence is solid, and that is what `base_sink_m` is
// for.** The ETL sinks the foot 0.25 m because the kerb is flattened for
// mountability and the ground is a separately decimated surface, so the two
// disagree by centimetres and daylight shows under a fence planted exactly at
// road height. Balusters would let that daylight straight back through, so the
// skirt is closed. It is under the pavement wherever the two agree.
uniform float skirt_top_m = 0.0;

// Antiderivative of a unit-period pulse train of duty cycle `duty`: the total
// covered length from 0 to `t`. Exact, and the whole reason this shader does
// not alias.
float pulse_integral(float t, float duty) {
	return floor(t) * duty + min(fract(t), duty);
}

// ⚠️ **Everything below is evaluated TWICE per covered pixel.**
// `depth_prepass_alpha` compiles `fragment()` into the depth prepass as well as
// the colour pass, so the whole mask runs once to decide whether to write depth
// and once to shade. That is the price of the prepass — which the header argues
// for, and which is worth it — but it means this is the one place in the bundle
// where a divide costs double. Hence the reciprocals below, hoisted out of the
// five members and passed in: the same two denominators were being recomputed
// seven times between them.
//
// The average coverage of a `width_m` bar repeating every `pitch_m`, over the
// footprint this fragment spans. Integrated rather than sampled, so it is 1.0
// inside a near baluster, 0.0 in the gap beside it, and settles to the duty
// cycle `width_m / pitch_m` once a bar is finer than a pixel.
float bars(float x_m, float pitch_m, float width_m, float span_m, float inv_span) {
	float inv_pitch = 1.0 / pitch_m;
	float duty = clamp(width_m * inv_pitch, 0.0, 1.0);
	// In pitches, so `2.0 * half_span == span_m * inv_pitch` and the final
	// division by it becomes a multiply by `pitch_m * inv_span`.
	float half_span = span_m * 0.5 * inv_pitch;
	float t = x_m * inv_pitch;
	float covered = pulse_integral(t + half_span, duty) - pulse_integral(t - half_span, duty);
	return clamp(covered * pitch_m * inv_span, 0.0, 1.0);
}

// The same integral for a single band rather than a train — a horizontal rail.
float band(float y_m, float low_m, float high_m, float span_m, float inv_span) {
	float half_span = span_m * 0.5;
	return clamp((min(y_m + half_span, high_m) - max(y_m - half_span, low_m)) * inv_span, 0.0, 1.0);
}

// The buried skirt: coverage of the half-line below `top_m`.
//
// ⚠️ **This was `band(y, -1000.0, top_m, ...)` and the lower bound was dead
// code.** `UV.y` cannot go below `-base_sink_m`, so `max(y - half_span, -1000.0)`
// never bound and the clamped ramp below is what the band always reduced to —
// checked against it over 200k samples at footprints from 1e-6 to 5 m, max
// difference 1.1e-13. Eleven operations became four.
float below(float y_m, float top_m, float inv_span) {
	return clamp(0.5 + (top_m - y_m) * inv_span, 0.0, 1.0);
}

void fragment() {
	// `UV` is not a texture coordinate: x is metres along this run of fence and
	// y is metres above the ribbon deck. `pipeline/railings.py:_run_uvs`.
	float along_m = UV.x;
	float up_m = UV.y;
	// ⚠️ **The floor is numerical, not visual.** `fwidth` can return 0 on a
	// degenerate derivative and everything below divides by this. 0.1 mm is far
	// under any footprint a camera in this game produces.
	float along_span_m = max(fwidth(along_m), 1e-4);
	float up_span_m = max(fwidth(up_m), 1e-4);
	float along_inv = 1.0 / along_span_m;
	float up_inv = 1.0 / up_span_m;

	// Steel is wherever any member is: a baluster, a post, either rail, or the
	// buried skirt. `max` rather than a sum, because two members overlapping —
	// a post crossing a rail — is one piece of steel and not two.
	float steel = bars(along_m, baluster_pitch_m, baluster_width_m, along_span_m, along_inv);
	steel = max(steel, bars(along_m, post_pitch_m, post_width_m, along_span_m, along_inv));
	steel = max(steel, band(up_m, top_rail_m.x, top_rail_m.y, up_span_m, up_inv));
	steel = max(steel, band(up_m, bottom_rail_m.x, bottom_rail_m.y, up_span_m, up_inv));
	steel = max(steel, below(up_m, skirt_top_m, up_inv));

	ALBEDO = rail_colour.rgb;
	ALPHA = steel;
	ROUGHNESS = rail_roughness;
	METALLIC = rail_metallic;
	// The mesh gives every vertex the normal that looks at the carriageway; the
	// back face needs the other hemisphere or it lights as if the sun were
	// behind the street.
	NORMAL = FRONT_FACING ? NORMAL : -NORMAL;
}
