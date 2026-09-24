extends SceneTree

## The HUD's two contracts: the touch reservation, and the street stabiliser (`P3-24`).
##
## ⚠️ **Runs without a built region**, like `verify_beam_budget.gd` and
## `verify_mesh_contract.gd`: the layout is committed tuning and the tracker is
## fed synthetic samples, so CI checks both on every push. That matters more
## here than usual — the thing being protected is a *future* task's screen
## space, and `P2-4` is exactly the kind of work that lands on a branch where no
## city has been built.
##
## **What this is for, in one line each:**
##
##   * `hud_layout.tres` says where `P2-4`'s thumbs go, and nothing this HUD
##     draws may sit under one. Without the check, "we left room for touch" is
##     a claim tested for the first time on a handset, by hand, after both
##     halves are already written.
##     ⚠️ **Against `thumb_rest_*`, NOT against `touch_zone_*`.** A tap zone is
##     half the screen and a thumb is a fingertip; the HUD is `MOUSE_FILTER_
##     IGNORE` throughout, so it intercepts nothing it overlaps and occlusion is
##     the only real constraint. Checking the zones instead was this file's
##     first version and it would have permanently banned the HUD from the two
##     corners every shipped game in the genre uses.
##   * `street_tracker.gd` exists because the naive one-liner strobes at junctions,
##     blanks on the region's 74 unnamed edges, and is silently wrong the rest
##     of the time. Each of those is asserted here as a **behaviour**, not as a
##     coverage tick.
##
## ⚠️ **The assertions are written so they can fail.** `Q72`'s lesson is that a
## counter which reads 0 because 0 is unreachable certifies whichever state the
## code produces, including the wrong one — so the dwell is tested from **both**
## sides (a change that should not happen yet, and the same change once it has
## earned it), and the layout check is exercised against a deliberately
## colliding rect as well as against the shipped one.
##
## 🔴 **This tool CAN print `verify_hud: ok` having checked nothing, and no guard
## inside it can prevent that.** If a `preload`ed script fails to compile — one
## promoted warning is enough — `MonitorScript.new(_shipped)` raises a script error and
## GDScript **aborts the calling function on the spot**. Every assertion after it
## is skipped, `_failed` stays 0, and `_init` runs on to print `ok` and `quit(0)`.
## Demonstrated during `P3-25`: mutating `_correcting` to `return false` left its
## two parameters unused, which is promoted, which produced a green run over an
## empty suite. A guard is not available — `new() == null` aborts at the guard
## itself, and `can_instantiate()` cannot be called on the class.
##
## What catches it is `tools/check.sh`, which greps stderr for `SCRIPT ERROR` and
## supplies the exit code Godot will not. **This is the concrete reason CLAUDE.md
## says never to run a verify tool by hand and read its output.**
##
## ⚠️ **Nothing here references a `class_name` global.** A `--script` tool that
## does fails to parse on a fresh clone, where the class cache has not been
## written, and the SceneTree then exits **0** having checked nothing.
## `ARCHITECTURE.md` records the trap; everything is `preload`ed by path.

const TrackerScript = preload("res://scripts/core/street_tracker.gd")
const HudLayoutScript = preload("res://scripts/ui/hud_layout.gd")
const HudStyleScript = preload("res://scripts/ui/hud_style.gd")
const StreetPlateScript = preload("res://scripts/ui/street_plate.gd")
const AccentBarScript = preload("res://scripts/ui/accent_bar.gd")
const MonitorScript = preload("res://scripts/core/wrong_way_monitor.gd")
const WrongWayProfileScript = preload("res://scripts/core/wrong_way_profile.gd")
const TrackerProfileScript = preload("res://scripts/core/street_tracker_profile.gd")
const NoEntryIconScript = preload("res://scripts/ui/no_entry_icon.gd")
const SevenSegmentScript = preload("res://scripts/ui/seven_segment.gd")
const SpeedDialScript = preload("res://scripts/ui/speed_dial.gd")
const MinimapProfileScript = preload("res://scripts/ui/minimap_profile.gd")
const MinimapProjectionScript = preload("res://scripts/ui/minimap_projection.gd")
const MinimapMeshScript = preload("res://scripts/ui/minimap_mesh.gd")
const MinimapScript = preload("res://scripts/ui/minimap.gd")
const FareFaceScript = preload("res://scripts/ui/fare_face.gd")
const FareScript = preload("res://scripts/fares/fare.gd")
const FareSystemScript = preload("res://scripts/fares/fare_system.gd")
const FareTariffScript = preload("res://scripts/fares/fare_tariff.gd")
const FareMeterScript = preload("res://scripts/core/fare_meter.gd")
const FareGuideScript = preload("res://scripts/fares/fare_guide.gd")
const FareGuideProfileScript = preload("res://scripts/fares/fare_guide_profile.gd")

## ⚠️ **The paths come from the scripts the game loads, never restated here.** A
## check that names its own path goes green while the game reads a different
## file — the one failure a verify tool cannot be allowed to have.

## Long enough to clear the shipped `street_tracker.tres` dwell in one sample where a
## test means to, and used as a fraction where a test means not to.
const LONG_S: float = 1.0

## `TS115`'s bar, as fractions of the disc's diameter — **the world sign's own
## numbers**, measured off TD's cell by `tools/sign_face_survey.py` and living in
## `hong_kong.yaml` (`0.87`) and `signs.py::_NO_ENTRY_BAR_THICKNESS` (`0.187`).
##
## 🔴 **Restated here on purpose, and this is the one place in this file that
## does it.** The rule above is that a check never names its own path, because a
## check that does goes green while the game reads another file. This is the
## opposite situation: those two files are build-time Python and YAML that
## `res://` cannot reach at all, so the HUD's copy in `hud_style.tres` has
## nothing to be graded against unless a third copy states what the first said.
## The check is a **ratchet between two things that must agree**, not a source of
## truth — `clearance_reconcile.py`'s shape. `Q67` is why it is worth having: the
## same two numbers were authored by eye at 0.66 by 0.22 for a year, on the
## region's most-seen sign, and no frame showed it.
const SIGN_BAR_LENGTH: float = 0.87
const SIGN_BAR_THICKNESS: float = 0.187

## Flashes per second the warning may not exceed. Three per second is the
## photosensitive-seizure threshold in WCAG 2.3.1 and is a ceiling rather than a
## preference, so it is asserted rather than left in a comment.
const MAX_BLINK_HZ: float = 3.0

## Least luminance separation an ink may have from the field it sits on. Three
## pairs are graded against it — plate, chip and the NO ENTRY bar on its disc —
## and it was written out three times before it had a name.
const MIN_CONTRAST: float = 0.30

## Least luminance separation between a main road and a minor one on the map:
## half the ink bar, because both sit on the same dark field and the eye reads
## the two strokes side by side rather than one against the field.
const MAIN_ROAD_CONTRAST: float = 0.15

## A speed comfortably over the shipped `wrong_way.tres` `min_kph`, and one well
## under it, in m/s. 10 m/s is 36 kph; 1.0 is 3.6.
const FAST: float = 10.0
const CRAWL: float = 1.0

var _failed: int = 0

## The shipped tables, read once: every tracker and monitor below is built from
## them, so the assertions grade the numbers that ship and not a copy (`P5-26`).
var _shipped: WrongWayProfile = null
var _tracking: StreetTrackerProfile = null


func _init() -> void:
	_shipped = load(WrongWayProfileScript.PATH) as WrongWayProfile
	_tracking = load(TrackerProfileScript.PATH) as StreetTrackerProfile
	if _shipped == null or _tracking == null:
		_fail("tuning", "wrong_way.tres or street_tracker.tres did not load as its profile")
		quit(1)
		return
	_check_layout()
	_check_style()
	_check_bar()
	_check_digits()
	_check_dial()
	_check_plate_tuning()
	_check_tracker()
	_check_wrong_way()
	_check_minimap()
	_check_fare_face()
	_check_guide()

	if _failed > 0:
		push_error("verify_hud: %d check(s) failed" % _failed)
		quit(1)
		return
	print("verify_hud: ok")
	quit(0)


# ---------------------------------------------------------------- layout ----


func _check_layout() -> void:
	var layout: Resource = load(HudLayoutScript.PATH)
	if layout == null:
		_fail("layout", "%s did not load" % HudLayoutScript.PATH)
		return

	# The shipped layout must be clean. This is the assertion that fails the day
	# someone nudges the speed readout into the drift button.
	var collisions: PackedStringArray = layout.collisions()
	if collisions.size() > 0:
		_fail("layout", "HUD sits under a thumb: %s" % ", ".join(collisions))
	else:
		print(
			(
				"  layout: %d HUD rects clear of %d thumb rests"
				% [layout.hud_slots().size(), layout.thumb_slots().size()]
			)
		)

	# 🔴 **A missing `.tres` key is now a zero, not a sensible default.** Dropping
	# the `@export` defaults removed the second copy of the tuning table that had
	# already drifted once — and it moved the failure mode from "stale value" to
	# "no value", which draws a zero-size panel and looks like a HUD element that
	# failed to appear. Nothing else in the suite would catch that.
	for slot_name: String in layout.hud_slots():
		var rect: Rect2 = layout.hud_slots()[slot_name]
		if rect.size.x <= 0.0 or rect.size.y <= 0.0:
			_fail("layout", "%s has no size — is it missing from the .tres?" % slot_name)

	# The map and the plate are one panel (`Q136`): same width, one on the other.
	# Nudging either alone opens a gap or a step in a shared keyline, which no
	# other check here would see.
	# `P3-5a` filled three slots. A filled slot leaves the reserved set — it is
	# no longer outlined as empty — and MUST stay in the graded set, or the
	# meter could drift onto a thumb with the check still green.
	var reserved: Dictionary[String, Rect2] = layout.reserved_slots()
	_expect(
		(
			not reserved.has("MeterSlot")
			and not reserved.has("TimerSlot")
			and not reserved.has("CalloutSlot")
			and reserved.has("AwardSlot")
			and reserved.has("ComboSlot")
		),
		"layout",
		"the meter, the timer and the callout are filled; the award and the combo stay reserved"
	)
	_expect(
		(
			layout.hud_slots().has("meter")
			and layout.hud_slots().has("timer")
			and layout.hud_slots().has("callout")
		),
		"layout",
		"and the three filled slots are still graded against the thumbs"
	)
	_expect(layout.abutting(), "layout", "the minimap sits on the street plate at its width")
	var apart: Resource = layout.duplicate()
	apart.minimap = Rect2(apart.minimap.position - Vector2(0.0, 8.0), apart.minimap.size)
	_expect(not apart.abutting(), "layout", "and a minimap lifted 8 px off it is refused")

	var outside: PackedStringArray = layout.within_design()
	if outside.size() > 0:
		_fail("layout", "rect(s) outside the design resolution: %s" % ", ".join(outside))

	# ⚠️ ...and the check must be capable of failing. A `collisions()` that
	# always returned empty would pass the assertion above for ever, which is
	# the exact failure `verify_mesh_contract.gd` was written about. So: put a
	# rect under a thumb on a throwaway copy and require it to be caught.
	#
	# ⚠️ **A duplicate of the SHIPPED resource, not `new()`.** Neither `HudLayout`
	# nor `HudStyle` declares `@export` defaults any more — the numbers live only
	# in the `.tres`, as `HandlingProfile` does — so `new()` would hand these
	# probes an all-zero table and grade nothing.
	var probe: Resource = layout.duplicate()
	probe.speed = probe.thumb_rest_left
	if probe.collisions().is_empty():
		_fail("layout", "a rect placed on thumb_rest_left was NOT reported — the check is inert")
	else:
		print("  layout: mutation caught (%s)" % ", ".join(probe.collisions()))

	# ⚠️ ...and the other half, which is the one this file got wrong first time.
	# Overlapping a tap ZONE must be ALLOWED. Without this assertion, someone
	# "tightening" the check back to `zone_slots()` would pass every test above
	# and silently re-ban the corners the references use.
	var over_zone: Resource = layout.duplicate()
	# The UPPER part of the tap zone, deliberately. A tap zone geometrically
	# CONTAINS its own thumb rest — the rest is the bottom outer corner of it —
	# so handing the whole zone to this probe tests nothing and fails for the
	# wrong reason. What must be permitted is a rect inside the zone and clear
	# of the fingertip, which is exactly where the speed readout now sits.
	var zone: Rect2 = over_zone.touch_zone_left
	over_zone.speed = Rect2(zone.position, Vector2(zone.size.x, zone.size.y * 0.5))
	if over_zone.collisions().is_empty():
		print("  layout: a rect over a tap zone is permitted, as it must be")
	else:
		_fail(
			"layout",
			(
				(
					"a rect over touch_zone_left was refused (%s) — the check has been "
					+ "tightened onto tap zones, which bans the corners every reference uses"
				)
				% ", ".join(over_zone.collisions())
			)
		)


# ------------------------------------------------------------------ style ----


## The palette exists and keeps the one discipline it is written around.
func _check_style() -> void:
	var style: Resource = load(HudStyleScript.PATH)
	if style == null:
		_fail("style", "%s did not load" % HudStyleScript.PATH)
		return

	# 🔴 **One housing (`Q139`).** Every panel is the meter's black box, so the
	# three fields are one value held in three keys — and a tweak to one of them
	# is how the HUD goes back to being two designs, which is what the user saw
	# in the white map beside the dark speed and asked to have fixed.
	var housing: Color = style.plate_field
	if not (housing.is_equal_approx(style.chip_field) and housing.is_equal_approx(style.map_field)):
		_fail("style", "plate_field, chip_field and map_field are not one housing colour")
	elif housing.get_luminance() > 0.2 or housing.a < 1.0:
		_fail("style", "the housing is not dark and opaque (%.2f)" % housing.get_luminance())
	else:
		print("  style: one housing, dark and opaque, under every panel")

	# 🔴 **The speed is the DASHBOARD's and red is the FARE's** (the user's
	# calls): speed was never on a 咪錶, so it is a dial with an amber needle, and
	# the meter's red LED is the fare's (`P3-5a`). An amber that drifts to red spends
	# the one colour the fare has to itself — and the bar's red already means
	# "losing speed", two pixels below the needle.
	var needle: Color = style.dial_needle
	_expect(
		needle.g > needle.r * 0.4 and needle.g < needle.r * 0.85 and needle.b < needle.g,
		"style",
		"the dial's needle is amber, not the fare's red"
	)
	_expect(
		(
			_contrast(needle, housing) >= MIN_CONTRAST
			and _contrast(style.chip_muted, housing) >= MIN_CONTRAST
		),
		"style",
		"and the needle and the ticks both read on the housing"
	)
	# A scale the car can run off the end of pins the needle at the moment it is
	# most worth reading. 140 is `handling.tres`'s `max_speed_kph`, restated
	# because a tuning table is not this check's to load.
	_expect(
		style.dial_full_scale_kph >= 140.0,
		"style",
		"the dial's scale reaches past the car's top speed (%.0f)" % style.dial_full_scale_kph
	)
	_expect(
		(
			style.dial_minor_kph > 0.0
			and is_zero_approx(fmod(style.dial_major_kph, style.dial_minor_kph))
		),
		"style",
		"and every major tick is also a minor one"
	)
	if style.dial_tick_px <= 0.0 or style.speed_size <= 0:
		_fail("style", "the dial has no tick weight, or the numerals no size")

	# 🔴 **The 咪錶's LED (`P3-5a`)**: red, lit off its ghost, and the ghost a
	# face rather than a second reading — a ghost as bright as the housing's
	# ink would read "888.8" behind every fare.
	var lit: Color = style.meter_lit
	_expect(
		lit.r > lit.g * 2.0 and lit.r > lit.b * 2.0,
		"style",
		"the meter's digits are the fare's red"
	)
	_expect(
		_contrast(lit, style.meter_unlit) >= MIN_CONTRAST,
		"style",
		"and a lit segment separates from its ghost"
	)
	_expect(
		_contrast(style.meter_unlit, housing) < MIN_CONTRAST,
		"style",
		"and the ghost stays a face, not a reading"
	)
	if (
		style.meter_digit_px <= 0.0
		or style.meter_segment_px <= 0.0
		or style.meter_cells <= 0
		or style.meter_label_size <= 0
	):
		_fail("style", "the meter has no digit height, segment weight, cell count or label size")
	if (
		style.timer_size <= 0
		or style.timer_unit_size <= 0
		or style.timer_unit_gap < 0
		or style.timer_warn_s <= 0.0
	):
		_fail("style", "the timer has no size, or no bar under which it is urgent")
	if style.callout_size_en <= 0 or style.callout_size_zh <= 0 or style.callout_hold_s <= 0.0:
		_fail("style", "the callout has no sizes, or no hold after a fare ends")
	_expect(
		(
			style.callout_caption_size_zh > style.callout_caption_size
			and style.callout_sub_size_zh > style.callout_sub_size
			and style.callout_size_zh > style.callout_size_en
		),
		"style",
		"the Chinese callout sizes are larger than the Latin ones — the Kai thins out"
	)
	# The pips: both legible on the map, the destination the fare's red and
	# the pool's amber a different hue — one colour would make every stand a
	# destination.
	_expect(
		(
			_contrast(style.map_pickup, style.map_field) >= MIN_CONTRAST
			and _contrast(style.map_destination, style.map_field) >= MIN_CONTRAST
		),
		"style",
		"both pips read on the map"
	)
	_expect(
		(
			style.map_destination.r > style.map_destination.g * 2.0
			and style.map_pickup.g > style.map_pickup.r * 0.6
		),
		"style",
		"the destination's pip is red and the pool's is not"
	)
	if style.map_pending_px <= 0.0 or style.map_pin_px <= style.map_pending_px:
		_fail("style", "map_pending_px is 0, or the destination's pin is not larger")
	if style.map_beacon_px <= 0.0:
		_fail("style", "map_beacon_px is 0 — is it missing from the .tres?")
	if style.timer_outline_px <= 0:
		_fail("style", "the bare timer has no outline — it would vanish on a light road")

	# Ink must be readable on its own field. Two numbers, and either can be
	# nudged past the other by someone tuning a colour they liked.
	if _contrast(style.plate_ink, style.plate_field) < MIN_CONTRAST:
		_fail("style", "plate ink is too close in luminance to the plate field")
	if _contrast(style.chip_ink, style.chip_field) < MIN_CONTRAST:
		_fail("style", "chip ink is too close in luminance to the chip field")

	# 🔴 **Green gains, red loses, and a swap renders perfectly.** This is the
	# oldest convention a driver has — the traffic signal, and the car's own
	# brake lamps — and the two colours sit one `.tres` edit apart. Transposed,
	# the bar moves exactly as convincingly and tells the driver the opposite of
	# the truth. No frame catches that; a rule about which channel dominates
	# does.
	#
	# ⚠️ The taxi-red rule this replaced, and why the convention beat it, is in
	# `hud_style.gd`.
	if style.accent.g <= style.accent.r or style.accent.g <= style.accent.b:
		_fail("style", "the gaining half of the bar is not green — green is go")
	elif style.accent_negative.r <= style.accent_negative.g:
		_fail("style", "the losing half of the bar is not red — red is stop")
	else:
		print("  style: the bar gains green and loses red")

	if style.chamfer_px <= 0.0:
		_fail("style", "chamfer_px is 0 — the panels are plain rectangles again")

	# ⚠️ **The bar must be able to say two different things.** It reads
	# acceleration, signed, and if the two hues collapse together then gaining
	# and losing speed render identically — a bar that moves and means nothing,
	# which is what it was before it carried a reading at all.
	if style.accent.is_equal_approx(style.accent_negative):
		_fail("style", "the bar draws the same colour gaining and losing speed")
	elif style.accent_track.a <= 0.0:
		_fail("style", "the bar has no bed, so a reading of zero looks like a dead panel")
	else:
		print("  style: the bar reads two ways and has a bed to read against")

	if style.accel_full_scale_mps2 <= 0.0 or style.accel_smoothing_s <= 0.0:
		_fail("style", "the acceleration bar's scale or smoothing is zero")

	# 🔴 **The wrong-way sign must still be a NO ENTRY.** It is drawn from three
	# numbers quoted off the sign standing on the pole, and every one of them can
	# be tuned in the `.tres` by someone who thinks they are picking a HUD colour.
	# A HUD sign in the wrong red, or with a bar drawn to the wrong proportion, is
	# not a styling choice — it is a different sign, and `Q67` proved that reads
	# as perfectly correct to everyone who looks at it.
	var disc_red: bool = (
		style.warn_disc.r > style.warn_disc.g and style.warn_disc.r > style.warn_disc.b
	)
	var bar_legible: bool = _contrast(style.warn_bar, style.warn_disc) >= MIN_CONTRAST
	if not disc_red:
		_fail("style", "the wrong-way sign is not red — it is a NO ENTRY, not a decoration")
	if not bar_legible:
		_fail("style", "the NO ENTRY bar is not legible against its own disc")
	if disc_red and bar_legible:
		print("  style: the wrong-way sign is a red disc with a legible bar")

	if (
		not is_equal_approx(style.warn_bar_length, SIGN_BAR_LENGTH)
		or not is_equal_approx(style.warn_bar_thickness, SIGN_BAR_THICKNESS)
	):
		_fail(
			"style",
			(
				(
					"the HUD draws NO ENTRY at %.3f x %.3f and the sign on the pole is "
					+ "%.3f x %.3f — see hud_style.gd, and Q67 for why nobody can see this"
				)
				% [
					style.warn_bar_length,
					style.warn_bar_thickness,
					SIGN_BAR_LENGTH,
					SIGN_BAR_THICKNESS
				]
			)
		)
	else:
		print("  style: the HUD's NO ENTRY matches the one on the pole")

	# ⚠️ A sign that does not blink is a sign that has stopped being an alarm, and
	# one that blinks too fast is a hazard rather than a warning about one.
	if style.warn_blink_hz <= 0.0:
		_fail("style", "the wrong-way sign does not blink")
	elif style.warn_blink_hz > MAX_BLINK_HZ:
		_fail(
			"style",
			(
				"the sign blinks at %.1f Hz, over the %.1f Hz photosensitivity ceiling"
				% [style.warn_blink_hz, MAX_BLINK_HZ]
			)
		)
	else:
		print(
			(
				"  style: the sign blinks at %.1f Hz, under the %.1f Hz ceiling"
				% [style.warn_blink_hz, MAX_BLINK_HZ]
			)
		)


## The bar's own arithmetic, which no frame can be trusted to show.
##
## 🔴 **Against `bar_span`, not against `accent_fill`.** The first version of
## this check set `accent_fill` and read it back, which tests Godot's `clampf`
## and nothing else: a setter mutated to `signf(value)` passed every assertion.
## What can actually be wrong is the *direction* of a centre-origin bar, and a
## bar drawn the wrong way sweeps exactly as convincingly as one drawn the right
## way. `Q72`'s rule — the test of a check is whether any reachable state makes
## it fail.
func _check_bar() -> void:
	var middle: float = 50.0
	_expect(
		AccentBarScript.bar_span(0.0, 100.0, 0.0).y == middle,
		"bar",
		"a zero reading draws nothing either side of the centre"
	)
	_expect(
		AccentBarScript.bar_span(0.0, 100.0, 1.0).y == 100.0,
		"bar",
		"a full positive reading reaches the right edge of the bed"
	)
	_expect(
		AccentBarScript.bar_span(0.0, 100.0, -1.0).y == 0.0,
		"bar",
		"a full negative reading reaches the left, which is the inversion test"
	)
	_expect(
		(
			AccentBarScript.bar_span(0.0, 100.0, 5.0).y == 100.0
			and AccentBarScript.bar_span(0.0, 100.0, -5.0).y == 0.0
		),
		"bar",
		"over-range readings clamp the same way in both directions"
	)
	_expect(
		AccentBarScript.bar_span(0.0, 100.0, 0.5).y == 75.0,
		"bar",
		"and a half reading reaches half way, so the scale is linear"
	)


# ------------------------------------------------------------------- dial ----


## The needle's arithmetic (`Q139`). A needle swept the wrong way, or off a
## wrong zero, moves exactly as convincingly as a right one — `_check_bar`'s
## lesson, on a gauge the driver trusts more than the bar.
func _check_dial() -> void:
	var zero: float = SpeedDialScript.angle_deg(0.0, 160.0)
	var full: float = SpeedDialScript.angle_deg(160.0, 160.0)
	_expect(is_equal_approx(zero, SpeedDialScript.START_DEG), "dial", "zero is the scale's start")
	_expect(
		is_equal_approx(full - zero, SpeedDialScript.SWEEP_DEG) and full > zero,
		"dial",
		"full scale is one sweep CLOCKWISE of it, as a speedometer turns"
	)
	_expect(
		is_equal_approx(SpeedDialScript.angle_deg(80.0, 160.0), (zero + full) * 0.5),
		"dial",
		"half the scale is half the sweep, so the scale is linear"
	)
	_expect(
		(
			SpeedDialScript.angle_deg(400.0, 160.0) == full
			and SpeedDialScript.angle_deg(-5.0, 160.0) == zero
		),
		"dial",
		"and a reading off either end pins, it does not wrap"
	)
	# The arc must be over the TOP: its midpoint points up, which on a canvas
	# is -Y. A dial opening upwards puts the needle under the numerals.
	var mid := Vector2.from_angle(deg_to_rad((zero + full) * 0.5))
	_expect(mid.y < -0.99, "dial", "the arc's middle is straight up")
	var placed: Vector3 = SpeedDialScript.frame(Vector2(166.0, 120.0))
	_expect(
		placed.z <= 83.0 and placed.y - placed.z >= 0.0,
		"dial",
		"and the dial fits its box with its top inside it"
	)


# ----------------------------------------------------------------- digits ----


## The meter's numerals (`Q139`). A wrong segment table draws a perfectly
## convincing wrong number, which is the worst thing a speedometer can do.
func _check_digits() -> void:
	# 🔴 The whole table, restated in segment LETTERS rather than checked by
	# count: a 4 lit as `abfg` has the right number of segments and is not a 4,
	# and that mutation survived the count. Two copies that must agree, which is
	# this file's `SIGN_BAR_LENGTH` arrangement and for its reason.
	var lights: Dictionary[String, String] = {
		"0": "abcdef",
		"1": "bc",
		"2": "abdeg",
		"3": "abcdg",
		"4": "bcfg",
		"5": "acdfg",
		"6": "acdefg",
		"7": "abc",
		"8": "abcdefg",
		"9": "abcdfg",
		"r": "eg",
		"-": "g",
		" ": "",
	}
	var wrong := PackedStringArray()
	for glyph: String in lights:
		var wanted: int = 0
		for letter: String in lights[glyph]:
			wanted |= 1 << "abcdefg".find(letter)
		if SevenSegmentScript.segments_of(glyph) != wanted:
			wrong.append(glyph)
	_expect(
		wrong.is_empty(), "digits", "every numeral lights its own segments (%s)" % ", ".join(wrong)
	)
	_expect(
		(
			SevenSegmentScript.segments_of("0") & 0b1000000 == 0
			and SevenSegmentScript.segments_of("1") == 0b0000110
		),
		"digits",
		"0 leaves the middle dark and 1 is the two on the right"
	)
	_expect(
		SevenSegmentScript.segments_of("X") == 0,
		"digits",
		"a character no meter has lights nothing"
	)

	# Every segment of every cell is drawn, lit or ghost, and the value is
	# right-aligned: "48" in three cells is ghost, 4, 8.
	var mesh: ArrayMesh = SevenSegmentScript.build(
		"48", 3, 60.0, 8.0, 0.0, Color.WHITE, Color.BLACK
	)
	if mesh == null:
		_fail("digits", "a three-cell display built no mesh — every assertion below is inert")
		return
	var arrays: Array = mesh.surface_get_arrays(0)
	var points: PackedVector2Array = arrays[Mesh.ARRAY_VERTEX]
	var inks: PackedColorArray = arrays[Mesh.ARRAY_COLOR]
	var per_cell: int = 7 * 4 * 3
	_expect(points.size() == per_cell * 3, "digits", "three cells draw all 21 segments")
	var lit_by_cell: Array[int] = [0, 0, 0]
	for index: int in range(0, points.size(), 12):
		if inks[index] == Color.WHITE:
			lit_by_cell[floori(index / float(per_cell))] += 1
	_expect(
		lit_by_cell == [0, 4, 7],
		"digits",
		'"48" is a ghost, then a 4, then an 8 — right-aligned (%s)' % str(lit_by_cell)
	)
	var box: Vector2 = SevenSegmentScript.display_size(3, 60.0, 0.0)
	var inside: bool = true
	for point: Vector2 in points:
		inside = inside and Rect2(Vector2.ZERO, box).grow(0.01).has_point(point)
	_expect(inside, "digits", "and nothing is drawn outside the display's own box")
	_expect(
		SevenSegmentScript.build("1", 0, 60.0, 8.0, 0.0, Color.WHITE, Color.BLACK) == null,
		"digits",
		"no cells, no mesh"
	)

	# The decimal point (`P3-5a`): a mark on the cell before it, not a cell.
	var cells: Array[Array] = SevenSegmentScript.cells_of("29.0", 4)
	_expect(
		cells == [[" ", false], ["2", false], ["9", true], ["0", false]],
		"digits",
		'"29.0" is four cells with the 9 dotted, right-aligned (%s)' % str(cells)
	)
	_expect(
		SevenSegmentScript.cells_of(".5", 2) == [[" ", false], ["5", false]],
		"digits",
		"a dot with no cell before it marks nothing"
	)
	_expect(
		SevenSegmentScript.cells_of("1234.5", 3) == [["3", false], ["4", true], ["5", false]],
		"digits",
		"a value wider than the display keeps its right-hand cells, dot included"
	)
	var dotted: ArrayMesh = SevenSegmentScript.build(
		"29.0", 4, 60.0, 8.0, 0.0, Color.WHITE, Color.BLACK
	)
	var plain: ArrayMesh = SevenSegmentScript.build(
		"290", 4, 60.0, 8.0, 0.0, Color.WHITE, Color.BLACK
	)
	var dotted_points: PackedVector2Array = dotted.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	var dotted_inks: PackedColorArray = dotted.surface_get_arrays(0)[Mesh.ARRAY_COLOR]
	var plain_points: PackedVector2Array = plain.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	_expect(
		plain_points.size() == per_cell * 4 and dotted_points.size() == per_cell * 4 + 6,
		"digits",
		"the dot is six vertices after every cell's segments, and none without it"
	)
	var dot_ok: bool = dotted_points.size() == per_cell * 4 + 6
	if dot_ok:
		var cell_w: float = 60.0 * SevenSegmentScript.CELL_ASPECT
		var pitch: float = cell_w + 60.0 * SevenSegmentScript.CELL_GAP
		# The dotted cell is the third (index 2): its right edge and the next's left.
		var gap_from: float = 2.0 * pitch + cell_w
		var gap_to: float = 3.0 * pitch
		for index: int in range(per_cell * 4, dotted_points.size()):
			var point: Vector2 = dotted_points[index]
			dot_ok = (
				dot_ok
				and point.x >= gap_from - 0.01
				and point.x <= gap_to + 0.01
				and point.y >= 60.0 - 8.0 - 0.01
				and dotted_inks[index] == Color.WHITE
			)
	_expect(dot_ok, "digits", "and it sits lit at the foot of the gap after the 9")


# ----------------------------------------------------------- plate tuning ----


func _check_plate_tuning() -> void:
	var tuning: Dictionary = StreetPlateScript.load_tuning()
	if tuning.is_empty():
		_fail("plate", "%s is missing, empty or not an object" % StreetPlateScript.PATH)
		return

	# The font is the reason this HUD can draw Chinese at all, and a missing one
	# renders as a row of tofu — which reads as a broken game rather than as a
	# missing file, so it is worth an assertion rather than a warning.
	var font_path: String = str(tuning.get("font_zh", ""))
	if font_path.is_empty():
		_fail("plate", "no `font_zh` in %s" % StreetPlateScript.PATH)
	elif load(font_path) == null:
		_fail("plate", "`font_zh` names a font that did not load: %s" % font_path)
	else:
		print("  plate: font loads (%s)" % font_path.get_file())

	# ⚠️ A substitution must map a character to a **single** character. The table
	# is for one encoding of a glyph standing in for another, and a multi-
	# character right-hand side is a name edit wearing a font's clothes — which
	# is precisely what `Q54` forbids doing to published data.
	var substitutions: Dictionary = tuning.get("substitutions", {}) as Dictionary
	for from: Variant in substitutions:
		var to: Variant = substitutions[from]
		if not (from is String) or not (to is String):
			_fail("plate", "substitution %s -> %s is not a string pair" % [from, to])
		elif (from as String).length() != 1 or (to as String).length() != 1:
			_fail("plate", "substitution '%s' -> '%s' is not single-character" % [from, to])
	print("  plate: %d substitution(s), all single-character" % substitutions.size())

	# ⚠️ **And the substitution must actually happen.** The table can be perfect
	# and the call site wrong, which renders as the tofu box the table exists to
	# prevent — so this exercises the function the plate calls rather than
	# inspecting the data it reads.
	for from: Variant in substitutions:
		var source: String = "%s%s%s" % ["道", from, "街"]
		var drawn: String = StreetPlateScript.substitute(source, substitutions)
		if drawn.contains(from as String):
			_fail("plate", "substitute() left '%s' in place" % from)
		elif not drawn.contains(str(substitutions[from])):
			_fail("plate", "substitute() did not put '%s' in" % substitutions[from])
	# ...and that it is not rewriting text it was not asked to.
	if StreetPlateScript.substitute("軒尼詩道", substitutions) != "軒尼詩道":
		_fail("plate", "substitute() altered a name with nothing to substitute")
	else:
		print("  plate: substitute() swaps only what the table names")

	# The minimap's strip cuts the LETTERING, not the box (`Q136`). The longest
	# name in the four regions must come out inside the room, and a short one
	# must not be touched — a fit that always shrank would pass the first alone.
	var room: float = 300.0
	var long_name := Label.new()
	long_name.text = "CENTRAL-WAN CHAI BYPASS TUNNEL"
	var fitted: int = StreetPlateScript.fitted_size(long_name, 26, room)
	var fitted_px: float = (
		long_name
		. get_theme_font(&"font")
		. get_string_size(long_name.text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, fitted)
		. x
	)
	_expect(
		fitted < 26 and fitted >= 12 and fitted_px <= room,
		"plate",
		(
			"a 30-character name is set smaller to fit the strip (%d px, %.0f wide)"
			% [fitted, fitted_px]
		)
	)
	long_name.text = "SHARP STREET"
	_expect(
		StreetPlateScript.fitted_size(long_name, 26, room) == 26,
		"plate",
		"and a short one keeps the style's size"
	)
	long_name.free()


# --------------------------------------------------------------- tracker ----


func _check_tracker() -> void:
	# A first named street is adopted at once. There is nothing on the plate to
	# protect, so making the player wait 0.6 s to be told where they started
	# would be the dwell working against its own purpose.
	var first := TrackerScript.new(_tracking)
	first.sample(1, "HENNESSY ROAD", "軒尼詩道", LONG_S)
	_expect(first.street_en == "HENNESSY ROAD", "tracker", "first named street is adopted")
	_expect(first.street_zh == "軒尼詩道", "tracker", "the Chinese name comes with it")
	# ⚠️ The first adoption is NOT a change. Counting it puts an off-by-one in
	# the one number that grades this HUD.
	_expect(first.changes == 0, "tracker", "the first street is not counted as a change")

	# The dwell, from the side that must NOT move. This is the junction case:
	# the graph offers a different road for a moment and the plate must ignore
	# it.
	var brief := TrackerScript.new(_tracking)
	brief.sample(1, "HENNESSY ROAD", "軒尼詩道", LONG_S)
	brief.sample(2, "FLEMING ROAD", "菲林明道", 0.2)
	_expect(
		brief.street_en == "HENNESSY ROAD",
		"tracker",
		"a street seen for less than the dwell does not take the plate"
	)

	# ...and from the side that must. Without this, a tracker that simply never
	# changed would pass every assertion above — `Q72` again.
	brief.sample(2, "FLEMING ROAD", "菲林明道", LONG_S)
	_expect(
		brief.street_en == "FLEMING ROAD",
		"tracker",
		"a street that serves the dwell does take the plate"
	)
	_expect(brief.changes == 1, "tracker", "and that one counts as exactly one change")

	# A candidate that loses its nearest-ness before the dwell elapses must
	# expire rather than bank its progress. Two 0.4 s glimpses of a road, with a
	# glimpse of a third in between, must not add up to a 0.6 s dwell.
	var flapping := TrackerScript.new(_tracking)
	flapping.sample(1, "HENNESSY ROAD", "軒尼詩道", LONG_S)
	flapping.sample(2, "FLEMING ROAD", "菲林明道", 0.4)
	flapping.sample(3, "O'BRIEN ROAD", "柯布連道", 0.4)
	flapping.sample(2, "FLEMING ROAD", "菲林明道", 0.4)
	_expect(
		flapping.street_en == "HENNESSY ROAD",
		"tracker",
		"interleaved candidates do not accumulate a dwell between them"
	)

	# The 74 unnamed edges, and the miss. Neither is evidence about which street
	# the player is on, so neither may blank the plate.
	var unnamed := TrackerScript.new(_tracking)
	unnamed.sample(1, "HENNESSY ROAD", "軒尼詩道", LONG_S)
	unnamed.sample(9, "", "", LONG_S)
	_expect(
		unnamed.street_en == "HENNESSY ROAD", "tracker", "an unnamed edge does not blank the plate"
	)
	unnamed.sample(-1, "", "", LONG_S)
	_expect(
		unnamed.street_en == "HENNESSY ROAD", "tracker", "a miss does not blank the plate either"
	)
	_expect(unnamed.changes == 0, "tracker", "and neither is counted as a change")

	# ⚠️ An unnamed sample must not RESET a pending candidate either. A junction
	# interleaves two named roads with the unnamed cap between them, so a reset
	# would mean the dwell could never be served at the one place it exists for.
	var through_cap := TrackerScript.new(_tracking)
	through_cap.sample(1, "HENNESSY ROAD", "軒尼詩道", LONG_S)
	through_cap.sample(2, "FLEMING ROAD", "菲林明道", 0.4)
	through_cap.sample(-1, "", "", 0.4)
	through_cap.sample(2, "FLEMING ROAD", "菲林明道", 0.4)
	_expect(
		through_cap.street_en == "FLEMING ROAD",
		"tracker",
		"an unnamed sample between two of a candidate does not reset its dwell"
	)

	# Hennessy Road is 40-odd edges. Crossing from one to the next is not a
	# change of street and must not start a dwell against a name that is not
	# changing — if it did, the plate would blink off and on along one road.
	var same_name := TrackerScript.new(_tracking)
	same_name.sample(1, "HENNESSY ROAD", "軒尼詩道", LONG_S)
	same_name.sample(2, "HENNESSY ROAD", "軒尼詩道", 0.1)
	_expect(same_name.changes == 0, "tracker", "a second edge of the same street is not a change")
	_expect(same_name.edge_id == 2, "tracker", "but the tracker follows onto it")

	# Nothing named yet: the plate must stay hidden rather than draw an empty
	# sign, which is every frame on a clone with no generated city.
	var empty := TrackerScript.new(_tracking)
	_expect(not empty.has_street(), "tracker", "no street before the first named sample")
	empty.sample(-1, "", "", LONG_S)
	_expect(not empty.has_street(), "tracker", "and a miss does not invent one")


# ------------------------------------------------------------- wrong way ----


## The monitor's behaviour, and the sign's proportions.
##
## 🔴 **Every assertion here is written from both sides**, because the region is
## **93.5% one-way by drivable length** — so a monitor that simply never fired
## would satisfy any one-sided suite while being the most plausible way for this
## to be broken. `Q72`'s rule: the test of a counter is not that it reads 0 but
## that some reachable configuration makes it non-zero.
func _check_wrong_way() -> void:
	var legal := Vector3.FORWARD

	# 🔴 The two bars are two numbers, and the nose bar is 120: the region is
	# 93.5% one-way by drivable length, a bar at 90 rings on every legal turn
	# across a one-way street, and reusing one number for both let a car
	# pointed backwards while drifting sideways read as already correcting
	# (`Q81`). The dwell literals below were written against 0.5 s and 0.8 s;
	# a retune moves them together or this says so.
	_expect(
		_shipped.angle_deg == 120.0 and _shipped.correcting_angle_deg == 90.0,
		"way",
		(
			"the nose bar is 120 and the withholding bar is 90 (%.0f / %.0f)"
			% [_shipped.angle_deg, _shipped.correcting_angle_deg]
		)
	)
	_expect(
		_shipped.raise_s == 0.5 and _shipped.clear_s == 0.8 and _shipped.clear_s > _shipped.raise_s,
		"way",
		"the dwells are the 0.5 s raise and 0.8 s clear the samples below are written against"
	)

	# Driving the legal way down a one-way street, for four seconds. Nothing.
	var with_flow := MonitorScript.new(_shipped)
	_drive(with_flow, legal, 0.0, 0.0, FAST, 20)
	_expect(
		with_flow.raises == 0 and not with_flow.wrong_way,
		"way",
		"driving with the flow of a one-way street raises nothing"
	)

	# 🔴 **Reversing while pointed the legal way is NOT the wrong way**, and this
	# assertion is the whole of why the monitor reads the nose. Judged on velocity
	# — which is how this was built first — backing off the start line raises a NO
	# ENTRY at 40 kph, and the sign's instruction is *turn around*, which a driver
	# already facing the right way must not be given.
	var backing := MonitorScript.new(_shipped)
	_drive(backing, legal, 0.0, 180.0, FAST, 20)
	_expect(
		backing.raises == 0,
		"way",
		"reversing while pointed the legal way raises nothing, however fast or long"
	)

	# ...and the same street driven at it nose-first does, which is what makes
	# both assertions above mean something. From both sides of the dwell, so this
	# one stays expanded rather than folded into `_drive`.
	var against := MonitorScript.new(_shipped)
	against.sample(true, legal, _at(legal, 180.0, 1.0), _at(legal, 180.0, FAST), 0.4)
	_expect(not against.wrong_way, "way", "the sign does not go up before the dwell is served")
	against.sample(true, legal, _at(legal, 180.0, 1.0), _at(legal, 180.0, FAST), 0.2)
	_expect(against.wrong_way, "way", "and it does go up once the dwell is served")
	_expect(against.raises == 1, "way", "counted as exactly one raise")
	_drive(against, legal, 180.0, 180.0, FAST, 10)
	_expect(against.raises == 1, "way", "a sign already up is not raised again on every sample")

	# ⚠️ The other half of the nose rule: a car pointed the wrong way whose wheels
	# are carrying it the RIGHT way is reversing out of its own mistake, and a
	# sign that stays up through the correction is one the player drives through.
	var correcting := MonitorScript.new(_shipped)
	_drive(correcting, legal, 180.0, 0.0, FAST, 20)
	_expect(correcting.raises == 0, "way", "backing out of a mistake is not signed while it works")

	# 🔴 **But sliding sideways is not correcting either, and nothing checked it.**
	# The withholding bar was the same 120 as the nose bar, so a car pointed fully
	# backwards while drifting square across the law read as "already carrying
	# itself back the legal way" and the sign was withheld from the exact moment
	# it exists for. Found by mutation — dropping the nose bar to 90 left every
	# other assertion here green, because the withholding bar absorbed it.
	var drifting := MonitorScript.new(_shipped)
	_drive(drifting, legal, 180.0, 90.0, FAST, 10)
	_expect(drifting.wrong_way, "way", "a car pointed backwards and sliding sideways is signed")

	# ...but being stationary is not being right. A car stopped dead facing the
	# wrong way is exactly who the sign is for.
	var stalled := MonitorScript.new(_shipped)
	_drive(stalled, legal, 180.0, 0.0, CRAWL, 20)
	_expect(stalled.wrong_way, "way", "a car stopped facing the wrong way is signed, not excused")

	# 🔴 The junction case, and the reason the bar is 120 degrees rather than 90.
	# A car crossing or turning across a one-way street passes through
	# perpendicular, and at 90 everything past it counts as against the flow — so
	# a legal right turn over a one-way carriageway would ring the alarm halfway
	# round the corner.
	var crossing := MonitorScript.new(_shipped)
	_drive(crossing, legal, 90.0, 90.0, FAST, 10)
	_expect(
		crossing.raises == 0, "way", "crossing a one-way street square on is not driving down it"
	)

	var oblique := MonitorScript.new(_shipped)
	_drive(oblique, legal, 100.0, 100.0, FAST, 10)
	_expect(oblique.raises == 0, "way", "nor is a turn that carries 100 degrees across the flow")

	# ⚠️ ...and the bar is what refused those, rather than the samples being
	# harmless. Without this, an angle test that had been broken to `false` would
	# pass both assertions above.
	var tight := MonitorScript.new(_with_nose_bar(90.0))
	_drive(tight, legal, 100.0, 100.0, FAST, 10)
	_expect(tight.raises == 1, "way", "and at a 90 degree bar that same drive DOES raise")

	# Evidence has to be consecutive. Two glimpses of the wrong way with a legal
	# sample between them must not bank into a raise — `street_tracker.gd`'s
	# interleaved-candidate case, at a louder readout.
	var flapping := MonitorScript.new(_shipped)
	flapping.sample(true, legal, _at(legal, 180.0, 1.0), _at(legal, 180.0, FAST), 0.4)
	flapping.sample(true, legal, _at(legal, 0.0, 1.0), _at(legal, 0.0, FAST), 0.2)
	flapping.sample(true, legal, _at(legal, 180.0, 1.0), _at(legal, 180.0, FAST), 0.4)
	_expect(flapping.raises == 0, "way", "interleaved evidence does not accumulate a dwell")

	# The clear, from both sides of its own dwell — which is longer than the
	# raise, so that driving the wrong way THROUGH a junction does not blink the
	# sign off in the middle of the emergency it is reporting.
	var onto_two_way: MonitorScript = _raised(legal)
	onto_two_way.sample(false, legal, _at(legal, 180.0, 1.0), _at(legal, 180.0, FAST), 0.4)
	_expect(onto_two_way.wrong_way, "way", "a two-way edge does not clear the sign at once")
	onto_two_way.sample(false, legal, _at(legal, 180.0, 1.0), _at(legal, 180.0, FAST), 0.5)
	_expect(not onto_two_way.wrong_way, "way", "it clears once the longer dwell is served")

	# 🔴 **The deliberate departure from `street_tracker.gd`.** The tracker holds
	# its last answer through a miss, because a stale street name is the honest
	# answer to "where am I". An alarm must not: latched on by the car leaving the
	# graph it is a red sign that cannot be dismissed and cannot be acted on.
	var miss: MonitorScript = _raised(legal)
	for tick: int in 10:
		miss.sample(false, legal, _at(legal, 180.0, 1.0), _at(legal, 180.0, FAST), 0.2)
	_expect(not miss.wrong_way, "way", "a miss clears the sign, unlike a miss on the street plate")

	# 🔴 **And the door the miss rule does not cover: no car at all.** On a scene
	# change the HUD stops sampling, and a monitor that merely froze left the sign
	# blinking for ever with nothing driving it.
	var gone: MonitorScript = _raised(legal)
	_expect(gone.has_angle(), "way", "a monitor that has sampled reports a real angle")
	gone.stand_down(LONG_S)
	_expect(not gone.wrong_way, "way", "and standing down with no car takes the sign back down")
	_expect(not gone.has_angle(), "way", "with no angle left to report")

	# The sign's own geometry. `Q67` found this project drawing the same bar a
	# quarter short for a year, so what is asserted is the proportion and not that
	# something was drawn.
	var box := Vector2(96.0, 96.0)
	var bar: Rect2 = NoEntryIconScript.bar_rect(box, SIGN_BAR_LENGTH, SIGN_BAR_THICKNESS)
	_expect(
		bar.get_center().is_equal_approx(box * 0.5), "way", "the bar is centred on its own disc"
	)
	_expect(
		is_equal_approx(bar.size.x, box.x * SIGN_BAR_LENGTH), "way", "and spans the published 0.87"
	)
	_expect(bar.size.x > bar.size.y * 2.0, "way", "and is a bar rather than a block")
	# ⚠️ A non-square rect must draw the same sign, not a stretched one. A squashed
	# NO ENTRY is legible and wrong, which is this file's whole subject.
	var wide: Rect2 = NoEntryIconScript.bar_rect(
		Vector2(200.0, 96.0), SIGN_BAR_LENGTH, SIGN_BAR_THICKNESS
	)
	_expect(
		wide.size.is_equal_approx(bar.size), "way", "a non-square rect draws the sign, not an oval"
	)


## A monitor whose sign is already up, for the clearing tests.
## The shipped profile with only the nose bar moved — how a bar is mutated
## without touching the dwells the samples are written against.
func _with_nose_bar(angle_deg: float) -> WrongWayProfile:
	var moved := _shipped.duplicate() as WrongWayProfile
	moved.angle_deg = angle_deg
	return moved


func _raised(legal: Vector3) -> MonitorScript:
	var monitor := MonitorScript.new(_shipped)
	monitor.sample(true, legal, _at(legal, 180.0, 1.0), _at(legal, 180.0, FAST), LONG_S)
	if not monitor.wrong_way:
		_fail("way", "the fixture could not raise the sign — every clearing test below is inert")
	return monitor


## A vector `degrees` away from `law` in plan, at `speed_ms`.
##
## Taking `law` rather than assuming it means the angle asked for is the angle
## the monitor measures, whatever law a test passes.
static func _at(law: Vector3, degrees: float, speed_ms: float) -> Vector3:
	return law.rotated(Vector3.UP, deg_to_rad(degrees)) * speed_ms


## One stretch of driving: `ticks` samples of a car pointed `nose_deg` off `law`
## and travelling `travel_deg` off it at `speed_ms`.
##
## ⚠️ **Folded because a pasted loop still passes.** Nine of these differed only
## in four numbers, and most assert `raises == 0` — so a copy that kept the
## previous case's facing would grade the wrong thing and print green.
static func _drive(
	monitor: MonitorScript,
	law: Vector3,
	nose_deg: float,
	travel_deg: float,
	speed_ms: float,
	ticks: int
) -> void:
	for tick: int in ticks:
		monitor.sample(true, law, _at(law, nose_deg, 1.0), _at(law, travel_deg, speed_ms), 0.2)


# --------------------------------------------------------------- minimap ----


## The map's arithmetic (`P3-44`), which no frame can be trusted to show.
##
## 🔴 **A mirrored map of a street grid looks right.** Game `-Z` is north, `+X`
## is east and a canvas has `+Y` down, so the one thing that can be wrong is the
## sign of the heading rotation — and a map turned the wrong way round still
## turns, convincingly. So east-is-right is asserted under BOTH orientations,
## and each heading is checked against a point that is not on its own axis.
func _check_minimap() -> void:
	var mapping: Resource = load(MinimapProfileScript.PATH)
	var style: Resource = load(HudStyleScript.PATH)
	if mapping == null or style == null:
		_fail("map", "%s did not load" % MinimapProfileScript.PATH)
		return

	# Named fields, not `get()` by string: a typo there drops a key from the check.
	var floors: Dictionary[String, float] = {
		"span_m": mapping.span_m,
		"min_stroke_px": mapping.min_stroke_px,
		"casing_px": mapping.casing_px,
		"marker_px": mapping.marker_px,
		"arrow_spacing_px": mapping.arrow_spacing_px,
	}
	for key: String in floors:
		if floors[key] <= 0.0:
			_fail("map", "%s is 0 — is it missing from the .tres?" % key)
	var anchor: Vector2 = mapping.anchor
	_expect(
		anchor.x > 0.0 and anchor.x < 1.0 and anchor.y > 0.0 and anchor.y < 1.0,
		"map",
		"the car's anchor is inside the slot (%.2f, %.2f)" % [anchor.x, anchor.y]
	)
	# The border's arrow stands on a ray FROM the car, so the car must be inside
	# the room it may stand in, or the arrow lands on the car or behind it.
	var layout: Resource = load(HudLayoutScript.PATH)
	if layout != null:
		var slot: Vector2 = layout.minimap.size
		var inset: float = style.map_beacon_px
		var room := Rect2(Vector2(inset, inset), slot - Vector2(inset, inset) * 2.0)
		_expect(
			room.grow(-mapping.marker_px * 0.5).has_point(slot * anchor),
			"map",
			"the car stands clear inside the border arrow's room (%s in %s)" % [slot * anchor, room]
		)

	# 🔴 Opaque, both. Strokes overlap at every joint, a deck's casing is the
	# field drawn over the street beneath it, and the roads are clipped by the
	# field's drawn alpha — three things a translucent colour breaks quietly.
	_expect(
		(
			style.map_field.a == 1.0
			and style.map_road.a == 1.0
			and style.map_road_main.a == 1.0
			and style.map_water.a == 1.0
			and style.map_park.a == 1.0
		),
		"map",
		"the field, the roads, the water and the parks are opaque"
	)
	# The ground is the background, never the figure: a road over the harbour or
	# through Victoria Park reads as well as one on the bare field.
	_expect(
		(
			_contrast(style.map_road, style.map_water) >= MIN_CONTRAST
			and _contrast(style.map_road, style.map_park) >= MIN_CONTRAST
		),
		"map",
		"a minor road is legible over the water and the parks"
	)
	_expect(
		_contrast(style.map_road, style.map_field) >= MIN_CONTRAST,
		"map",
		"the roads are legible on the field"
	)
	# A main road that does not stand apart from a minor one is the defect the
	# class exists to fix; lighter, so it reads as the bigger road on the dark.
	_expect(
		(
			style.map_road_main.get_luminance() > style.map_road.get_luminance()
			and _contrast(style.map_road_main, style.map_road) >= MAIN_ROAD_CONTRAST
		),
		"map",
		(
			"a main road is lighter than a minor one, by %.2f"
			% _contrast(style.map_road_main, style.map_road)
		)
	)
	_expect(
		_contrast(style.map_marker, style.map_marker_edge) >= MIN_CONTRAST,
		"map",
		"the chevron's rim separates it from a road of any luminance"
	)

	var car := Vector3(500.0, 6.0, 300.0)
	var at := Vector2(120.0, 140.0)
	var north := Vector3(0.0, 0.0, -1.0)
	var east := Vector3(1.0, 0.0, 0.0)
	var scale: float = 0.75
	for heading_up: bool in [true, false]:
		var pinned: Transform2D = MinimapProjectionScript.roads_transform(
			car, north, heading_up, scale, at
		)
		var mode: String = "heading-up" if heading_up else "north-up"
		_expect(_lands(pinned, car, at), "map", "%s: the car is on its anchor" % mode)
		_expect(
			_lands(pinned, car + east * 100.0, at + Vector2(75.0, 0.0)),
			"map",
			"%s, facing north: 100 m east is 75 px RIGHT — the map is not mirrored" % mode
		)
		_expect(
			_lands(pinned, car + north * 100.0, at + Vector2(0.0, -75.0)),
			"map",
			"%s, facing north: 100 m north is 75 px up" % mode
		)

	# Facing east, the two orientations must now DISAGREE, and in a known way.
	var turned: Transform2D = MinimapProjectionScript.roads_transform(car, east, true, scale, at)
	_expect(
		_lands(turned, car + east * 100.0, at + Vector2(0.0, -75.0)),
		"map",
		"heading-up, facing east: the road ahead is up"
	)
	_expect(
		_lands(turned, car + north * 100.0, at + Vector2(-75.0, 0.0)),
		"map",
		"heading-up, facing east: north is to the LEFT, which is the turn's sign"
	)
	var fixed: Transform2D = MinimapProjectionScript.roads_transform(car, east, false, scale, at)
	_expect(
		_lands(fixed, car + north * 100.0, at + Vector2(0.0, -75.0)),
		"map",
		"north-up, facing east: north stays up"
	)
	_expect(
		is_equal_approx(MinimapProjectionScript.marker_rotation(east, false), PI * 0.5),
		"map",
		"and the chevron turns a quarter clockwise instead"
	)
	_expect(
		MinimapProjectionScript.marker_rotation(east, true) == 0.0,
		"map",
		"heading-up, the chevron stays up and the map turns"
	)

	_check_minimap_mesh()
	_check_minimap_pips(mapping, style)
	_check_minimap_route(mapping, style)


## The fare's pips (`P3-5a`) ride the roads' transform: a destination east of
## a north-facing car lands right of the chevron, and the pool's mesh is the
## roads' child, so `follow` moves both for nothing. A pip parented to the
## field instead would sit still in the slot while the city turned under it.
func _check_minimap_pips(mapping: Resource, style: Resource) -> void:
	var marker: PackedVector2Array = MinimapScript.pin_shape(26.0)
	var above: bool = true
	for point: Vector2 in marker:
		above = above and point.y <= 0.0 and point.y >= -26.0
	_expect(
		marker[marker.size() - 1] == Vector2.ZERO and above and marker.size() >= 6,
		"map",
		"a pin stands on its tip: the tip at the origin, the head above it"
	)

	var map: Control = MinimapScript.new()
	# An empty graph: no roads, and everything else built as shipped.
	map.setup(mapping, style, RoadGraph.new(), Vector2(280.0, 236.0), 88.0)
	var pin: Polygon2D = map.get_node_or_null("Field/Pin") as Polygon2D
	if pin == null:
		_fail("map", "the pin is not the field's child — every assertion below is inert")
		map.free()
		return
	_expect(not pin.visible, "map", "the pin is hidden until there is a target")
	_expect(
		pin.get_index() < map.get_node("Field/Car").get_index(), "map", "and it draws under the car"
	)
	var car := Vector3(500.0, 6.0, 300.0)
	var north := Vector3(0.0, 0.0, -1.0)
	var east := Vector3(1.0, 0.0, 0.0)
	map.follow(car, north)
	map.set_target(car + east * 100.0, true)
	var anchor: Vector2 = Vector2(280.0, 236.0) * mapping.anchor
	var px_per_m: float = 280.0 / mapping.span_m
	_expect(
		pin.visible and pin.position.distance_to(anchor + Vector2(100.0 * px_per_m, 0.0)) < 0.01,
		"map",
		"facing north, a destination 100 m east lands right of the chevron"
	)
	_expect(pin.color == style.map_destination, "map", "in the destination's red")
	map.follow(car, east)
	_expect(
		pin.position.distance_to(anchor + Vector2(0.0, -100.0 * px_per_m)) < 0.01,
		"map",
		"and facing east it is ahead: follow re-places it, upright"
	)
	_expect(pin.rotation == 0.0, "map", "— the pin does not turn with the map")
	map.set_target(Vector3.ZERO, false)
	_expect(not pin.visible, "map", "and it hides again between targets")

	# Every pending customer a pin of its own, upright, re-placed by `follow`.
	map.follow(car, north)
	map.set_pickups(PackedVector3Array([car + north * 50.0, car + east * 50.0]))
	var first: Polygon2D = map.get_node_or_null("Field/Pending0") as Polygon2D
	var second: Polygon2D = map.get_node_or_null("Field/Pending1") as Polygon2D
	if first == null or second == null:
		_fail("map", "two pending customers are not two pins under the field")
	else:
		_expect(
			(
				first.position.distance_to(anchor + Vector2(0.0, -50.0 * px_per_m)) < 0.01
				and second.position.distance_to(anchor + Vector2(50.0 * px_per_m, 0.0)) < 0.01
			),
			"map",
			"two pending customers are two pins, each on its place"
		)
		_expect(
			first.color == style.map_pickup and first.get_index() < pin.get_index(),
			"map",
			"in the pool's amber, under the destination's pin"
		)
		map.follow(car, east)
		_expect(
			(
				first.position.distance_to(anchor + Vector2(-50.0 * px_per_m, 0.0)) < 0.01
				and first.rotation == 0.0
			),
			"map",
			"and facing east the northern one is to the left, upright: follow re-places them"
		)
		map.show_pending(false)
		_expect(
			not first.visible and not second.visible, "map", "hidden together while a fare runs"
		)
		map.show_pending(true)
		_expect(first.visible, "map", "and shown again")
	map.set_pickups(PackedVector3Array())
	_expect(
		(
			map.get_node_or_null("Field/Pending0") == null
			or map.get_node("Field/Pending0").is_queued_for_deletion()
		),
		"map",
		"an empty pool draws no pins"
	)
	map.free()


## The route (`P3-46`): cut by plan length like `Hit.t`, one stroke in its own
## colour, the roads' child so `follow` carries it, and off at `route_px` 0.
func _check_minimap_route(mapping: Resource, style: Resource) -> void:
	_expect(style.map_route.a == 1.0, "map", "the route is opaque: its strokes overlap at a bend")
	_expect(
		(
			_contrast(style.map_route, style.map_field) >= MIN_CONTRAST
			and _contrast(style.map_route, style.map_road) >= MAIN_ROAD_CONTRAST
			and _contrast(style.map_route, style.map_road_main) >= MAIN_ROAD_CONTRAST
		),
		"map",
		"and legible on the field and apart from both road colours"
	)
	_expect(mapping.route_px >= 0.0, "map", "route_px is a width or 0, never negative")

	var line := PackedVector2Array([Vector2(0.0, 0.0), Vector2(60.0, 0.0), Vector2(100.0, 0.0)])
	var middle: PackedVector2Array = MinimapMeshScript.cut(line, 0.25, 0.75)
	_expect(
		(
			middle.size() == 3
			and middle[0].is_equal_approx(Vector2(25.0, 0.0))
			and middle[1].is_equal_approx(Vector2(60.0, 0.0))
			and middle[2].is_equal_approx(Vector2(75.0, 0.0))
		),
		"map",
		"a cut is by plan length, keeping the vertex between its ends (%s)" % middle
	)
	_expect(
		MinimapMeshScript.cut(line, 0.75, 0.25).is_empty(),
		"map",
		"and a cut ending before it starts is empty"
	)
	_expect(MinimapMeshScript.cut(line, 0.0, 1.0) == line, "map", "the whole line cut is the line")

	var ink := Color.BLUE
	var north_50 := PackedVector2Array([Vector2(500.0, 300.0), Vector2(500.0, 250.0)])
	_expect(
		(
			MinimapMeshScript.route_mesh(PackedVector2Array([Vector2.ZERO]), 4.0, ink) == null
			and MinimapMeshScript.route_mesh(north_50, 0.0, ink) == null
		),
		"map",
		"one point, or no width, is no mesh"
	)
	var mesh: ArrayMesh = MinimapMeshScript.route_mesh(north_50, 4.0, ink)
	if mesh == null:
		_fail("map", "two points built no route mesh — every assertion below is inert")
		return
	var vertices: PackedVector2Array = mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	var colours: PackedColorArray = mesh.surface_get_arrays(0)[Mesh.ARRAY_COLOR]
	var within: bool = vertices.size() == 6
	for index: int in vertices.size():
		within = within and absf(vertices[index].x - 500.0) <= 2.0 + 1e-4
		within = within and colours[index].is_equal_approx(ink)
	_expect(within, "map", "a straight route is one quad, half its width each side, in its ink")

	var map: Control = MinimapScript.new()
	map.setup(mapping, style, RoadGraph.new(), Vector2(280.0, 236.0), 88.0)
	var roads: MeshInstance2D = map.get_node_or_null("Field/Roads") as MeshInstance2D
	var route: MeshInstance2D = map.get_node_or_null("Field/Roads/Route") as MeshInstance2D
	if roads == null or route == null:
		_fail("map", "the route is not the roads' child — every assertion below is inert")
		map.free()
		return
	_expect(not route.visible and route.mesh == null, "map", "no route until one is set")
	var pin: Node = map.get_node("Field/Pin")
	_expect(roads.get_index() < pin.get_index(), "map", "the route draws under the pins")
	var car := Vector3(500.0, 6.0, 300.0)
	var north := Vector3(0.0, 0.0, -1.0)
	var east := Vector3(1.0, 0.0, 0.0)
	map.follow(car, north)
	map.set_route(north_50)
	var anchor: Vector2 = Vector2(280.0, 236.0) * mapping.anchor
	var px_per_m: float = 280.0 / mapping.span_m
	var placed: Transform2D = roads.transform * route.transform
	_expect(
		(
			route.visible
			and route.mesh != null
			and placed.basis_xform(Vector2.RIGHT).length() > 0.0
			and (placed * north_50[1]).distance_to(anchor + Vector2(0.0, -50.0 * px_per_m)) < 0.01
		),
		"map",
		"facing north, a route's far end 50 m north lands 50 m up from the chevron"
	)
	var widths: PackedVector2Array = route.mesh.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	var expected_half: float = mapping.route_px / px_per_m * 0.5
	var at_width: bool = widths.size() == 6
	for vertex: Vector2 in widths:
		at_width = at_width and is_equal_approx(absf(vertex.x - 500.0), expected_half)
	_expect(at_width, "map", "drawn route_px wide at the slot's scale, in metres")
	var before: ArrayMesh = route.mesh
	map.set_route(north_50)
	_expect(route.mesh == before, "map", "the same points rebuild nothing")
	map.follow(car, east)
	placed = roads.transform * route.transform
	_expect(
		(placed * north_50[1]).distance_to(anchor + Vector2(-50.0 * px_per_m, 0.0)) < 0.01,
		"map",
		"and facing east it is to the left: the roads' transform carries it, follow untouched"
	)
	map.set_route(PackedVector2Array())
	_expect(not route.visible and route.mesh == null, "map", "an empty route hides it again")
	map.free()

	# The dial at 0: what `P3-9` runs.
	var off: Resource = mapping.duplicate()
	off.route_px = 0.0
	var bare: Control = MinimapScript.new()
	bare.setup(off, style, RoadGraph.new(), Vector2(280.0, 236.0), 88.0)
	bare.follow(car, north)
	bare.set_route(north_50)
	var none: MeshInstance2D = bare.get_node("Field/Roads/Route") as MeshInstance2D
	_expect(not none.visible and none.mesh == null, "map", "route_px 0 draws no route")
	bare.free()


## The draw order, which IS the grade separation: a mesh draws in index order.
func _check_minimap_mesh() -> void:
	# ⚠️ Black and white because a mesh keeps its colours as RGBA8: 0.1 comes
	# back as 26/255, and the assertions below are about ORDER, not quantising.
	var road := Color.BLACK
	var field := Color.WHITE
	var street: RefCounted = _stroke(Vector2(-50.0, 0.0), Vector2(50.0, 0.0), 0)
	var deck: RefCounted = _stroke(Vector2(0.0, -50.0), Vector2(0.0, 50.0), 1)
	_expect(
		MinimapMeshScript.build([], road, road, field, 2.0) == null, "map", "no strokes, no mesh"
	)

	# Deck handed in FIRST, so an order that merely preserved the input fails.
	var strokes: Array[MinimapMeshScript.Stroke] = [deck, street]
	var mesh: ArrayMesh = MinimapMeshScript.build(strokes, road, road, field, 2.0)
	if mesh == null:
		_fail("map", "two strokes built no mesh — every assertion below is inert")
		return
	var arrays: Array = mesh.surface_get_arrays(0)
	var vertices: PackedVector2Array = arrays[Mesh.ARRAY_VERTEX]
	var colours: PackedColorArray = arrays[Mesh.ARRAY_COLOR]
	var per_stroke: int = floori(vertices.size() / 3.0)
	_expect(
		vertices.size() == per_stroke * 3 and colours.size() == vertices.size(),
		"map",
		"street, casing and deck are three strokes of equal size, coloured a vertex"
	)
	_expect(
		absf(vertices[0].y) <= 4.0 and colours[0].is_equal_approx(road),
		"map",
		"the street is drawn first, whatever order it was handed in"
	)
	_expect(
		(
			colours[per_stroke].is_equal_approx(field)
			and colours[per_stroke * 2].is_equal_approx(road)
		),
		"map",
		"then the deck's casing in the field's colour, then the deck over it"
	)
	var casing_reach: float = 0.0
	var deck_reach: float = 0.0
	for index: int in range(per_stroke, per_stroke * 2):
		casing_reach = maxf(casing_reach, absf(vertices[index].x))
		deck_reach = maxf(deck_reach, absf(vertices[index + per_stroke].x))
	_expect(
		is_equal_approx(casing_reach - deck_reach, 2.0),
		"map",
		"and the casing stands 2.0 m proud of the deck (%.1f)" % (casing_reach - deck_reach)
	)

	# 🔴 One bevel a turn, so it has to be on the OUTSIDE — on the inside it is
	# under the two quads and the notch stays open, at a size no frame shows.
	# Right then down: the notch is up and to the right of the corner.
	var bend: RefCounted = _stroke(Vector2(-50.0, 0.0), Vector2(0.0, 50.0), 0)
	bend.points = PackedVector2Array([Vector2(-50.0, 0.0), Vector2.ZERO, Vector2(0.0, 50.0)])
	var bent: Array[MinimapMeshScript.Stroke] = [bend]
	var corner: PackedVector2Array = (
		MinimapMeshScript
		. build(bent, road, road, field, 2.0)
		. surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	)
	var bevels: int = 0
	var outside: bool = false
	for index: int in range(0, corner.size(), 3):
		if corner[index] == Vector2.ZERO:
			bevels += 1
			# The centroid: the third vertex is the corner itself, at the origin.
			var centre: Vector2 = (corner[index + 1] + corner[index + 2]) / 3.0
			outside = centre.x > 0.0 and centre.y < 0.0
	_expect(bevels == 1 and outside, "map", "a turn takes one bevel, on its outside")

	# Two roads meeting at a node share ONE cap, at the wider road's half — two
	# would be the 16k triangles this was cut from, and the narrower half would
	# leave the wide road's corner open.
	var lane: RefCounted = _stroke(Vector2(200.0, 0.0), Vector2(300.0, 0.0), 0)
	var avenue: RefCounted = _stroke(Vector2(200.0, 0.0), Vector2(200.0, 100.0), 0)
	avenue.width_m = 16.0
	var meeting: Array[MinimapMeshScript.Stroke] = [lane, avenue]
	var met: PackedVector2Array = (
		MinimapMeshScript
		. build(meeting, road, road, field, 2.0)
		. surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	)
	var fans: int = 0
	var reach: float = 0.0
	for index: int in range(0, met.size(), 3):
		if met[index] == Vector2(200.0, 0.0):
			fans += 1
			reach = maxf(reach, met[index].distance_to(met[index + 1]))
	_expect(
		fans == MinimapMeshScript.CAP_SIDES and is_equal_approx(reach, 8.0),
		"map",
		"two roads at one node share one cap, at the wider half (%d fans, %.1f m)" % [fans, reach]
	)

	_check_minimap_arrows(road, field)
	_check_minimap_main_roads(road, field)
	_check_minimap_ground(road, field)
	_check_minimap_beacon()

	var wobble := PackedVector2Array([Vector2.ZERO, Vector2(50.0, 0.2), Vector2(100.0, 0.0)])
	_expect(
		MinimapMeshScript.simplified(wobble, 0.5).size() == 2,
		"map",
		"a vertex 0.2 m off its road is dropped at a 0.5 m tolerance"
	)
	_expect(MinimapMeshScript.simplified(wobble, 0.1).size() == 3, "map", "and kept at a 0.1 m one")


## The target's arrow on the map's border (the user's call): down while the
## target is on the map, on the border on the line from the car toward it
## otherwise — never at a corner the line does not pass through.
func _check_minimap_beacon() -> void:
	var room := Rect2(10.0, 10.0, 200.0, 100.0)
	var car := Vector2(110.0, 80.0)
	_expect(
		not MinimapScript.beacon_point(room, car, Vector2(150.0, 30.0)).is_finite(),
		"map",
		"a target on the map takes no beacon"
	)
	var east: Vector2 = MinimapScript.beacon_point(room, car, Vector2(1000.0, 80.0))
	_expect(
		east.is_equal_approx(Vector2(210.0, 80.0)),
		"map",
		"a target due east stands the beacon on the east edge, level with the car (%s)" % east
	)
	var ahead: Vector2 = MinimapScript.beacon_point(room, car, Vector2(170.0, -220.0))
	_expect(
		(
			is_equal_approx(ahead.y, 10.0)
			and is_zero_approx((ahead - car).cross(Vector2(170.0, -220.0) - car))
		),
		"map",
		"a target ahead and right meets the top edge, on the line to it (%s)" % ahead
	)


## The ground is drawn FIRST, so every road is over it, and a region's triangles
## land where its offset puts them.
func _check_minimap_ground(road: Color, field: Color) -> void:
	var water := Color.BLUE
	var park := Color.GREEN
	var ground := MinimapMeshScript.Ground.new()
	ground.add(
		{"water": [[0.0, 0.0, 10.0, 0.0, 0.0, 10.0]], "parks": [[1.0, 1.0, 2.0, 1.0, 1.0, 2.0]]},
		Vector2(100.0, 0.0),
		water,
		park
	)
	ground.add({"water": [[0.0, 0.0, 1.0]]}, Vector2.ZERO, water, park)
	_expect(
		ground.vertices.size() == 6 and ground.vertices[1] == Vector2(110.0, 0.0),
		"map",
		"the ground moves by the region's offset, and a malformed triangle adds nothing"
	)
	var street: RefCounted = _stroke(Vector2(-50.0, 0.0), Vector2(50.0, 0.0), 0)
	var inks: PackedColorArray = (
		MinimapMeshScript
		. build([street], road, road, field, 2.0, null, ground)
		. surface_get_arrays(0)[Mesh.ARRAY_COLOR]
	)
	_expect(
		inks[0] == water and inks[3] == park and inks.find(road) == 6,
		"map",
		"the water and the parks are drawn before any road"
	)


## Main roads draw after the minor roads of their level, in their own colour:
## a junction's cap is its pass's, so a main road runs through the grid unbroken.
func _check_minimap_main_roads(road: Color, field: Color) -> void:
	var main_road := Color.RED
	var trunk: RefCounted = _stroke(Vector2(-50.0, 0.0), Vector2(50.0, 0.0), 0)
	trunk.main = true
	var side: RefCounted = _stroke(Vector2(0.0, -50.0), Vector2(0.0, 50.0), 0)
	# The main road handed in FIRST, so an order that kept the input fails.
	var inks: PackedColorArray = (
		MinimapMeshScript
		. build([trunk, side], road, main_road, field, 2.0)
		. surface_get_arrays(0)[Mesh.ARRAY_COLOR]
	)
	var first_main: int = inks.find(main_road)
	_expect(
		first_main > 0 and inks.rfind(road) < first_main and inks[inks.size() - 1] == main_road,
		"map",
		"a main road is drawn after the minor road it crosses, in its own colour"
	)


## The one-way arrows (`Q136`). 🔴 **An arrow pointing the wrong way is the one
## defect here that sends a driver into oncoming traffic**, and at 7 px no
## frame shows it — so the tip is asserted AHEAD along the vertex order, which
## is the way the ETL guarantees a `forward` edge travels.
func _check_minimap_arrows(road: Color, field: Color) -> void:
	var arrows := MinimapMeshScript.Arrows.new()
	arrows.length_m = 8.0
	arrows.spacing_m = 50.0
	var lawful: RefCounted = _stroke(Vector2(0.0, 300.0), Vector2(100.0, 300.0), 0)
	lawful.width_m = 16.0
	var plain: Array[MinimapMeshScript.Stroke] = [lawful]
	var bare: int = (
		MinimapMeshScript
		. build(plain, road, road, field, 2.0, arrows)
		. surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
		. size()
	)
	_expect(
		(
			bare
			== (
				MinimapMeshScript
				. build(plain, road, road, field, 2.0)
				. surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
				. size()
			)
		),
		"map",
		"a two-way road takes no arrows"
	)

	lawful.one_way = true
	var arrowed: Array = (
		MinimapMeshScript.build(plain, road, road, field, 2.0, arrows).surface_get_arrays(0)
	)
	var points: PackedVector2Array = arrowed[Mesh.ARRAY_VERTEX]
	var inks: PackedColorArray = arrowed[Mesh.ARRAY_COLOR]
	_expect(points.size() == bare + 6, "map", "100 m of one-way road at a 50 m spacing takes two")
	var tip: Vector2 = points[bare]
	var tail: Vector2 = (points[bare + 1] + points[bare + 2]) * 0.5
	_expect(
		is_equal_approx(tip.x - tail.x, 8.0) and is_equal_approx(tip.y, tail.y),
		"map",
		"each points ALONG the vertex order, tip ahead of tail"
	)
	_expect(
		is_equal_approx((tip.x + tail.x) * 0.5, 25.0) and is_equal_approx(points[bare + 3].x, 79.0),
		"map",
		"centred on the quarter points, not bunched at a junction"
	)
	_expect(inks[bare] == field, "map", "inside a road it fits, the arrow is the field's colour")

	lawful.width_m = 4.0
	var narrow: PackedColorArray = (
		MinimapMeshScript
		. build(plain, road, road, field, 2.0, arrows)
		. surface_get_arrays(0)[Mesh.ARRAY_COLOR]
	)
	_expect(
		narrow[narrow.size() - 1] == road,
		"map",
		"on a road narrower than its head it is the road's, standing out as barbs"
	)


func _stroke(from: Vector2, to: Vector2, level: int) -> RefCounted:
	var stroke := MinimapMeshScript.Stroke.new()
	stroke.points = PackedVector2Array([from, to])
	stroke.width_m = 8.0
	stroke.level = level
	return stroke


## True where `placed` carries `world` onto `wanted`, to a hundredth of a pixel.
static func _lands(placed: Transform2D, world: Vector3, wanted: Vector2) -> bool:
	return (placed * MinimapProjectionScript.plan(world)).distance_to(wanted) < 0.01


# -------------------------------------------------------------- fare face ----


## What the fare panels say (`P3-5a`), on synthetic fares: the pickup while
## idle, the destination once hailed, the outcome held after, the clock on
## both sides of its bar, and money as the 咪錶 shows it.
func _check_fare_face() -> void:
	var tariff: Resource = load(FareTariffScript.PATH)
	var style: Resource = load(HudStyleScript.PATH)
	if tariff == null or style == null:
		_fail("face", "%s or the style did not load" % FareTariffScript.PATH)
		return
	if style.callout_sub_size <= 0 or style.callout_caption_size <= 0:
		_fail("face", "callout_sub_size or callout_caption_size is 0 — missing from the .tres?")
	if style.tick_size <= 0 or style.tick_fade_s <= 0.0:
		_fail("face", "the tick has no size or no fade")
	var stand: RefCounted = _stop(
		"Tonnochy Road outside Sun Hung Kai Centre",
		"杜老誌道新鴻基中心外",
		Vector3(100.0, 0.0, 0.0),
		["Sun Hung Kai Centre", "新鴻基中心"],
		["TONNOCHY ROAD", "杜老誌道"]
	)
	var square: RefCounted = _stop(
		"Russell Street (within Times Square)",
		"羅素街（時代廣場內）",
		Vector3(900.0, 0.0, 400.0),
		["Times Square", "時代廣場"],
		["RUSSELL STREET", "羅素街"]
	)
	# No building near it and its edge unnamed: the publisher's description is
	# all there is, and the subtitle is the distance alone.
	var kerb: RefCounted = _stop(
		"Harbour Road (opposite to Great Eagle Centre)", "港灣道（鷹君中心對面）", Vector3.ZERO, [], []
	)
	var idle: int = FareSystemScript.State.IDLE
	var boarding: int = FareSystemScript.State.BOARDING
	var carrying: int = FareSystemScript.State.CARRYING

	var face: RefCounted = FareFaceScript.new(3, "en")
	var zh: RefCounted = FareFaceScript.new(3, "zh")
	face.on_sampled(idle, null, null, 10.0, 0.0)
	_expect(
		face.caption.is_empty() and face.callout.is_empty() and not face.has_target,
		"face",
		"idle with no customer, nothing is said and nothing is pointed at (the user's call)"
	)
	face.on_sampled(idle, null, stand, 10.0, 0.0)
	_expect(
		(
			face.caption.is_empty()
			and face.has_target
			and not face.target_is_destination
			and face.target == stand.point
		),
		"face",
		"idle with a pending customer, the arrow points at the closest one and the box stays down"
	)
	_expect(not face.target_is_destination, "face", "and every pending customer is marked")
	_expect(
		(
			face.meter_text == "0.0"
			and face.total_text == "TOTAL HK$0.0"
			and face.tip_text.is_empty()
			and not face.show_timer
		),
		"face",
		"the meter reads nothing yet, the total nothing, no tip, and the clock is down"
	)
	face.on_sampled(idle, null, null, 10.0, 245.7)
	zh.on_sampled(idle, null, null, 10.0, 245.7)
	_expect(
		face.total_text == "TOTAL HK$245.7" and zh.total_text == "合計 HK$245.7",
		"face",
		"the session's takings read under the meter, in the language"
	)

	var fare: RefCounted = FareScript.new()
	fare.pickup = stand
	fare.destination = square
	fare.meter = FareMeterScript.new(tariff)
	fare.allowance_s = 60.0
	fare.remaining_s = 42.4
	fare.remaining_road_m = 1234.0
	face.on_sampled(boarding, fare, null, 10.0, 0.0)
	_expect(
		(
			face.caption == "PICKING UP"
			and face.callout == "Times Square"
			and face.callout_sub == "RUSSELL STREET"
		),
		"face",
		"boarding: the caption says so, the destination's building, its street, no distance"
	)
	zh.on_sampled(boarding, fare, null, 10.0, 0.0)
	_expect(
		zh.caption == "上客中" and zh.callout == "時代廣場" and zh.callout_sub == "羅素街",
		"face",
		"and in Chinese the same (%s)" % zh.callout
	)
	_expect(
		face.has_target and face.target_is_destination and face.target == square.point,
		"face",
		"and the guide points at the destination, as the destination"
	)
	_expect(
		face.target_is_destination,
		"face",
		"with the pending customers unmarked while someone is aboard"
	)
	_expect(not face.show_timer, "face", "the clock waits for the passenger to board")
	face.on_sampled(carrying, fare, null, 10.0, 0.0)
	_expect(
		face.caption == "DESTINATION" and face.callout_sub == "RUSSELL STREET  1.2 km",
		"face",
		"carrying: DESTINATION, and the road distance left after the street (%s)" % face.callout_sub
	)
	fare.remaining_road_m = 320.4
	face.on_sampled(carrying, fare, null, 10.0, 0.0)
	_expect(face.callout_sub == "RUSSELL STREET  320 m", "face", "under a kilometre, in metres")
	fare.destination = kerb
	face.on_sampled(carrying, fare, null, 10.0, 0.0)
	_expect(
		(
			face.callout == "Harbour Road (opposite to Great Eagle Centre)"
			and face.callout_sub == "320 m"
		),
		"face",
		"with no building and no street name, the description leads and the distance stands alone"
	)
	fare.destination = square
	face.on_sampled(carrying, fare, null, 10.0, 0.0)
	_expect(
		face.show_timer and face.timer_text == "43" and not face.timer_urgent,
		"face",
		"carrying, 42.4 s left reads 43 — rounded up, not down — and is not urgent"
	)
	_expect(face.meter_text == "29.0", "face", "and the meter shows the flagfall, to one place")
	fare.remaining_s = 10.0
	face.on_sampled(carrying, fare, null, 10.0, 0.0)
	_expect(face.timer_urgent, "face", "at the bar, the clock is urgent")
	fare.remaining_s = 10.05
	face.on_sampled(carrying, fare, null, 10.0, 0.0)
	_expect(not face.timer_urgent, "face", "a twentieth past it, not yet")
	fare.meter.advance(2200.0, 0.0)
	face.on_sampled(carrying, fare, null, 10.0, 0.0)
	_expect(
		face.meter_text == "31.1", "face", "2,200 m reads 31.1 — the first unit past the flagfall"
	)

	# The receipt (`P3-49`): what banked, over the sum that made it — the
	# meter, the time and each skill by name with its count. 31.1 on the meter
	# from the 2,200 m above; 12.5 of time; two drifts and a speed.
	fare.banked_hkd = 122.88
	fare.time_hkd = 12.5
	fare.awards.append(FareScript.Award.new(FareScript.Skill.DRIFT, 5.0))
	fare.awards.append(FareScript.Award.new(FareScript.Skill.SPEED, 5.0))
	fare.awards.append(FareScript.Award.new(FareScript.Skill.DRIFT, 5.0))
	fare.skills_hkd = 15.0
	fare.tip_hkd = 27.5
	face.on_ended(fare, true)
	face.on_sampled(idle, fare, stand, 10.0, 122.88)
	_expect(
		(
			face.caption == "DELIVERED · TIP HK$27.5"
			and face.callout == "HK$122.9"
			and face.callout_sub == "meter 31.1 + time 12.5 + drift ×2 10.0 + speed 5.0"
		),
		"face",
		"delivered: the callout holds what was banked over the receipt (%s)" % face.callout_sub
	)
	zh.on_ended(fare, true)
	zh.on_sampled(idle, fare, stand, 10.0, 122.88)
	_expect(
		(
			zh.caption == "已送達 · 小費 HK$27.5"
			and zh.callout_sub == "咪錶 31.1 + 時間 12.5 + 甩尾 ×2 10.0 + 飆車 5.0"
		),
		"face",
		"and in Chinese (%s)" % zh.callout_sub
	)
	_expect(
		(
			face.award_text(fare.awards[0]) == "+HK$5.0 drift"
			and zh.award_text(fare.awards[1]) == "+HK$5.0 飆車"
		),
		"face",
		"a skill flashes as its money and its name"
	)
	var bare: RefCounted = FareScript.new()
	bare.pickup = stand
	bare.destination = square
	bare.meter = FareMeterScript.new(tariff)
	_expect(
		face.receipt(bare) == "meter 29.0",
		"face",
		"a fare with no tip is the meter alone (%s)" % face.receipt(bare)
	)
	_expect(
		face.meter_text == "0.0" and face.total_text == "TOTAL HK$122.9" and not face.show_timer,
		"face",
		"everything but the total resets: the meter reads 0.0, the clock is down"
	)
	_expect(
		face.has_target and not face.target_is_destination and face.target == stand.point,
		"face",
		"and the guide is back on the closest pending customer, ring down"
	)
	face.on_sampled(idle, fare, stand, 10.0, 122.88)
	face.on_sampled(idle, fare, stand, 10.0, 122.88)
	_expect(face.caption.begins_with("DELIVERED"), "face", "still held on the third sample")
	face.on_sampled(idle, fare, stand, 10.0, 122.88)
	_expect(
		face.caption.is_empty() and face.callout.is_empty(),
		"face",
		"and on the fourth the box is down"
	)

	# A bail is said as what it is, over what walked out unpaid: the meter
	# and every skill that had paid.
	fare.banked_hkd = 0.0
	fare.tip_hkd = 0.0
	fare.time_hkd = 0.0
	face.on_ended(fare, false)
	face.on_sampled(idle, fare, stand, 10.0, 122.88)
	_expect(
		(
			face.caption == "RAN OFF WITHOUT PAYING"
			and face.callout == "HK$0.0"
			and face.callout_sub == "meter 31.1 + drift ×2 10.0 + speed 5.0 lost"
		),
		"face",
		"bailed says so, over what was lost (%s)" % face.callout_sub
	)
	zh.on_ended(fare, false)
	zh.on_sampled(idle, fare, stand, 10.0, 122.88)
	_expect(
		zh.caption == "乘客走數" and zh.callout_sub == "咪錶 31.1 + 甩尾 ×2 10.0 + 飆車 5.0 冇收",
		"face",
		"and in Chinese (%s)" % zh.callout_sub
	)
	# A new hail inside the hold wins: the outcome is old news.
	face.on_sampled(boarding, fare, null, 10.0, 122.88)
	_expect(face.caption == "PICKING UP", "face", "and a new hail inside the hold wins")
	face.on_sampled(idle, fare, stand, 10.0, 122.88)
	_expect(face.caption.is_empty(), "face", "with the old notice dropped, not resumed")

	# A penalty (`P3-50`, planned) is an award with negative money: docked on
	# the receipt with a minus, flashed as a deduction.
	var docked: RefCounted = FareScript.Award.new(FareScript.Skill.CRASH, -5.0)
	bare.awards.append(docked)
	bare.time_hkd = 4.0
	_expect(
		(
			face.receipt(bare) == "meter 29.0 + time 4.0 + crash −5.0"
			and face.award_text(docked) == "−HK$5.0 crash"
			and zh.award_text(docked) == "−HK$5.0 撞車"
		),
		"face",
		"a penalty is docked on the receipt and flashed as a deduction (%s)" % face.receipt(bare)
	)
	# The tip, live, under the meter while carrying and nowhere else.
	fare.tip_hkd = 27.5
	face.on_sampled(carrying, fare, null, 10.0, 0.0)
	_expect(
		face.tip_text == "TIP HK$27.5",
		"face",
		"carrying, the tip stands under the meter (%s)" % face.tip_text
	)
	zh.on_sampled(carrying, fare, null, 10.0, 0.0)
	_expect(zh.tip_text == "小費 HK$27.5", "face", "and in Chinese")
	face.on_sampled(boarding, fare, null, 10.0, 0.0)
	_expect(face.tip_text.is_empty(), "face", "boarding, no tip yet")

	_expect(
		(
			FareFaceScript.money(102.5) == "102.5"
			and FareFaceScript.money(29.0) == "29.0"
			and FareFaceScript.seconds(0.2) == "1"
			and FareFaceScript.seconds(0.0) == "0"
			and FareFaceScript.seconds(-1.0) == "0"
			and FareFaceScript.distance(324.9) == "320 m"
			and FareFaceScript.distance(995.0) == "1.0 km"
			and FareFaceScript.flash(2.1) == "+HK$2.1"
		),
		"face",
		"money is HK$ to one place, the clock never reads below zero, distance steps by 10 m"
	)


## The world guide (`Q142`): its table, and how size and colour answer distance.
func _check_guide() -> void:
	var profile: Resource = load(FareGuideProfileScript.PATH)
	if profile == null:
		_fail("guide", "%s did not load" % FareGuideProfileScript.PATH)
		return
	var floors: Dictionary[String, float] = {
		"near_m": profile.near_m,
		"far_m": profile.far_m,
		"arrow_near_m": profile.arrow_near_m,
		"arrow_far_m": profile.arrow_far_m,
		"height_m": profile.height_m,
		"ring_radius_m": profile.ring_radius_m,
		"ring_width_m": profile.ring_width_m,
		"ring_lift_m": profile.ring_lift_m,
		"pulse_hz": profile.pulse_hz,
		"pulse_depth": profile.pulse_depth,
		"ring_alpha": profile.ring_alpha,
	}
	for key: String in floors:
		if floors[key] <= 0.0:
			_fail("guide", "%s is 0 — is it missing from the .tres?" % key)
	_expect(profile.far_m > profile.near_m, "guide", "far is further than near")
	_expect(
		profile.arrow_near_m > profile.arrow_far_m,
		"guide",
		"the arrow is LARGER near than far (the user's call)"
	)
	var far: Color = profile.far_colour
	var near: Color = profile.near_colour
	_expect(
		far.r > far.g * 2.0 and near.g > near.r * 2.0,
		"guide",
		"red far, green near (the user's call)"
	)
	_expect(profile.ring_width_m < profile.ring_radius_m, "guide", "the ring is a band, not a disc")
	_expect(
		(
			profile.pending_colour.a > 0.0
			and profile.pending_colour.g > profile.pending_colour.b * 2.0
		),
		"guide",
		"the pending customers' rings have a colour, and it is the map's amber, not a blue"
	)
	_expect(
		(
			FareGuideScript.closeness(profile, profile.far_m + 1.0) == 0.0
			and FareGuideScript.closeness(profile, profile.far_m) == 0.0
			and FareGuideScript.closeness(profile, profile.near_m) == 1.0
			and FareGuideScript.closeness(profile, 0.0) == 1.0
		),
		"guide",
		"closeness is 0 at and beyond far, 1 at and inside near"
	)
	var mid: float = (profile.near_m + profile.far_m) * 0.5
	var a: float = FareGuideScript.closeness(profile, mid)
	var b: float = FareGuideScript.closeness(profile, mid - 10.0)
	_expect(is_equal_approx(a, 0.5) and b > a, "guide", "halfway reads 0.5 and closer reads more")
	var arrow: ArrayMesh = FareGuideScript.arrow_mesh(1.0)
	var ring: ArrayMesh = FareGuideScript.ring_mesh(4.0, 0.6)
	var arrow_points: PackedVector3Array = arrow.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	var ring_points: PackedVector3Array = ring.surface_get_arrays(0)[Mesh.ARRAY_VERTEX]
	_expect(
		arrow_points.size() == 9 and arrow_points[0] == Vector3(0.0, 0.0, -0.5),
		"guide",
		"the arrow is three triangles with its nose along -Z"
	)
	var flat: bool = ring_points.size() == 48 * 6
	var banded: bool = flat
	for point: Vector3 in ring_points:
		flat = flat and point.y == 0.0
		var r: float = Vector2(point.x, point.z).length()
		banded = banded and (is_equal_approx(r, 4.0) or is_equal_approx(r, 3.4))
	_expect(flat and banded, "guide", "the ring is flat, 48 segments between radius 3.4 and 4.0")


## A synthetic stop the way `FareSystem` resolves one: the publisher's
## description, the document's `place` (empty for none) and the graph's road.
static func _stop(
	en: String, zh: String, point: Vector3, place: PackedStringArray, road: PackedStringArray
) -> RefCounted:
	var stop: RefCounted = FareScript.Stop.new()
	stop.region = "test"
	stop.id = en
	var node: Dictionary = {"name": {"en": en, "zh": zh}}
	if place.size() == 2:
		node["place"] = {"en": place[0], "zh": place[1]}
	stop.node = node
	stop.point = point
	if road.size() == 2:
		stop.road_en = road[0]
		stop.road_zh = road[1]
	return stop


# ----------------------------------------------------------------- report ----


## Luminance separation between two colours. Named because the bare expression
## appeared three times and reads as arithmetic rather than as the question it is.
static func _contrast(ink: Color, field: Color) -> float:
	return absf(ink.get_luminance() - field.get_luminance())


func _expect(condition: bool, area: String, what: String) -> void:
	if condition:
		print("  %s: %s" % [area, what])
		return
	_fail(area, what)


func _fail(area: String, what: String) -> void:
	_failed += 1
	printerr("  FAIL %s: %s" % [area, what])
