// Lane markings drawn along the ribbon's own lane coordinate (`P3-12`).
//
// `docs/ART_DESIGN.md` has specified this since `P1-4`: markings come from a
// shader driven by the UVs, **not from a texture atlas**. That is not a stylistic
// preference — `scripts/city/mesh_contract.gd` walks every shader uniform and
// fails on any that holds a `Texture`, because the bundle is specified to carry
// no images at all. A marking atlas is a contract amendment; this is not.
//
// What the surface ships, and why it ships two channels rather than one, is in
// `docs/ARCHITECTURE.md`'s `roads.glb` table and in `etl/pipeline/surface.py`'s
// codec block. In short:
//
//   UV.x   the lane coordinate — 0 at the **nearside** kerb line, `lanes` at the
//          offside — so an integer U is a lane boundary whatever the 1.6x
//          widening did to the metres.
//   UV.y   metres along the carriageway, so a dash keeps a real-world pitch.
//   UV2.x  packed marking state, a small exact integer, constant per edge.
//   UV2.y  the edge's **drawn length** in metres, 0.0 on a junction cap.
//   COLOR.a  where a kerbside no-stopping restriction runs, per rail, and so per
//          side of the road — see `restricted` below. RGB is the asphalt.
//
// ⚠️ **UV alone cannot be drawn on**: the kerbs run off both ends of the lane
// range, so `fract(U)` paints a line down one, and `U = 3.0` is a kerb on a
// three-lane road and a lane boundary on a four-lane one. `surface_class` and
// `lanes` are what separate them, which is why `UV2` exists.
//
// ⚠️ **The junction fade is doing two jobs and only one of them is cosmetic.**
// A junction cap overlaps its arms rather than abutting them — 6,051 m² of
// 52,985 m², 210 of 1,398 trimmed ends — which is invisible while cap and
// carriageway are one colour and becomes a visible patch over any marking drawn
// underneath. Fading the markings out before the trim is what real lane lines do
// *and* what keeps that defect off screen. **The overlap is still there.**
// Anything drawn *on* a cap — a box junction — re-exposes it and wants the
// non-convex cap first.
//
// What is deliberately not here: turn arrows, road text and box junctions. Not
// because a glyph is impossible without a texture, but because nothing in the
// seventeen Road Network v2 layers says which lane turns where or which junction
// carries a box — `docs/DATA_SOURCES.md`, "Lane counts do not exist". See `Q53`.
shader_type spatial;

render_mode cull_back;

#include "res://assets/shaders/colour.gdshaderinc"

// Must match the `MARKING_*` codec constants in `etl/pipeline/surface.py`.
// ⚠️ Contract, not tuning — `docs/ARCHITECTURE.md` is the tiebreak if these and
// the ETL ever disagree, and `tools/verify_road_surface.gd` is what notices.
// Each field's modulus is the next field's multiplier, so the widths below are
// derived rather than written down: widening a field moves one line.
const float MARKING_CLASS_CARRIAGEWAY = 0.0;
const float MARKING_LANES = 4.0;
const float MARKING_DIRECTION = 64.0;
const float MARKING_BUS_LANE = 256.0;
const float MARKING_TRAM = 512.0;
const float MARKING_OFFSIDE_KERB = 1024.0;
const float MARKING_CENTRE = 2048.0;
// One past the widest `centre` the six bits hold. Named so the decode can
// mask like every other field rather than trusting that nothing is ever
// packed above it — the one unmasked read is the one that breaks silently.
const float MARKING_CENTRE_SPAN = 64.0;
// What kind of kerbside line each side carries (`P3-13`). Two bits each, and
// the same vocabulary on both: 0 nothing known, 1 known unrestricted, 2 single
// yellow, 3 double. **Where** it applies is not here — it is `COLOR.a`, which
// varies along the edge where this cannot.
const float MARKING_KERB_NEAR = 131072.0;
const float MARKING_KERB_OFF = 524288.0;
const float MARKING_KERB_SPAN = 4.0;
const float MARKING_KERB_SINGLE = 2.0;
const float MARKING_KERB_DOUBLE = 3.0;
// `direction` as the codec spells it. 0 is "absent", and a road whose direction
// did not survive gets no centre line rather than a guessed one.
const float DIRECTION_BOTH = 1.0;
// How close a lane divider may come to a drawn centre line before it is
// suppressed, in lane units. ⚠️ **An EDITORIAL bound and not a geometric one**:
// it is here so a dashed line does not run *beside* a solid one, which is why
// the unnamed pair's join at `U = 1.19` suppresses the divider at `k = 1`
// though the two never touch. The geometric bound is applied underneath it with
// a `max`, so this may be tuned without being able to put a dash through paint.
const float CENTRE_DIVIDER_CLEARANCE_U = 0.25;
// ⚠️ `tram_tracks` is shipped and deliberately not decoded, and since `P3-14`
// the tramway is drawn as its own mesh — `pipeline/tramway.py`, `tram.glb`.
//
// ⚠️ **The reason this comment used to give was a misquote of `ART_DESIGN.md`**
// ("an inset strip — geometry, not shading"), which says the opposite: *"it
// belongs with the markings shader, not with the ribbon"*. `Q58` measured the
// real reason. The published rails are **not on this ribbon**: 80 of the 86
// flagged edges are one-way, the reserve runs between two opposed carriageways,
// and only **18.8%** of cross-sections have both tracks on the drawn surface —
// **1.5%** on Hennessy. A rail drawn in lane space would sit a median 3.26 m
// from where the estate publishes it.
//
// The bit stays in the codec because it is still true and still cheap: it says
// which streets carry a tram, which `P3-3`'s traffic will want.

group_uniforms paint;
// Bright white and saturated yellow, per `ART_DESIGN.md`'s anchor colours. Not
// pure white: road paint is never brighter than the sky and a clipped white
// line reads as an emissive strip at grazing angles.
uniform vec3 line_colour : source_color = vec3(0.91, 0.91, 0.87);
uniform vec3 yellow_colour : source_color = vec3(0.86, 0.68, 0.13);
// How much of the asphalt shows through. Paint on a road is worn, and at 1.0
// every line reads as a decal laid on top rather than as something driven over.
uniform float paint_opacity : hint_range(0.0, 1.0) = 0.85;
// Fresh paint is smoother than the aggregate around it. A small difference, and
// it is what catches the low sun along a line rather than across it.
uniform float paint_roughness : hint_range(0.0, 1.0) = 0.7;
uniform float road_roughness : hint_range(0.0, 1.0) = 0.95;

group_uniforms widths;
// ⚠️ **Every width here is in lane widths, not metres**, because that is what U
// is. They are authored wider than life on purpose: a real 10 cm line is under a
// pixel at any distance the player is actually looking, and the first tuning
// pass lost the markings entirely to that.
//
// 🔴 **A U-lane is NOT `lane_width_m`, and the conversion written here was wrong
// by the widening for three releases.** U is normalised to the ribbon *as drawn*
// — that is what makes an integer U a lane boundary whatever the widening did —
// so one U-lane is `2 * half_width / lanes`, which is **5.12 m** across this
// region (p10 4.16, p90 5.12) against the 3.20 m `lane_width_m` authors. This
// block used to read "at the region's 3.2 m lane, 0.031 is a 10 cm line", which
// understated every figure below by the 1.6x widening: `line_width` 0.05 is a
// **26 cm** line, not 16. `surface.py::_u_metres` is the same correction made on
// the ETL side, and `P3-12` records the join landing off the carriageway
// entirely the one time the two were confused.
uniform float line_width : hint_range(0.0, 0.3) = 0.05;
// The centre line is a DOUBLE continuous white line, and both numbers are TD's.
// `CT174/51-5(1)F` publishes RM1001 DOUBLE LINES as `LINE WIDTH = 150,
// LINES SPACING = 100`, so `centre_gap` is the **clear gap between the two
// lines and not a pitch** — the sheet's own convention, and the one the config
// block for `road_marks` spells out at length, because reading it as a pitch
// draws two 150 mm lines whose centres are 100 mm apart, which is one 250 mm
// line. The pitch is derived below rather than authored.
//
// ⚠️ **The pair is 1.88x life size and that is `line_width`'s exaggeration, not
// a second choice**: 0.055 U is 0.28 m against the published 0.150, and the gap
// is held at the sheet's own 100/150 of it so the shape stays TD's at whatever
// scale legibility asks for.
//
// ⚠️ **`yellow_gap` below is a PITCH, not a clear gap** — it is measured from the
// inner line's centre — so the two are not the same kind of number despite the
// names. Left as it is: it draws correctly, and renaming it moves a shipped
// value for nothing.
uniform float centre_width : hint_range(0.0, 0.3) = 0.055;
uniform float centre_gap : hint_range(0.0, 0.3) = 0.0367;
uniform float bus_width : hint_range(0.0, 0.4) = 0.09;
// The kerbside double yellow: where the inner line starts, and the gap to the
// second. Set clear of U = 0 so the pair sits on the carriageway rather than
// half under the kerb, and the gap clear of 0 so the two do not coincide.
uniform float yellow_inset : hint_range(0.0, 0.6) = 0.09;
uniform float yellow_gap : hint_range(0.01, 0.3) = 0.06;
uniform float yellow_width : hint_range(0.0, 0.2) = 0.035;

group_uniforms pitch;
// Along the carriageway, in metres — V is already metres, so these need no
// conversion and stay true whatever the widening did across the road.
uniform float dash_length_m : hint_range(0.5, 20.0) = 3.0;
uniform float dash_gap_m : hint_range(0.5, 20.0) = 6.0;

group_uniforms junction;
// How far back from the end of the ribbon the markings are gone. Real lane
// lines stop before a junction, and this is also what hides the cap overlap —
// see the header. **Sized against that overlap rather than by eye**: measured
// per arm end across the region, the cap reaches p90 1.17 m, p99 3.62 m and a
// worst 4.21 m back over the ribbon beneath it, so 6 m clears every one of the
// 1,398 ends with margin. It shipped at 9 first and that cost 48 more edges
// their markings for nothing — see `tuning/road_markings.tres`.
uniform float fade_m : hint_range(0.0, 30.0) = 6.0;
// How much of that distance is the fade itself rather than a hard stop.
uniform float fade_softness_m : hint_range(0.1, 20.0) = 3.0;

group_uniforms markings;
// Each line type on its own switch, so a look can be judged one at a time —
// and so the one item here with no source behind it can be turned off outright.
uniform float draw_lane_lines : hint_range(0.0, 1.0) = 1.0;
uniform float draw_centre_line : hint_range(0.0, 1.0) = 1.0;
uniform float draw_bus_lane : hint_range(0.0, 1.0) = 1.0;
// ⚠️ **The one marking here that is not in the data** — see
// `tuning/road_markings.tres`, which is where that argument belongs because it
// is where someone turns it off.
uniform float draw_double_yellow : hint_range(0.0, 1.0) = 1.0;

// `flat` throughout: the whole payload is constant per edge, and interpolating a
// packed code between two vertices lands between two states — a road that is
// two-and-a-half lanes wide travelling in one-and-a-half directions.
varying flat float surface_class;
varying flat float lanes;
varying flat float direction;
varying flat float bus_lane;
// 1 where `U = lanes` is a real kerb, 0 where that is not known — on one half of
// a dual carriageway it is the middle of the road, and a kerbside no-stopping
// line put there is the loudest way to be wrong about a marking.
varying flat float offside_kerb;
// Where an opposed pair's two flows meet, in sixteenths of a lane beyond the
// centreline, `k - 1` steps; 0 for an edge that is not half of a pair. Read at
// the `join` below, which is where the reason it must be published lives.
varying flat float centre_at;
varying flat float drawn_m;
// What the two kerbs of this edge carry, from the codec. `flat` like everything
// else here: a kind interpolated between two vertices lands between two states.
varying flat float kerb_near;
varying flat float kerb_off;
// ⚠️ **The one varying here that must NOT be flat.** `COLOR.a` is where the ETL
// writes how far along the edge the restriction runs — 255 on the stations
// inside it and 0 on the stations outside — and interpolating it is the whole
// mechanism: `surface.py` inserts a pair of stations a quarter-metre either
// side of every boundary, so this ramps 0 to 1 over half a metre and the line
// stops where the source says it stops. Flat here would snap every restriction
// to whole triangles.
//
// It is per *rail*, which is what makes one channel carry two kerbs: the two
// rails of the carriageway strip are the two sides of the road, so a fragment
// on the nearside line reads ~95% of the nearside rail's value.
varying float restricted;
// ⚠️ **The sRGB conversion is hoisted out of the fragment shader, and that rests
// on an ETL invariant rather than on nothing.** `surface.py`'s `_rgba`
// broadcasts one colour over a whole strip and `fan` over a whole cap, so no
// triangle of this mesh ever spans two colours — which makes `flat` here exactly
// equal to converting per fragment, not an approximation of it. It is worth
// doing because the conversion is three `pow`s and the road is the largest
// surface in the frame: kerb and cap fragments were paying for it and then
// taking no other branch at all. If the ETL ever ships per-vertex road colour,
// this has to come back down.
varying flat vec3 albedo_linear;

void vertex() {
	// `floor(x + 0.5)` before anything else, on the codec's own promise that
	// every legal code is exact in float32 (max 131,071, against 24 bits).
	float packed = floor(UV2.x + 0.5);
	surface_class = floor(mod(packed, MARKING_LANES));
	lanes = floor(mod(packed / MARKING_LANES, MARKING_DIRECTION / MARKING_LANES));
	direction = floor(mod(packed / MARKING_DIRECTION, MARKING_BUS_LANE / MARKING_DIRECTION));
	bus_lane = floor(mod(packed / MARKING_BUS_LANE, MARKING_TRAM / MARKING_BUS_LANE));
	offside_kerb = floor(mod(packed / MARKING_OFFSIDE_KERB, MARKING_CENTRE / MARKING_OFFSIDE_KERB));
	centre_at = floor(mod(packed / MARKING_CENTRE, MARKING_CENTRE_SPAN));
	kerb_near = floor(mod(packed / MARKING_KERB_NEAR, MARKING_KERB_SPAN));
	kerb_off = floor(mod(packed / MARKING_KERB_OFF, MARKING_KERB_SPAN));
	drawn_m = UV2.y;
	restricted = COLOR.a;
	// ⚠️ Only `.rgb`. The hoist above rests on `surface.py:_rgba` broadcasting
	// one colour per strip, and that argument covers the colour and not the
	// alpha — which now varies per vertex on purpose. Folding the two into one
	// varying would make the extent flat and silently undo `P3-13`.
	albedo_linear = vertex_srgb_to_linear(COLOR.rgb);
}

// Coverage of a line of half-width `half_w` centred at `at`, over a fragment
// whose footprint in the same coordinate is `u ± w`.
//
// ⚠️ **Exact box-filter overlap, not a `smoothstep` pair, and the difference is
// a visible bug rather than a refinement.** A `smoothstep(half_w - w, half_w +
// w, |u - at|)` is right only while `w` is smaller than the line. Past that it
// converges on **0.5 everywhere** — so a distant lane line does not thin out,
// it smears across half a lane at half strength, and four kerbside yellows
// summing that way clamp to a solid yellow carriageway at the horizon. This
// returns the fraction of the fragment the line actually covers, which is what
// an infinite number of samples inside it would average to: 1 up close,
// `half_w / w` in the distance, and a clean fade in between with no fudge and
// no distance uniform. `city_facade_clean.gdshader`'s `band()` converges on its
// duty cycle for the same reason and records the same argument.
//
// ⚠️ `w` must be derived from `fwidth(u)`, never `fwidth(fract(u))`, which
// spikes to ~1 at every repeat boundary and renders each line as a wide grey
// smear — an artefact that reads as a lighting bug and is really a sampling one.
float line_coverage(float u, float at, float half_w, float w) {
	float lo = max(at - half_w, u - w);
	float hi = min(at + half_w, u + w);
	return max(hi - lo, 0.0) / (2.0 * w);
}

void fragment() {
	ALBEDO = albedo_linear;
	ROUGHNESS = road_roughness;
	METALLIC = 0.0;

	// Kerbs and caps carry a lane coordinate that means nothing to draw on — a
	// kerb's runs off both ends of the road, and a cap's is `(0, 0)`, which is
	// the nearside kerb line rather than a sentinel. Everything below is inside
	// this gate, so those two pay for the asphalt above and nothing else.
	//
	// ⚠️ **A gate rather than an early `return`, which Godot's shading language
	// rejects in a processor function** — "Using 'return' in the 'fragment'
	// processor function is incorrect". It is valid GLSL, so the mistake reads
	// as correct; what catches it is that the shader then fails to compile at
	// run time, and `tools/check.sh` exits 0 on that. Only a render and a
	// `grep -i "shader error"` sees it.
	if (surface_class == MARKING_CLASS_CARRIAGEWAY) {
		float u = UV.x;
		float v = UV.y;
		// ⚠️ **Both derivatives are taken here, outside every branch below.**
		// `fwidth` in non-uniform control flow is undefined, and `away` varies
		// continuously across a primitive — so a pixel quad straddling the fade
		// boundary would take a derivative under divergent flow. The `+ 1e-5` is
		// the other half of the same care: `w = 0` on a screen-space-flat quad
		// divides by zero. Both match the facade shader's helpers exactly.
		float du = fwidth(u) * 0.5 + 1e-5;
		float dv = fwidth(v) * 0.5 + 1e-5;

		// Distance to the nearer end of the ribbon **as drawn**, after the
		// junction trims — so zero is where the carriageway actually stops.
		// Taken from the edge's length per fragment rather than shipped per
		// vertex; `etl/pipeline/surface.py`'s codec block has the reason, and it
		// is not a small one. Applied as a multiplier rather than as a second
		// gate: it is 1 over most of the road, so branching on it would buy the
		// junction approaches a little and cost a level of nesting everywhere.
		float away = smoothstep(fade_m - fade_softness_m, fade_m, min(v, drawn_m - v));

		// The centre of the road. A lane boundary only when the lane count is
		// even, so it is taken from `lanes * 0.5` rather than from the divider
		// test — and a one-lane road has no centre to mark.
		float centre = lanes * 0.5;
		bool two_way = direction == DIRECTION_BOTH && lanes >= 2.0;
		// Where the road's two flows are separated, which is one of two places.
		// On a two-way street it is the middle of the ribbon. On one half of an
		// opposed pair — two one-way carriageways widened until they read as one
		// road — it is a line neither edge's own geometry marks, so the ETL
		// publishes where: the ribbons overlap, and `U = lanes` on either lands
		// inside the other's carriageway rather than at the join.
		//
		// The two are exclusive by construction (`centre_at` is only written on a
		// one-way edge), and `else if` is what says so — as two independent tests
		// they would both draw the day that stopped being true.
		float join = centre;
		bool separated = two_way;
		if (two_way) {
			join = centre;
		} else if (centre_at > 0.0) {
			join = centre + (centre_at - 1.0) / 16.0;
			separated = true;
		}
		// Two lines straddling the join, so the centre-to-centre pitch is one line
		// width plus the clear gap and each sits HALF of that off the join.
		// ⚠️ **Named a half-pitch because it is one** — this block already carries
		// one gap-versus-pitch trap (`centre_gap` is a clear gap, `yellow_gap` is
		// a pitch) and a third word with a fourth meaning is how the next reader
		// doubles it.
		//
		// 🔴 **Summed, and it must NOT be "fixed" to a `max`.** `centre_gap > 0`
		// makes the two paint intervals disjoint, so the sum *is* the coverage of
		// their union and is `<= 1` identically — the clamp below never truncates
		// it, at any distance. That is what separates this from the four-yellow
		// case `line_coverage` warns about, which clamps because a `smoothstep`
		// converges on 0.5 whatever the line width while an exact box filter
		// converges on `half_w / w`. A `max` here would halve the pair's far-field
		// brightness and be wrong. ⚠️ `railings.gdshader::bars()` combines with
		// `max` for the opposite and equally correct reason — a post crossing a
		// rail is one piece of steel — so the two files disagree on purpose.
		float centre_half_pitch = (centre_width + centre_gap) * 0.5;
		// How far the pair reaches from the join, for the suppressions below.
		float centre_reach = centre_half_pitch + centre_width * 0.5;
		float white = separated
			? draw_centre_line
				* (line_coverage(u, join - centre_half_pitch, centre_width * 0.5, du)
					+ line_coverage(u, join + centre_half_pitch, centre_width * 0.5, du))
			: 0.0;

		// Lane dividers. Only the nearest boundary can be within a line's width
		// of this fragment, so this is one test rather than a loop over the lane
		// count.
		//
		// ⚠️ The dividing line is suppressed only where one is actually **drawn**.
		// Keying it on `two_way` alone put a gap in the dividers whenever
		// `draw_centre_line` was turned down, which defeats the dial — and it
		// missed the opposed-pair join entirely, which lands inside the same
		// window (the unnamed pair's is at `U = 1.19`, a fifth of a lane from the
		// divider at `k = 1`) and would have run a dashed line beside a solid one.
		//
		// ⚠️ **Floored by the geometry rather than replaced by it.** The quarter
		// lane above is editorial; `max` is what stops a wider `centre_gap` or
		// `centre_width` — both tunable to 0.3 — putting a dash through the pair
		// with nothing to catch it. Shipped, the geometric term is 0.0985 against
		// the editorial 0.25; at the top of both ranges it is 0.475.
		//
		// ⚠️ **`<=`, because the join lands on the codec's own grid.** `centre_at`
		// is in sixteenths, so `abs(k - join)` is always a multiple of 1/16 and
		// `j = 4` is *exactly* 0.25 — reachable and deterministic, not a
		// floating-point near-miss. `centre_at 13 / lanes 3` is published in this
		// region and puts its divider there; under `<` the dash draws with 0.78 m
		// of clear asphalt beside the pair, which is what the window exists to
		// prevent.
		float k = floor(u + 0.5);
		float divider_clear = max(CENTRE_DIVIDER_CLEARANCE_U, centre_reach + line_width * 0.5);
		float centre_here = separated && abs(k - join) <= divider_clear ? draw_centre_line : 0.0;
		if (k > 0.5 && k < lanes - 0.5) {
			// The dash, in metres along the road. Phase is offset half a period
			// so the wrap lands mid-gap — otherwise the leading edge of every
			// dash is the wrap point and steps 0 to 1 with no antialiasing.
			float period = dash_length_m + dash_gap_m;
			float phase = fract(v / period + 0.5) * period;
			float dash = line_coverage(phase, period * 0.5, dash_length_m * 0.5, dv);
			white += draw_lane_lines * (1.0 - centre_here) * dash
				* line_coverage(u, k, line_width * 0.5, du);
		}

		// The bus lane is the nearside one, so what marks it is the boundary at
		// U = 1 — continuous, and wider than a lane divider. Skipped where that
		// boundary is already the centre line of a two-lane two-way street.
		float bus_clear = max(CENTRE_DIVIDER_CLEARANCE_U, centre_reach + bus_width * 0.5);
		if (bus_lane > 0.5 && lanes > 1.5 && !(separated && abs(join - 1.0) <= bus_clear)) {
			white += draw_bus_lane * line_coverage(u, 1.0, bus_width * 0.5, du);
		}

		// The kerbside pairs. `un` folds the offside onto the nearside, which is
		// exact — a reflection preserves |du| — and halves the work.
		//
		// The fold happens only where the offside is a **known kerb**. It used to
		// key on `two_way`, a proxy that got the right answer for the wrong
		// reason; the ETL now answers it directly from the buried-kerb pass, so a
		// one-way street with a real kerb gets its line and one half of a dual
		// carriageway still does not. A missing line is quieter than a
		// no-stopping line down the middle of a road.
		//
		// ⚠️ **Since `P3-13` this draws a *sourced* restriction, not a decorative
		// one.** `kerb_near`/`kerb_off` say which line each kerb carries and
		// `restricted` says how far along it runs, both from the `NSR` layer. The
		// city used to paint a double yellow on every kerb it had, which asserted
		// a legal restriction on 3.6x the kerb that carries one (`Q54`).
		float yellow = 0.0;
		if (draw_double_yellow > 0.0) {
			float un = offside_kerb > 0.5 ? min(u, lanes - u) : u;
			// Which kerb this fragment belongs to, recovered *after* the fold —
			// the fold is what threw the information away. Past the middle of the
			// ribbon it is the offside; below it, and on any edge whose offside is
			// not a known kerb, it is the nearside.
			float kind = (offside_kerb > 0.5 && u * 2.0 > lanes) ? kerb_off : kerb_near;
			if (kind >= MARKING_KERB_SINGLE) {
				yellow = line_coverage(un, yellow_inset, yellow_width * 0.5, du);
				if (kind >= MARKING_KERB_DOUBLE) {
					yellow += line_coverage(un, yellow_inset + yellow_gap, yellow_width * 0.5, du);
				}
				// The extent, as a ramp rather than a test. `restricted` crosses
				// half over the 0.5 m the ETL's inserted station pair spans, so
				// this lands the end of the line within a couple of centimetres
				// of where the source puts it — and antialiases it, which a
				// `> 0.5` would not. **No derivative is taken inside this
				// branch**; `du` and `dv` were both read at the top of the
				// carriageway block, which is what makes the branch legal.
				yellow *= draw_double_yellow * smoothstep(0.4, 0.6, restricted);
			}
		}

		white = clamp(white, 0.0, 1.0) * away;
		yellow = clamp(yellow, 0.0, 1.0) * away;

		// Blended by weight rather than by a test on which is non-zero: the two
		// only meet across an antialiased edge, and choosing there is what makes
		// a line change colour along its own boundary pixel.
		float total = white + yellow;
		vec3 paint = (line_colour * white + yellow_colour * yellow) / max(total, 1e-5);

		// Not opaque: worn paint is what keeps a line from reading as a decal
		// laid on the road rather than as something driven over.
		float painted = min(total, 1.0);
		ALBEDO = mix(albedo_linear, paint, painted * paint_opacity);
		ROUGHNESS = mix(road_roughness, paint_roughness, painted);
	}
}
