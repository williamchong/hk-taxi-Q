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
##     ⚠️ **Against `thumb_rest_*`, NOT against `touch_steer_*`.** A tap zone is
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
## ⚠️ **Nothing here references a `class_name` global.** A `--script` tool that
## does fails to parse on a fresh clone, where the class cache has not been
## written, and the SceneTree then exits **0** having checked nothing.
## `ARCHITECTURE.md` records the trap; everything is `preload`ed by path.

const TrackerScript = preload("res://scripts/core/street_tracker.gd")
const HudLayoutScript = preload("res://scripts/ui/hud_layout.gd")
const HudStyleScript = preload("res://scripts/ui/hud_style.gd")
const StreetPlateScript = preload("res://scripts/ui/street_plate.gd")
const ChamferPanelScript = preload("res://scripts/ui/chamfer_panel.gd")

## ⚠️ **The paths come from the scripts the game loads, never restated here.** A
## check that names its own path goes green while the game reads a different
## file — the one failure a verify tool cannot be allowed to have.

## Long enough to clear `StreetTracker.DEFAULT_DWELL_S` in one sample where a
## test means to, and used as a fraction where a test means not to.
const LONG_S: float = 1.0

var _failed: int = 0


func _init() -> void:
	_check_layout()
	_check_style()
	_check_bar()
	_check_plate_tuning()
	_check_tracker()

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

	var outside: PackedStringArray = layout.within_design()
	if outside.size() > 0:
		_fail("layout", "rect(s) outside the design resolution: %s" % ", ".join(outside))

	# ⚠️ ...and the check must be capable of failing. A `collisions()` that
	# always returned empty would pass the assertion above for ever, which is
	# the exact failure `verify_mesh_contract.gd` was written about. So: put a
	# rect under a thumb on a throwaway copy and require it to be caught.
	var probe: Resource = HudLayoutScript.new()
	probe.speed = probe.thumb_rest_left
	if probe.collisions().is_empty():
		_fail("layout", "a rect placed on thumb_rest_left was NOT reported — the check is inert")
	else:
		print("  layout: mutation caught (%s)" % ", ".join(probe.collisions()))

	# ⚠️ ...and the other half, which is the one this file got wrong first time.
	# Overlapping a tap ZONE must be ALLOWED. Without this assertion, someone
	# "tightening" the check back to `touch_zones()` would pass every test above
	# and silently re-ban the corners the references use.
	var over_zone: Resource = HudLayoutScript.new()
	# The UPPER part of the tap zone, deliberately. A tap zone geometrically
	# CONTAINS its own thumb rest — the rest is the bottom outer corner of it —
	# so handing the whole zone to this probe tests nothing and fails for the
	# wrong reason. What must be permitted is a rect inside the zone and clear
	# of the fingertip, which is exactly where the speed readout now sits.
	var zone: Rect2 = over_zone.touch_steer_left
	over_zone.speed = Rect2(zone.position, Vector2(zone.size.x, zone.size.y * 0.5))
	if over_zone.collisions().is_empty():
		print("  layout: a rect over a tap zone is permitted, as it must be")
	else:
		_fail(
			"layout",
			(
				(
					"a rect over touch_steer_left was refused (%s) — the check has been "
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
	if absf(style.plate_ink.get_luminance() - plate_lum) < 0.30:
		_fail("style", "plate ink is too close in luminance to the plate field")
	if absf(style.chip_ink.get_luminance() - chip_lum) < 0.30:
		_fail("style", "chip ink is too close in luminance to the chip field")

	# 🔴 **Green gains, red loses, and a swap renders perfectly.** This is the
	# oldest convention a driver has — the traffic signal, and the car's own
	# brake lamps — and the two colours sit one `.tres` edit apart. Transposed,
	# the bar moves exactly as convincingly and tells the driver the opposite of
	# the truth. No frame catches that; a rule about which channel dominates
	# does.
	#
	# ⚠️ This replaced a check that the accent stayed clear of **taxi red**. That
	# rule was written when the bar was yellow-and-blue in order to keep the
	# car's colour out of the HUD entirely, and the convention beat it: the red
	# here is not the taxi's paint spent on decoration, it is red used for the
	# one thing red means.
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


## The bar's own arithmetic, which no frame can be trusted to show.
##
## A signed reading drawn from a centre is easy to get subtly wrong — inverted,
## or clamped on one side only — and it renders as a bar that moves plausibly.
func _check_bar() -> void:
	var panel: Control = ChamferPanelScript.new()
	panel.accent_fill = 5.0
	_expect(is_equal_approx(panel.accent_fill, 1.0), "bar", "over-range reads clamp to full")
	panel.accent_fill = -5.0
	_expect(is_equal_approx(panel.accent_fill, -1.0), "bar", "and clamp the same way losing speed")
	panel.accent_fill = 0.0
	_expect(is_zero_approx(panel.accent_fill), "bar", "zero is zero")
	panel.free()


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


# ----------------------------------------------------------------- report ----


func _expect(condition: bool, area: String, what: String) -> void:
	if condition:
		print("  %s: %s" % [area, what])
		return
	_fail(area, what)


func _fail(area: String, what: String) -> void:
	_failed += 1
	printerr("  FAIL %s: %s" % [area, what])
