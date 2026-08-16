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
//   `paint_reflect 0.12`, roughness 0.55           69.86   (-9.20)  <- shipped
//
// The cost is real and roughly linear in what is asked for. It is affordable
// because the property it threatens survives it: at 69.86 the car is still 9x
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
//   UV.x  unused, reserved. A tile spends it on metres above the object's base;
//         nothing on a 4 m car needs that.
//   UV.y  `floor()` is the surface marker. The body is one primitive, so
//         nothing else tells a windscreen from the bodywork around it.
shader_type spatial;

render_mode cull_back;

// Must match `MARKER_*` in `tools/make_vehicle.py`.
const float MARKER_PAINT = 0.0;
const float MARKER_GLASS = 1.0;
const float MARKER_LAMP = 2.0;
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
uniform float fresnel_power : hint_range(1.0, 8.0) = 4.0;
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
// So the sun is isolated explicitly. ⚠️ **`sun_direction` is fed by
// `sun_glint.gd` from the scene's actual `DirectionalLight3D`** rather than
// authored here: a hand-copied vector would be a second copy of the rig's
// rotation and would drift silently the first time the sun is retuned or a
// night mode is added — the desync shape `P3-11`'s chassis guard exists for.
// The script reads the authority; this uniform is only where it lands.
uniform vec3 sun_direction = vec3(0.0, -1.0, 0.0);
uniform float glint_strength : hint_range(0.0, 4.0) = 1.1;
uniform float glint_sharpness : hint_range(1.0, 256.0) = 48.0;

varying flat float marker;
// World space, for the reflected ray. Interpolated rather than `flat`: the
// gradient has to vary *across* a screen, or a windscreen is one colour again
// and the whole point of the three bands above is lost.
varying vec3 world_pos;
varying vec3 world_n;

void vertex() {
	marker = floor(UV.y);
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
	float glint = pow(max(dot(bounced, -normalize(sun_direction)), 0.0), glint_sharpness);

	float roughness = paint_roughness;
	if (is_glass) {
		roughness = glass_roughness;
		albedo += sky_horizon * glint * glint_strength;
		albedo = mix(albedo, mirrored, glass_reflect * mix(glass_face_on, 1.0, fresnel));
	} else if (is_lamp) {
		roughness = lamp_roughness;
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
