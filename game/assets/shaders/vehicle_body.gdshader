// Clearcoat on the taxi, priced per surface (`P3-11c`).
//
// A `StandardMaterial3D` carries one roughness for a whole surface, and the
// body is one merged primitive holding seven flat colours — so paint, glazing
// and lamp lenses all had to share a value. They do not want the same one, and
// that is the whole reason this file exists.
//
// ⚠️ **What decides the shape here is that the reflection needs a *gradient*,
// not a strength.** A single flat sky colour was tried at two strengths and
// judged wrong in both directions — faint at 0.14, a panel painted blue at 0.34
// — which is the identical failure `ART_DESIGN.md` records against the facades:
// "a single reflection colour is why glass read as a swatch rather than a
// mirror". With the three bands below in, the glazing's `L*` spread went
// `sd 0.05 -> 6.35`, and that structure is what reads as glass.
//
// ⚠️ **Gloss on paint is priced, not free, and the prices are measured** at the
// `taxi` audit cameras (red bodywork `C*`, t04.50, in sun):
//
//   matte, as it shipped before this file          79.06
//   `paint_reflect 0.12`, roughness 0.9            73.65   (-5.42)
//   `paint_reflect 0.12`, roughness 0.55           69.86   (-9.20)
//
// ...all three at `fresnel_power` 4.0. Shipped is **71.63 (-7.43)**, because
// tightening the fresnel to 6.5 refunds 1.77 of that for 0.06 `L*` of glazing.
//
// ⚠️ **`fresnel` is what makes any of this affordable, and reads as decoration
// until it is ablated.** Forced to 1.0 — the reflection landing at every angle
// rather than grazing ones — the paint loses a *further* `C* 13.75`, down to
// 56.11. It is the term keeping the clearcoat off a panel that faces the
// camera, which is what `paint_face_on` 0.06 exists to say.
//
// The cost is real and roughly linear in what is asked for. It is affordable
// because the property it threatens survives it: at 71.63 the car is still 9x
// the frame median of 7.5 and clear of the city's 99th percentile of 39.8, so
// `ART_DESIGN.md`'s "the only chromatic object in the frame" holds at the
// bottom of the dial. ⚠️ The residual risk is **recognition** rather than art —
// red is an identifying feature of the car, and `P3-9a` grades exactly that.
//
// `METALLIC` is nailed to zero throughout: metalness with nothing to reflect
// renders as sky-coloured plastic.
//
// The input that cannot be derived from geometry is which surface is which, and
// `tools/make_vehicle.py` ships it in `TEXCOORD_0`:
//
//   UV.x  `floor()` is the switched circuit — which of the car's lamps, if any,
//         turns this surface on. Reserved and zero before `P3-11d`.
//   UV.y  `floor()` is the surface marker. The body is one primitive, so
//         nothing else tells a windscreen from the bodywork around it.
shader_type spatial;

render_mode cull_back;

// Must match `MARKER_*` in `tools/make_vehicle.py`.
const float MARKER_PAINT = 0.0;
const float MARKER_GLASS = 1.0;
const float MARKER_LAMP = 2.0;
// Must match `CIRCUIT_*` in `tools/make_vehicle.py`. Only `NONE` is named here:
// the rest are the channels of `lamp_lit` then `lamp_front` in order, and
// enumerating them again as constants would be a second copy of the ordering
// with nothing enforcing it.
const float CIRCUIT_NONE = 0.0;
// Where the circuits split across two vectors, and how many they hold between
// them. The seam is at 4 because that is a `vec4`, not because anything about
// the car divides there — so it is named once and the total is derived from it
// rather than both being written down and left to disagree.
const int CIRCUIT_SEAM = 4;
const int CIRCUIT_COUNT = 2 * CIRCUIT_SEAM;
// ⚠️ `MARKER_TRIM` (3.0) is shipped by the ETL and takes no branch of its own —
// it shares paint's clearcoat, for the reason given at that branch. Carried
// separately anyway, on the tiles' ground-marker reasoning: it costs nothing to
// keep separable now, and a later brightwork treatment would otherwise need a
// second pass over the vertex format and a rebuild of every vehicle.

// What the glazing reflects. There is no probe and no SSR behind this — it is
// three colours and the reflected ray's own elevation choosing between them.
//
// ⚠️ **A single reflection colour was the first attempt and it read as a swatch,
// which is the mistake `ART_DESIGN.md` already records against the facades.**
// Real glazing shows the sky *gradient*; below the horizon it reflects the city,
// which is darker than either band. Turning a flat colour *up* does not fix it —
// at `glass_reflect 0.34` the backlight read as a panel painted blue, and the
// fault was flatness rather than strength.
//
// ⚠️ **What moves this on a car is roll and pitch, not steering** — and the
// first version of this comment claimed the opposite. `bounced.y` is the only
// thing selecting a band, and a vector's `y` is *invariant under yaw*: turning
// rotates the view ray and the normal about the vertical axis together, so a
// flat corner changes nothing here. Cornering lean, acceleration squat, braking
// dive and kerbs are what tilt the normal out of plane. Measured on a skidpad
// circle at fixed lighting, the glazing moves `L* 23.85-27.87` across headings —
// real, worth having, and about four points rather than the sweep first
// claimed. Matched to the facades' values so the car and the city agree about
// what the sky is.
uniform vec3 sky_zenith : source_color = vec3(0.24, 0.47, 0.78);
uniform vec3 sky_horizon : source_color = vec3(0.85, 0.91, 0.96);
uniform vec3 ground_reflection : source_color = vec3(0.32, 0.33, 0.35);

group_uniforms glass;

// How much of the reflection above the glazing takes at a grazing angle.
uniform float glass_reflect : hint_range(0.0, 1.0) = 0.45;
// ⚠️ Not zero at zero degrees. Mirror glass is not transparent faced squarely,
// and a fresnel that falls to nothing head-on leaves the backlight a flat black
// rectangle at exactly the angle the chase camera holds it at — which is the
// angle the player sees for the whole game.
uniform float glass_face_on : hint_range(0.0, 1.0) = 0.25;
uniform float fresnel_power : hint_range(1.0, 8.0) = 6.5;
uniform float glass_roughness : hint_range(0.0, 1.0) = 0.14;

group_uniforms lamp;

// The lamp lenses, and the reason they are a marker rather than a colour: the
// tail cluster is three lenses stacked — amber, white, red — and the bottom one
// is `RED` on `RED` bodywork with no bezel behind it, so it reads as a bump
// rather than a lamp. The bezel was removed on request with that trade
// understood, and recolouring the lens is the earlier bug (a white tail lamp).
// A lens is glass over a reflector, so separating it by *shading* takes nothing
// off the palette and reverses no decision.
uniform float lamp_roughness : hint_range(0.0, 1.0) = 0.35;
uniform float lamp_reflect : hint_range(0.0, 1.0) = 0.06;

// How brightly a switched lens burns when its circuit is live (`P3-11d`).
//
// ⚠️ **This is the fix `P3-11c` could not reach, and it reverses none of the
// decisions that closed the other two.** The red tail lens is `RED` on `RED`
// bodywork with no bezel; shading alone moved it `L*` +0.77 in shade and +0.41
// in sun, which that round recorded as "real, and not enough". Recolouring the
// lens is the earlier bug and a white tail lamp besides, and faking the removed
// bezel is that reversal wearing a different hat. A lens that *lights* separates
// itself by emitting its own authored colour, which changes no swatch and puts
// nothing back behind the cluster. It also only claims the lens when the car is
// actually braking — the unlit case is still the one `P3-11c` measured.
//
// ⚠️ **Above 1.0 on purpose.** `clean_daylight.tres` glows on an HDR threshold
// of 1.0, so a lens below that is merely a brighter swatch — the bloom is what
// reads as a lamp rather than as paint, and it is the whole difference at the
// distance a chase camera holds. The value is priced against the sunlit
// bodywork next to it, not chosen for a dark scene: this is a daytime game and
// a brake lamp competing with direct sun is the hard case, not the easy one.
//
// ⚠️ **The dial is not brightness against darkness — it is bloom against
// redness**, and that is worth knowing before turning it up. The tonemap is
// ACES, which desaturates a clipped channel toward white, and the lens's red
// channel is already at 255 by 1.2. Everything above that lands on green and
// blue. Measured on the high-level strip, same 294 px, braking at `t03.30`:
//
//   0.0 (ablated)   L*  2.29   C*  9.35    sRGB ( 16,   4,  15)
//   1.2             L* 67.04   C* 56.44    sRGB (255, 123, 120)
//   1.6  shipped    L* 72.72   C* 44.34    sRGB (255, 149, 142)
//   2.3             L* 79.17   C* 31.81    sRGB (255, 176, 170)
//
// 1.6 is the knee: enough over the threshold to carry a visible halo, still
// `C*` 44 at the core. 2.3 is a white lamp with a red glow round it, which is
// the failure `ART_DESIGN.md` already names for the tail cluster.
//
// One value for every lens, which is only affordable because the emission below
// is normalised: the level a lens is authored at no longer sets how hard it
// burns, so a near-black strip and a cream reverse lamp can share this dial.
uniform float lamp_emission : hint_range(0.0, 8.0) = 1.6;

// Which circuits are live this frame, in `CIRCUIT_*` order less one:
// x brake, y reverse, z indicator left, w indicator right, then on into
// `lamp_front` below. 0 is out, 1 is full.
//
// ⚠️ **`instance uniform`, and that is not an optimisation.** `vehicle_body.tres`
// is one shared material — `generated_scene_import.gd` hands the same resource
// to every mesh that asks for `vehicle_body` by name, and `ART_DESIGN.md`'s
// roster puts an AI red taxi on the streets alongside the player's. A plain
// uniform is a property of the *material*, so the first car to brake would brake
// every taxi in Wan Chai. Lamp state is per car, so it goes in the per-instance
// channel; `sun_toward` above stays a plain uniform for the mirror-image reason
// — there is one sun, and every car agrees about where it is.
//
// Written by `scripts/vehicle/vehicle_lamps.gd`. Unset instances keep the
// default, which is every lamp out — so the `taxi_builtin` spike, which carries
// no lamp rig, simply drives around with dark lenses rather than failing.
instance uniform vec4 lamp_lit = vec4(0.0);

// Circuits 5-8, in the same ordering: x side lamps, y head lamps, z and w
// unwired. The car's *front* lamps, and they are in a second vector for one
// reason only — `lamp_lit` is a `vec4` and its four channels were spent.
//
// ⚠️ **A second `instance uniform` rather than a wider payload, and the split
// is arbitrary.** Nothing about a side lamp belongs with a head lamp more than
// with a brake lamp; the seam is where GLSL put it. So the *ordering* is the
// contract and this declaration is not — a fifth channel added to the front of
// the list would silently move every lens behind it into the other vector.
// `CIRCUIT_COUNT` is what the bounds guard reads, so that stays true either way.
//
// ⚠️ Two of these ship at zero and that is not spare capacity to raid casually:
// Godot caps instance uniforms per shader, and a third vector spends a slot on
// a car that has run out of lenses to light long before it runs out of channels.
instance uniform vec4 lamp_front = vec4(0.0);

group_uniforms paint;

// Clearcoat. ⚠️ **The measurement that refused gloss on paint refused a
// *uniform* one, and this is not that.** Dropping roughness across the whole
// body sampled flat ambient over every panel and washed the red with sky —
// `C* 79.06 -> 70.08`, `L*` rising as `C*` fell. A waxed panel does not read by
// being uniformly brighter: it reads by picking up the *sky at its shoulders and
// the dark ground below its beltline*, concentrated where the surface turns away
// from the eye. So the reflection is the same three-band gradient the glazing
// uses, `paint_reflect` is small, and `paint_face_on` is near zero — a panel
// square to the camera keeps its full red, and only the curvature catches
// anything. That is the difference between wax and a wash.
uniform float paint_roughness : hint_range(0.0, 1.0) = 0.55;
uniform float paint_reflect : hint_range(0.0, 1.0) = 0.12;
// ⚠️ Deliberately not `glass_face_on`'s 0.25. Mirror glass is not transparent
// faced squarely and must not go black head-on; paint is the opposite case —
// head-on is exactly where its colour must survive untouched.
uniform float paint_face_on : hint_range(0.0, 1.0) = 0.06;

group_uniforms glint;

// The sun glint — a highlight that sweeps as the car changes heading.
//
// ⚠️ **`SPECULAR` was tried first and is the wrong lever, measured.** Raising it
// 0.5 -> 0.9 brightened the glazing's mean `L*` by 5.8 while its p99 spread
// across headings moved only 2.69 -> 3.54: a uniform lift, not a moving
// hotspot. The cause is the same one behind everything else in this file —
// `SPECULAR` scales *ambient* specular as well as the sun's, and with no probes
// the ambient half dominates, so the glass went back to reading as a panel
// painted blue. Reverted to Godot's 0.5 default.
//
// So the sun is isolated explicitly. ⚠️ **`sun_toward` is fed by
// `sun_glint.gd` from the scene's actual `DirectionalLight3D`** rather than
// authored here: a hand-copied vector would be a second copy of the rig's
// rotation and would drift silently the first time the sun is retuned or a
// night mode is added — the desync shape `P3-11`'s chassis guard exists for.
// The script reads the authority; this uniform is only where it lands.
// Unit-length and already pointing *at* the sun — `sun_glint.gd` owns both
// guarantees, so this is used raw.
uniform vec3 sun_toward = vec3(0.0, 1.0, 0.0);
uniform float glint_strength : hint_range(0.0, 4.0) = 1.1;
uniform float glint_sharpness : hint_range(1.0, 256.0) = 48.0;

varying flat float marker;
// `flat` for the same reason `marker` is: every vertex of a lens carries the
// same circuit, and an interpolated one would land between two channels at the
// seam between a lamp and the paint it is seated in.
varying flat float circuit;
// World space, for the reflected ray. Interpolated rather than `flat`: the
// gradient has to vary *across* a screen, or a windscreen is one colour again
// and the whole point of the three bands above is lost.
varying vec3 world_pos;
varying vec3 world_n;

void vertex() {
	marker = floor(UV.y);
	circuit = floor(UV.x);
	world_pos = (MODEL_MATRIX * vec4(VERTEX, 1.0)).xyz;
	world_n = normalize(MODEL_NORMAL_MATRIX * NORMAL);
}

// `COLOR_0` is sRGB-encoded and nothing converts it for free. Godot 4 has no
// `vertex_color_is_srgb` render mode — it survives only as a `BaseMaterial3D`
// flag, and this material is not one — so every shader carries its own, exactly
// as the two facade shaders do. Skipping it does not merely lighten the car:
// sRGB read as linear is brighter than it should be, and brightness the albedo
// did not ask for is brightness that does not vary with albedo (`Q27`).
vec3 vertex_srgb_to_linear(vec3 c) {
	return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

void fragment() {
	vec3 albedo = vertex_srgb_to_linear(COLOR.rgb);

	bool is_glass = abs(marker - MARKER_GLASS) < 0.5;
	bool is_lamp = abs(marker - MARKER_LAMP) < 0.5;

	// One fresnel serves both reflective markers; the marker chooses how much of
	// it lands. Computed unconditionally — it is a handful of ALU and branching
	// around it on a mesh this small buys nothing.
	float fresnel = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), fresnel_power);

	// The mirror. Where the reflected ray points decides what it sees, so a
	// screen darkens toward the city as the car turns and brightens toward the
	// zenith as it pitches — which a single colour cannot do at any strength.
	vec3 to_surface = normalize(world_pos - INV_VIEW_MATRIX[3].xyz);
	vec3 bounced = reflect(to_surface, normalize(world_n));
	vec3 mirrored = mix(
		ground_reflection,
		mix(sky_horizon, sky_zenith, clamp(bounced.y, 0.0, 1.0)),
		smoothstep(-0.08, 0.08, bounced.y)
	);

	// Isolated from the sun alone, so it moves with heading where the sky
	// gradient cannot: `bounced.y` is invariant under yaw, `bounced · sun` is
	// not. Confined to glass and lenses — on paint it is a second way to spend
	// the chroma the clearcoat is already paying for.
	//
	// ⚠️ **Guarded, where `fresnel` above is not, and the difference is which
	// branches read it.** `fresnel` is consumed on all three, so a test around
	// it would only add work. This is read by two, and paint is most of a car
	// body — so without the guard the `pow` runs on the majority of fragments
	// that discard it.
	float glint = 0.0;
	if (is_glass || is_lamp) {
		glint = pow(max(dot(bounced, sun_toward), 0.0), glint_sharpness);
	}

	float roughness = paint_roughness;
	if (is_glass) {
		roughness = glass_roughness;
		albedo += sky_horizon * glint * glint_strength;
		albedo = mix(albedo, mirrored, glass_reflect * mix(glass_face_on, 1.0, fresnel));
	} else if (is_lamp) {
		roughness = lamp_roughness;
		// The lens glows *its own* colour, taken before the reflection is mixed
		// in: a lit lamp is brighter than what it is reflecting, so letting the
		// sky tint the emission is the swatch problem again, one surface further
		// on. Red stays red, amber stays amber, and the white reverse lens is the
		// only one that goes near white — which is what a reverse lamp is.
		//
		// ⚠️ **The hue, normalised — not the albedo scaled — and the high-level
		// brake lamp is why.** An unlit lens is dark because of what sits behind
		// it, not because it is a weaker bulb, and `albedo * emission` conflates
		// the two: it makes "invisible when off" and "bright when on" the same
		// dial pulled in opposite directions. The strip in the backlight has to
		// be both, so it is authored near-black (`DEEP_RED`) and burns at the
		// same intensity as every other lens. Dividing by the largest channel
		// keeps the hue and discards the level, which is the half that belongs
		// to the reflector rather than to the lamp.
		//
		// ⚠️ Dynamic index rather than a comparison per circuit, which is why
		// `CIRCUIT_*` is an ordering and not a set — and ⚠️ **bounded at both
		// ends, because an out-of-range index into a `vec4` is undefined on a
		// Mobile driver rather than an error.** `CIRCUIT_NONE` lands on -1, so
		// the lower bound *is* the never-lights test; the upper one is a ninth
		// circuit the generator could add before anyone widened the payload
		// again, which is the same one-swatch-away hazard the divide below
		// already pays for. `P3-11d` shipped this guard against exactly the
		// widening that has now happened.
		int channel = int(circuit - CIRCUIT_NONE) - 1;
		if (channel >= 0 && channel < CIRCUIT_COUNT) {
			// ⚠️ **Both vectors are indexed with the same in-range slot, and
			// writing `lamp_front[channel - 4]` instead is the bug this line is
			// shaped to avoid.** The spec says a ternary evaluates one operand,
			// but Mobile drivers flatten branches routinely — and a flattened
			// `channel - 4` at `channel = 0` is the negative index the bound
			// above exists to stop, arriving through the fix for it. Masking to
			// the low two bits is `channel - 4` on the far side of the seam and
			// harmless on the near side, so neither operand can be out of range
			// whichever way the driver compiles this.
			int slot = channel & (CIRCUIT_SEAM - 1);
			float level = channel < CIRCUIT_SEAM ? lamp_lit[slot] : lamp_front[slot];
			// The guard is for a black lens, which is not authored today and is
			// one swatch away from being: it would divide by zero and emit NaN,
			// which the Mobile renderer resolves as a white hole in the car.
			float peak = max(albedo.r, max(albedo.g, albedo.b));
			vec3 hue = albedo / max(peak, 0.001);
			EMISSION = hue * level * lamp_emission;
		}
		albedo += sky_horizon * glint * glint_strength * 0.5;
		albedo = mix(albedo, mirrored, lamp_reflect * fresnel);
	} else {
		// Paint and trim. `MARKER_TRIM` shares this branch rather than taking one
		// of its own: silver is a near-neutral, so it has the least hue of its own
		// to defend and is the surface a sky wash disfigures first — the ice-blue
		// roof is that failure already recorded. It gets the clearcoat and nothing
		// else, which is what brightwork is.
		albedo = mix(albedo, mirrored, paint_reflect * mix(paint_face_on, 1.0, fresnel));
	}

	ALBEDO = albedo;
	// Nailed down rather than left at a default. The Mobile renderer has no SSR
	// and no reflection probes, so a metal surface has nothing to reflect and
	// renders as sky-coloured plastic — see this file's header, and
	// `ART_DESIGN.md`'s anti-goals, which refuse the metalness workflow for
	// exactly this reason and not as a matter of taste.
	METALLIC = 0.0;
	ROUGHNESS = roughness;
}
