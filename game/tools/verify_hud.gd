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
## promoted warning is enough — `MonitorScript.new()` raises a script error and
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
const NoEntryIconScript = preload("res://scripts/ui/no_entry_icon.gd")

## ⚠️ **The paths come from the scripts the game loads, never restated here.** A
## check that names its own path goes green while the game reads a different
## file — the one failure a verify tool cannot be allowed to have.

## Long enough to clear `StreetTracker.DEFAULT_DWELL_S` in one sample where a
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

## A speed comfortably over `WrongWayMonitor.DEFAULT_MIN_KPH`, and one well
## under it, in m/s. 10 m/s is 36 kph; 1.0 is 3.6.
const FAST: float = 10.0
const CRAWL: float = 1.0

var _failed: int = 0


func _init() -> void:
	_check_layout()
	_check_style()
	_check_bar()
	_check_plate_tuning()
	_check_tracker()
	_check_wrong_way()

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

	# 🔴 **The plate must be light and the chip dark, or the whole scheme is
	# noise.** "White is the city speaking, dark is the car speaking" is the one
	# rule that makes two readouts feel like one design, and it is a rule a
	# colour tweak can silently invert — a HUD with two dark panels reads as
	# consistent and says nothing.
	var plate_lum: float = style.plate_field.get_luminance()
	var chip_lum: float = style.chip_field.get_luminance()
	if plate_lum <= chip_lum:
		_fail(
			"style",
			(
				(
					"the plate (%.2f) is not lighter than the instrument chip (%.2f) — "
					+ "the city/car distinction has inverted"
				)
				% [plate_lum, chip_lum]
			)
		)
	else:
		print(
			(
				"  style: plate %.2f over chip %.2f — the two voices are distinct"
				% [plate_lum, chip_lum]
			)
		)

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
	var bar_legible: bool = _contrast(style.plate_field, style.warn_disc) >= MIN_CONTRAST
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


# --------------------------------------------------------------- tracker ----


func _check_tracker() -> void:
	# A first named street is adopted at once. There is nothing on the plate to
	# protect, so making the player wait 0.6 s to be told where they started
	# would be the dwell working against its own purpose.
	var first := TrackerScript.new()
	first.sample(1, "HENNESSY ROAD", "軒尼詩道", LONG_S)
	_expect(first.street_en == "HENNESSY ROAD", "tracker", "first named street is adopted")
	_expect(first.street_zh == "軒尼詩道", "tracker", "the Chinese name comes with it")
	# ⚠️ The first adoption is NOT a change. Counting it puts an off-by-one in
	# the one number that grades this HUD.
	_expect(first.changes == 0, "tracker", "the first street is not counted as a change")

	# The dwell, from the side that must NOT move. This is the junction case:
	# the graph offers a different road for a moment and the plate must ignore
	# it.
	var brief := TrackerScript.new()
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
	var flapping := TrackerScript.new()
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
	var unnamed := TrackerScript.new()
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
	var through_cap := TrackerScript.new()
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
	var same_name := TrackerScript.new()
	same_name.sample(1, "HENNESSY ROAD", "軒尼詩道", LONG_S)
	same_name.sample(2, "HENNESSY ROAD", "軒尼詩道", 0.1)
	_expect(same_name.changes == 0, "tracker", "a second edge of the same street is not a change")
	_expect(same_name.edge_id == 2, "tracker", "but the tracker follows onto it")

	# Nothing named yet: the plate must stay hidden rather than draw an empty
	# sign, which is every frame on a clone with no generated city.
	var empty := TrackerScript.new()
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

	# Driving the legal way down a one-way street, for four seconds. Nothing.
	var with_flow := MonitorScript.new()
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
	var backing := MonitorScript.new()
	_drive(backing, legal, 0.0, 180.0, FAST, 20)
	_expect(
		backing.raises == 0,
		"way",
		"reversing while pointed the legal way raises nothing, however fast or long"
	)

	# ...and the same street driven at it nose-first does, which is what makes
	# both assertions above mean something. From both sides of the dwell, so this
	# one stays expanded rather than folded into `_drive`.
	var against := MonitorScript.new()
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
	var correcting := MonitorScript.new()
	_drive(correcting, legal, 180.0, 0.0, FAST, 20)
	_expect(correcting.raises == 0, "way", "backing out of a mistake is not signed while it works")

	# 🔴 **But sliding sideways is not correcting either, and nothing checked it.**
	# The withholding bar was the same 120 as the nose bar, so a car pointed fully
	# backwards while drifting square across the law read as "already carrying
	# itself back the legal way" and the sign was withheld from the exact moment
	# it exists for. Found by mutation — dropping the nose bar to 90 left every
	# other assertion here green, because the withholding bar absorbed it.
	var drifting := MonitorScript.new()
	_drive(drifting, legal, 180.0, 90.0, FAST, 10)
	_expect(drifting.wrong_way, "way", "a car pointed backwards and sliding sideways is signed")

	# ...but being stationary is not being right. A car stopped dead facing the
	# wrong way is exactly who the sign is for.
	var stalled := MonitorScript.new()
	_drive(stalled, legal, 180.0, 0.0, CRAWL, 20)
	_expect(stalled.wrong_way, "way", "a car stopped facing the wrong way is signed, not excused")

	# 🔴 The junction case, and the reason the bar is 120 degrees rather than 90.
	# A car crossing or turning across a one-way street passes through
	# perpendicular, and at 90 everything past it counts as against the flow — so
	# a legal right turn over a one-way carriageway would ring the alarm halfway
	# round the corner.
	var crossing := MonitorScript.new()
	_drive(crossing, legal, 90.0, 90.0, FAST, 10)
	_expect(
		crossing.raises == 0, "way", "crossing a one-way street square on is not driving down it"
	)

	var oblique := MonitorScript.new()
	_drive(oblique, legal, 100.0, 100.0, FAST, 10)
	_expect(oblique.raises == 0, "way", "nor is a turn that carries 100 degrees across the flow")

	# ⚠️ ...and the bar is what refused those, rather than the samples being
	# harmless. Without this, an angle test that had been broken to `false` would
	# pass both assertions above.
	var tight := MonitorScript.new(90.0)
	_drive(tight, legal, 100.0, 100.0, FAST, 10)
	_expect(tight.raises == 1, "way", "and at a 90 degree bar that same drive DOES raise")

	# Evidence has to be consecutive. Two glimpses of the wrong way with a legal
	# sample between them must not bank into a raise — `street_tracker.gd`'s
	# interleaved-candidate case, at a louder readout.
	var flapping := MonitorScript.new()
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
func _raised(legal: Vector3) -> MonitorScript:
	var monitor := MonitorScript.new()
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
