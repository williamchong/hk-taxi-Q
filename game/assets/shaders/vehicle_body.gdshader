// Clearcoat on the taxi, priced per surface (`P3-11c`).
//
// A `StandardMaterial3D` carries one roughness for a whole surface, and the
// body is one merged primitive holding seven flat colours — so paint, glazing
// and lamp lenses all had to share a value. They do not want the same one, and
// that is the whole reason this file exists.
//
// ⚠️ **For glazing and lenses, what decides the shape here is that the
// reflection needs a *gradient*, not a strength.** A single flat sky colour was tried at two strengths and
// judged wrong in both directions — faint at 0.14, a panel painted blue at 0.34
// — which is the identical failure `ART_DESIGN.md` records against the facades:
// "a single reflection colour is why glass read as a swatch rather than a
// mirror". With the three bands below in, the glazing's `L*` spread went
// `sd 0.05 -> 6.35`, and that structure is what reads as glass.
//
// ⚠️ **Paint takes the painted gradient again (`Q248`), over `Q215`'s
// `CLEARCOAT`.** `P3-11c` mixed it into the paint's albedo and paid for it in
// chroma (`C*` 79.06 matte -> 71.63 shipped, at the `taxi` t04.50 camera);
// `Q215` took it out and left the engine's lobe. `Q248` puts it back on the
// user's pick from a sheet, knowing the price: a flat panel under a flat mix
// was a wash, and what changed is the crown below, which turns it into a
// gradient across the panel. `paint_reflect` 0 is `Q215`'s car.
// ⚠️ The residual risk is still **recognition** — red identifies the car, and
// `P3-9a` grades exactly that; `clearcoat` 0 is the matte car.
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

#include "res://assets/shaders/colour.gdshaderinc"

// Must match `MARKER_*` in `tools/make_vehicle.py`.
const float MARKER_PAINT = 0.0;
const float MARKER_GLASS = 1.0;
const float MARKER_LAMP = 2.0;
const float MARKER_TRIM = 3.0;
// Paint a `MultiMesh` instance may repaint (`Q167`): a parked kind's livery
// panels, shaded as paint and coloured from `INSTANCE_CUSTOM` (sRGB, `a` 1 to
// apply; `ParkedLayer` writes it) when its alpha is set. The player's taxi
// ships no such vertex, so it cannot be touched.
const float MARKER_LIVERY = 4.0;
// Glass with a saloon lit behind it (`tools/make_parked.py`'s `Shape.cabin`): the
// glazing by day, and at night it burns `cabin_light` by `night_lights`. No
// per-instance state: a bus at its stop and a tram in service both have their
// lights on, and neither is ever a switched-off car.
const float MARKER_CABIN = 5.0;
// The same at `cabin_glow_dim`: a minibus's saloon is dimmer than a bus's.
const float MARKER_CABIN_DIM = 6.0;
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
// `MARKER_TRIM` shares paint's branch and its `CLEARCOAT`, and adds the sun's
// glint (`Q248`) — the brightwork treatment it was carried separately for.

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
// The rig's hour (`Q160`; `city_facade_clean.gdshaderinc` has the account): the
// three colours below are a noon sky, and this is what dims the mirror with it.
global uniform vec3 sky_light;
// 0 by day, 1 at full night (`Q160`): a moving car's tail and head lamps.
global uniform float night_lights;
// 0 at rest to 1 at the player's full speed (`cel_outline.gdshader`): the
// detail lines thin and fade with the city's.
global uniform float outline_speed;
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

// A MOVING car's lamps, for a `MultiMesh` instance (`P3-3c`). An `instance
// uniform` is one per node, so a fleet in one `MultiMesh` cannot use
// `lamp_lit`; `TrafficSystem` writes its state into `INSTANCE_CUSTOM.a` above
// the livery's bit instead: `a = livery + 2 * running + 4 * braking + 8 * left
// + 16 * right + 32 * for hire`, small integers a half float carries exactly. A switched-off
// parked car writes 0 or 1 and every circuit stays dark — the difference the
// user asked to see (2026-10-29). Left and right are the indicators (`P3-3f`), both at once a
// stopping car's hazards; they flash at `traffic_blink_hz` for
// `traffic_blink_duty` of each beat, each instance on its own phase.
// Running: the head lamps at `traffic_day_lamps` by day, full at night, and the
// brake lens at `traffic_tail_lit` scaled by the night, and a tram's side lamps
// at `traffic_side_lit`; braking: the brake lens full, day or night.
uniform float traffic_day_lamps : hint_range(0.0, 1.0) = 0.5;
uniform float traffic_tail_lit : hint_range(0.0, 1.0) = 0.35;
// A tram's side lamps while it runs, day or night. 0.75 of `lamp_emission` is the
// 1.2 of the table above: at full 1.6 the red lens reads salmon.
uniform float traffic_side_lit : hint_range(0.0, 1.0) = 0.75;
// Set on the library's material from `vehicle_lamps.tres` (`VehicleLampsProfile.
// wire_blink`), the taxi's own beat: no second copy here, so an unwired
// material's indicators stay dark rather than flash at a guess.
uniform float traffic_blink_hz : hint_range(0.0, 4.0) = 0.0;
uniform float traffic_blink_duty : hint_range(0.0, 1.0) = 0.0;
// A moving taxi's roof sign while it is for hire (`Q183`): bit 32 above the
// livery's, at the player's `sign_lit`, set with the beat by `wire_blink`. 0 on an
// unwired material, so a sign stays dark rather than burn at a guess.
uniform float traffic_sign_lit : hint_range(0.0, 1.0) = 0.0;
// Must match `CIRCUIT_BRAKE` and `CIRCUIT_HEADLAMP` in `tools/make_vehicle.py`,
// less one, as `channel` below counts them.
const int CHANNEL_BRAKE = 0;
const int CHANNEL_HEADLAMP = 5;
// `CIRCUIT_SIDELAMP`, less one: a tram's small lamps.
const int CHANNEL_SIDELAMP = 4;
// `CIRCUIT_INDICATOR_L` and `_R`, less one.
const int CHANNEL_INDICATOR_L = 2;
const int CHANNEL_INDICATOR_R = 3;
// `CIRCUIT_ROOFSIGN`, less one.
const int CHANNEL_ROOFSIGN = 6;

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
// channel; `sun_toward` below stays a plain uniform for the mirror-image reason
// — there is one sun, and every car agrees about where it is.
//
// Written by `scripts/vehicle/vehicle_lamps.gd`. Unset instances keep the
// default, which is every lamp out — so a car carrying no lamp rig simply drives
// around with dark lenses rather than failing. An AI roster car too far away to
// be worth switching is the case that matters now; the `taxi_builtin` spike was
// the original one, and `Q50` retired it.
//
// ⚠️ **`VEHICLE_BATCHED` drops both to constants** (`VehicleBodyBatch`): every
// node drawn with an `instance uniform` holds 16 slots of the global buffer,
// which the web renderer caps at its uniform block (16 KB on this Mac's WebGL2:
// 1,024 slots, about 60 nodes), and each parked cell's `MultiMesh` is a node.
// A batch reads its lamps from
// `INSTANCE_CUSTOM.a` and nobody writes its instance channels, so the
// constants are the zero it read anyway; only the player's car keeps these.
#ifdef VEHICLE_BATCHED
const vec4 lamp_lit = vec4(0.0);
#else
instance uniform vec4 lamp_lit = vec4(0.0);
#endif

// Circuits 5-8, in the same ordering: x side lamps, y head lamps, z the roof
// sign, w unwired. Mostly the car's *front* lamps, and they are in a second
// vector for one reason only — `lamp_lit` is a `vec4` and its four channels
// were spent. ⚠️ The roof sign is the channel that breaks that description, and
// it is here because `z` was the next free slot rather than because it belongs
// with the head lamps: it answers to whether the car is in service, not to the
// light. The seam carries no meaning — see the note below.
//
// ⚠️ **A second `instance uniform` rather than a wider payload, and the split
// is arbitrary.** Nothing about a side lamp belongs with a head lamp more than
// with a brake lamp; the seam is where GLSL put it. So the *ordering* is the
// contract and this declaration is not — a fifth channel added to the front of
// the list would silently move every lens behind it into the other vector.
// `CIRCUIT_COUNT` is what the bounds guard reads, so that stays true either way.
//
// ⚠️ One of these ships at zero — `w`, since the roof sign took `z` — and it is
// not spare capacity to raid casually:
// Godot caps instance uniforms per shader, and a third vector spends a slot on
// a car that has run out of lenses to light long before it runs out of channels.
#ifdef VEHICLE_BATCHED
const vec4 lamp_front = vec4(0.0);
#else
instance uniform vec4 lamp_front = vec4(0.0);
#endif

group_uniforms cabin;

// A saloon's lights seen through its windows at full night (`Q177`). Under the
// 1.0 glow threshold on purpose: a lit room, not a lamp.
uniform vec3 cabin_light : source_color = vec3(1.0, 0.84, 0.56);
uniform float cabin_glow : hint_range(0.0, 4.0) = 0.25;
uniform float cabin_glow_dim : hint_range(0.0, 4.0) = 0.12;

group_uniforms paint;

// Clearcoat, the engine's own second specular lobe (`Q215`). ⚠️ **It ADDS a
// reflection over the paint, and that is why it costs no chroma.** `P3-11c`'s
// coat mixed the painted sky INTO the albedo: the reflection replaced red and was
// then lit like diffuse paint, so it dimmed in shade and turned with the sun —
// `C*` -7.43 at the shipped dial. `CLEARCOAT` leaves the base coat's albedo alone,
// reflects the sky's radiance at a Schlick fresnel of 4% head-on, and gives the
// sun a tight highlight of its own: measured on the menu orbit's frame, red
// `C*` 52.12 -> 52.32 and `L*` 30.03 -> 27.77 in shade.
// `paint_roughness` is now the BASE coat under it, not the gloss.
// ⚠️ `Q248` mixes the painted sky back into the albedo on top of this, and pays
// that chroma again: `paint_reflect` below.
uniform float paint_roughness : hint_range(0.0, 1.0) = 0.55;
uniform float clearcoat : hint_range(0.0, 1.0) = 1.0;
uniform float clearcoat_roughness : hint_range(0.0, 1.0) = 0.12;
// The painted sky on paint and trim (`Q248`): how much of it at a glance, the
// share of that seen face-on, and the glance's own fresnel power — wider than
// the glazing's `fresnel_power`, which would leave a rim and nothing else.
uniform float paint_reflect : hint_range(0.0, 1.0) = 0.6;
uniform float paint_face_on : hint_range(0.0, 1.0) = 0.12;
uniform float paint_fresnel_power : hint_range(1.0, 8.0) = 2.5;

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
// The glint's weight on trim — chrome and silver (`Q248`). Paint has none: its
// sun highlight is `CLEARCOAT`'s.
uniform float trim_glint : hint_range(0.0, 4.0) = 1.5;

group_uniforms ink;

// The detail lines (`tools/vehicle_ink.py`): a window, a band or a lens is a
// change of colour on one flat panel, which the city's depth outline cannot
// see, so the mesh carries each such edge in `UV2` and the line is drawn here.
// The width is in METRES, so the line is bold on a near car and thins with
// distance; under a pixel it is held a pixel wide and faded by its true width,
// and `ink_max_px` stops it swelling on a car against the lens.
// Must match `INK_SPAN_M` in `tools/vehicle_ink.py`.
const float INK_SPAN_M = 16.0;
uniform float ink_width_m : hint_range(0.0, 0.1) = 0.02;
uniform float ink_max_px : hint_range(0.0, 8.0) = 4.0;
// The line is the surface's own colour scaled by this; 0 is black.
uniform float ink_darkness : hint_range(0.0, 1.0) = 0.35;
// What the player's full speed takes off it: the same share `cel_outline.tres`
// takes off the city's line, restated here because that is another material.
uniform float ink_speed_thin : hint_range(0.0, 1.0) = 0.33;
uniform float ink_speed_fade : hint_range(0.0, 1.0) = 0.2;

group_uniforms relief;

// Pressed panels (`tools/make_vehicle.py`'s `embossed`): a bus's side is one
// flat quad, and a flat quad under one sun is one shade. The relief is drawn by
// tilting `NORMAL` — no texture, no UV (both sets are spent), no triangle — off
// a pitch the generator stamps per face and the import door hands on as
// `UV.y`'s fraction: a joint at every multiple of it along the body (a
// coach-built side's panels) or up it (a pressed side's crease). The joints
// are paint only; the seated edge below is every surface's.
// Must match `RELIEF_UNIT_M` and `RELIEF_COURSES` in `tools/make_vehicle.py`,
// and `RELIEF_SPAN` in `generated_scene_import.gd`.
const float RELIEF_SPAN = 256.0;
const float RELIEF_UNIT_M = 0.025;
const float RELIEF_COURSES = 127.0;
// Half the groove's width at a joint, and its walls' slope (rise over run).
// ⚠️ Under a pixel and a half the groove is held that wide and its slope cut to
// match, as the ink is: a V's two walls cancel inside one pixel, so a far bus
// loses its joints to grey rather than to shimmer (`held_wall`).
const float RELIEF_HELD_PX = 0.75;
uniform float relief_groove_m : hint_range(0.0, 0.1) = 0.02;
uniform float relief_groove_slope : hint_range(0.0, 2.0) = 1.2;
// How far each panel between two joints bows out, as the slope at its edges:
// the part of the relief a far vehicle keeps, since it is as wide as the panel.
// Joints along the body only — one crease has no panel to bow.
uniform float relief_pillow : hint_range(0.0, 0.5) = 0.04;
// How far in from an inked edge a surface falls away into it, and how steeply:
// a window in its frame, a frame on its wall. Glass and lenses too. Held to a
// pixel and a half and cut to match, as the groove is.
uniform float relief_edge_m : hint_range(0.0, 0.1) = 0.03;
uniform float relief_edge_slope : hint_range(0.0, 2.0) = 0.6;
// The crown (`Q248`): every panel leans away from the middle of the body, so a
// flat bonnet shades and reflects as a gradient rather than as one tone. No
// texture and no vertex channel — the lean is the fragment's own place on the
// body over `crown_radius_m`, from `crown_height_m` up the body's axis.
// `crown_height_m` is `vehicle_outline.gdshader`'s `outline_height_m`: the
// one middle of the body. `crown_along` is the share of it taken along the body: at 1.0 a wing's far
// end turned to the ground and went grey. 0 is the flat sheet.
uniform float crown : hint_range(0.0, 2.0) = 1.0;
uniform float crown_radius_m : hint_range(0.5, 20.0) = 3.0;
uniform float crown_height_m : hint_range(0.0, 3.0) = 0.7;
uniform float crown_along : hint_range(0.0, 1.0) = 0.3;
// Where the fragment is on the body, and the body's axes in view space.
varying vec3 body_at;
varying flat vec3 body_x;
varying flat vec3 body_y;
varying flat vec3 body_z;

varying flat float marker;
// The relief on this face: its pitch in metres (0 for none), the body's axis it
// repeats along in view space, and where along that axis the fragment is.
varying flat float relief_pitch;
varying flat float relief_bows;
varying float relief_at;
// `flat` for the same reason `marker` is: every vertex of a lens carries the
// same circuit, and an interpolated one would land between two channels at the
// seam between a lamp and the paint it is seated in.
varying flat float circuit;
// What `INSTANCE_CUSTOM.a` says above the livery bit: 0 or 1 each.
varying flat float running;
varying flat float braking;
// The indicators this frame, left and right, the blink already applied.
varying flat vec2 winking;
// Whether a moving taxi's roof sign is lit for hire: 0 or 1.
varying flat float for_hire;

#ifdef VEHICLE_BATCHED
#include "res://assets/shaders/vehicle_fade.gdshaderinc"
#endif

// A wall's slope `off_m` from its line: `slope` inside `reach_m`, none past
// it, the reach held to `RELIEF_HELD_PX` either side and the slope cut by as
// much. Two lines at once, because an inked triangle carries two edges.
vec2 held_wall(vec2 off_m, vec2 px_m, float reach_m, float slope) {
	vec2 held_m = max(vec2(reach_m), RELIEF_HELD_PX * px_m);
	return clamp((held_m - off_m) / px_m + 0.5, 0.0, 1.0) * slope * reach_m / held_m;
}

void vertex() {
	marker = floor(UV.y);
	circuit = floor(UV.x);
	// Swapped per vertex, not per fragment: a livery face is flat and every
	// vertex of it carries the one colour, so `COLOR` interpolates to it.
	float bits = floor(INSTANCE_CUSTOM.a + 0.5);
	if (abs(marker - MARKER_LIVERY) < 0.5 && mod(bits, 2.0) > 0.5) {
		COLOR.rgb = INSTANCE_CUSTOM.rgb;
	}
	running = mod(floor(bits / 2.0), 2.0);
	braking = mod(floor(bits / 4.0), 2.0);
	// A phase off the instance's slot, so a street of hazards does not flash as
	// one. Not off its position: a moving car's would draw a new phase every
	// frame and flicker. A traffic car keeps its slot for life.
	float phase = fract(float(INSTANCE_ID) * 0.618034);
	float lit = step(fract(TIME * traffic_blink_hz + phase), traffic_blink_duty);
	winking = vec2(mod(floor(bits / 8.0), 2.0), mod(floor(bits / 16.0), 2.0)) * lit;
	for_hire = mod(floor(bits / 32.0), 2.0);
#ifdef VEHICLE_BATCHED
	faded = fade_of(bits);
#endif
	float stamp = floor(fract(UV.y) * RELIEF_SPAN + 0.5);
	bool courses = stamp > RELIEF_COURSES;
	relief_pitch = (courses ? stamp - RELIEF_COURSES : stamp) * RELIEF_UNIT_M;
	relief_bows = courses ? 0.0 : 1.0;
	relief_at = courses ? VERTEX.y : VERTEX.z;
	body_at = VERTEX;
	mat3 to_view = mat3(MODELVIEW_MATRIX);
	body_x = normalize(to_view[0]);
	body_y = normalize(to_view[1]);
	body_z = normalize(to_view[2]);
}

void fragment() {
#ifdef VEHICLE_BATCHED
	if (fade_drops(faded, FRAGCOORD.xy)) {
		discard;
	}
#endif
	vec3 albedo = vertex_srgb_to_linear(COLOR.rgb);
	vec3 ink_tone = albedo * ink_darkness;

	bool is_cabin = abs(marker - MARKER_CABIN) < 0.5;
	bool is_cabin_dim = abs(marker - MARKER_CABIN_DIM) < 0.5;
	bool is_glass = is_cabin || is_cabin_dim || abs(marker - MARKER_GLASS) < 0.5;
	bool is_lamp = abs(marker - MARKER_LAMP) < 0.5;

	// The relief, before anything reads `NORMAL`: the mirror below and the
	// engine's lighting both shade the pressed surface.
	// Every derivative is taken out here, ahead of the branches: inside one, a
	// pixel quad that straddles a glass edge has none.
	vec2 edge_m = (1.0 - UV2) * INK_SPAN_M;
	vec2 edge_dx = dFdx(edge_m);
	vec2 edge_dy = dFdy(edge_m);
	vec2 edge_px_m = abs(edge_dx) + abs(edge_dy);
	float joint_px_m = max(fwidth(relief_at), 1e-5);
	vec3 across = dFdx(VERTEX);
	vec3 down = dFdy(VERTEX);
	vec3 flat_n = normalize(NORMAL);
	vec3 tilt = vec3(0.0);
	if (relief_pitch > 0.0 && !is_glass && !is_lamp) {
		// The height's slope along the axis: up out of the groove on either
		// side of a joint, and down the bow toward the next one.
		float cell = fract(relief_at / relief_pitch);
		float wall = held_wall(
			vec2(min(cell, 1.0 - cell) * relief_pitch),
			vec2(joint_px_m),
			relief_groove_m,
			relief_groove_slope
		).x;
		float slope = (cell < 0.5 ? wall : -wall)
				+ relief_bows * relief_pillow * (1.0 - 2.0 * cell);
		// Along the face only: an end face has no run along the body, so
		// the tangent is nothing there and the face stays flat.
		vec3 relief_axis = relief_bows > 0.5 ? body_z : body_y;
		tilt += (relief_axis - flat_n * dot(flat_n, relief_axis)) * slope;
	}
	// A seated edge: every edge the ink is drawn on — a pane in its frame, a
	// frame on its wall, a lens, a band — falls away into the joint, so the
	// pane reads as set in and the frame as standing proud. The distance is
	// the ink's own (`UV2`), linear over a triangle, so its screen derivatives
	// are exact and the slope's direction is read off them. A face with no
	// inked edge carries 0 in both channels and skips the lot.
	if (relief_edge_slope > 0.0 && max(UV2.x, UV2.y) >= 1e-5) {
		vec3 r_across = cross(down, flat_n);
		vec3 r_down = cross(flat_n, across);
		float area = dot(across, r_across);
		if (abs(area) > 1e-12) {
			vec2 wall = held_wall(
				edge_m, max(edge_px_m, vec2(1e-5)), relief_edge_m, relief_edge_slope
			);
			// Selected, not multiplied: a channel with no edge may hold an inf.
			wall = mix(vec2(0.0), wall, greaterThanEqual(UV2, vec2(1e-5)));
			tilt += (r_across * dot(edge_dx, wall) + r_down * dot(edge_dy, wall)) / area;
		}
	}
	if (crown > 0.0) {
		// Soft-limited, so a bus's far end leans no further than a car's.
		vec3 off = (body_at - vec3(0.0, crown_height_m, 0.0)) / crown_radius_m;
		off.z *= crown_along;
		off /= 1.0 + abs(off);
		vec3 lean = body_x * off.x + body_y * off.y + body_z * off.z;
		tilt -= crown * (lean - flat_n * dot(flat_n, lean));
	}
	NORMAL = normalize(flat_n - tilt);

	// The painted sky. Glass and lenses always read it; paint and trim read it
	// while `paint_reflect` or `trim_glint` is up (`Q248`), and with both at 0
	// the guard spares paint — most of a car body — the `pow`, the `normalize`
	// and the `reflect`, as it did under `Q215`.
	float fresnel = 0.0;
	vec3 mirrored = vec3(0.0);
	float glint = 0.0;
	bool is_trim = abs(marker - MARKER_TRIM) < 0.5;
	bool is_mirror = is_glass || is_lamp;
	if (is_mirror || paint_reflect > 0.0 || (is_trim && trim_glint > 0.0)) {
		// One fresnel a fragment, on its surface's own power; the marker chooses
		// how much of it lands.
		fresnel = pow(
			1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0),
			is_mirror ? fresnel_power : paint_fresnel_power
		);

		// The mirror. Where the reflected ray points decides what it sees, so a
		// screen darkens toward the city as the car turns and brightens toward the
		// zenith as it pitches — which a single colour cannot do at any strength.
		vec3 bounced = mat3(INV_VIEW_MATRIX) * reflect(-VIEW, NORMAL);
		mirrored = mix(
			ground_reflection,
			mix(sky_horizon, sky_zenith, clamp(bounced.y, 0.0, 1.0)),
			smoothstep(-0.08, 0.08, bounced.y)
		) * sky_light;

		// Isolated from the sun alone, so it moves with heading where the sky
		// gradient cannot: `bounced.y` is invariant under yaw, `bounced · sun` is
		// not. On trim too (`Q248`), not on paint — `CLEARCOAT` has its own sun
		// lobe, and an albedo glint there would spend its chroma a second time.
		if (is_mirror || is_trim) {
			glint = pow(max(dot(bounced, sun_toward), 0.0), glint_sharpness);
		}
	}

	float roughness = paint_roughness;
	float coat = 0.0;
	if (is_glass) {
		roughness = glass_roughness;
		albedo += sky_horizon * sky_light * glint * glint_strength;
		albedo = mix(albedo, mirrored, glass_reflect * mix(glass_face_on, 1.0, fresnel));
		if (is_cabin || is_cabin_dim) {
			EMISSION = cabin_light * (is_cabin ? cabin_glow : cabin_glow_dim) * night_lights;
		}
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
			if (channel == CHANNEL_BRAKE) {
				level = max(level, max(braking, running * traffic_tail_lit * night_lights));
			} else if (channel == CHANNEL_HEADLAMP) {
				level = max(level, running * max(traffic_day_lamps, night_lights));
			} else if (channel == CHANNEL_SIDELAMP) {
				level = max(level, running * traffic_side_lit);
			} else if (channel == CHANNEL_INDICATOR_L) {
				level = max(level, winking.x);
			} else if (channel == CHANNEL_INDICATOR_R) {
				level = max(level, winking.y);
			} else if (channel == CHANNEL_ROOFSIGN) {
				level = max(level, for_hire * traffic_sign_lit);
			}
			// The guard is for a black lens, which is not authored today and is
			// one swatch away from being: it would divide by zero and emit NaN,
			// which the Mobile renderer resolves as a white hole in the car.
			float peak = max(albedo.r, max(albedo.g, albedo.b));
			vec3 hue = albedo / max(peak, 0.001);
			EMISSION = hue * level * lamp_emission;
		}
		albedo += sky_horizon * sky_light * glint * glint_strength * 0.5;
		albedo = mix(albedo, mirrored, lamp_reflect * fresnel);
	} else {
		// Paint and trim, under one `CLEARCOAT` (`Q215`). Trim adds the sun's
		// glint, and both take `paint_reflect` of the painted sky by their own
		// glance (`Q248`) — which costs chroma, on the user's pick.
		coat = clearcoat;
		if (is_trim) {
			albedo += sky_horizon * sky_light * glint * trim_glint;
		}
		albedo = mix(albedo, mirrored, paint_reflect * mix(paint_face_on, 1.0, fresnel));
	}

	// Metres from each inked edge, and how many metres a pixel spans there. A
	// channel with no edge is 0 and is masked rather than left to the clamp:
	// its distance over a zero derivative is a number a phone's half floats
	// cannot hold.
	vec2 px_per_m = 1.0 / max(edge_px_m, vec2(1e-6));
	float width_m = ink_width_m * (1.0 - ink_speed_thin * outline_speed);
	vec2 width_px = min(width_m * px_per_m, vec2(ink_max_px));
	vec2 drawn = clamp(max(width_px, vec2(1.0)) - edge_m * px_per_m, 0.0, 1.0)
			* min(width_px, vec2(1.0)) * step(vec2(1e-5), UV2);
	float ink = max(drawn.x, drawn.y) * (1.0 - ink_speed_fade * outline_speed);
	albedo = mix(albedo, ink_tone, ink);
	EMISSION *= 1.0 - ink;

	ALBEDO = albedo;
	// Nailed down rather than left at a default. The Mobile renderer has no SSR
	// and no reflection probes, so a metal surface has nothing to reflect and
	// renders as sky-coloured plastic — see this file's header, and
	// `ART_DESIGN.md`'s anti-goals, which refuse the metalness workflow for
	// exactly this reason and not as a matter of taste.
	METALLIC = 0.0;
	ROUGHNESS = roughness;
	CLEARCOAT = coat;
	CLEARCOAT_ROUGHNESS = clearcoat_roughness;
}
