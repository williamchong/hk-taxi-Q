class_name HudLayout
extends Resource
## Where every part of the HUD goes, and where it may not go (`P3-24`).
##
## **This is a contract between two tasks that cannot see each other.** `P3-24`
## draws a HUD today; `P2-4` puts touch controls under a thumb later, on a
## handset neither task has. Without a shared table, "we left space for touch"
## is a sentence in a commit message that nobody can check, and the place it
## gets checked is a phone, by hand, after both halves are written.
##
## So the touch geometry is declared **here, now, by the task that is not
## building it**, and `tools/verify_hud.gd` asserts that nothing this HUD draws
## sits under a **thumb**. `P2-4` reads the same rects rather than choosing its
## own, and the check fails the day the two disagree.
##
## ⚠️ **A touch zone and a thumb are two different rects**, and this file learned
## that the hard way — see the block above `touch_zone_left` for the reference
## that disproved the first version of the rule.
##
## ⚠️ **Data rather than constants, and that is hard rule 4 read carefully.**
## `debug_hud.gd` argues the opposite way for dev chrome — nothing about it is
## balanced, so a resource would be a file to keep in sync for no reader. This
## has **three** readers: the HUD, the touch overlay, and the check. And unlike
## dev chrome it is balanced: `P3-5b`'s deliverable is literally "safe areas,
## one-handed layout", which is this file being tuned.
##
## ⚠️ **Rects are in the 1920x1080 design resolution**, which is what
## `project.godot` sets with `canvas_items` / `expand`. They are not pixels on a
## handset and must not be reasoned about as though they were; `hud.gd` anchors
## from them and lets the stretch do its job, then insets the whole thing by the
## display's safe area for the notch.

## The design resolution the rects below are expressed in. Kept beside them
## rather than read from `project.godot`: a check that took the rects from here
## and the resolution from there would silently pass on a project whose window
## settings had moved out from under the layout.
##
## 🔴 **Nothing here declares a default, and that is the convention rather than
## an oversight.** `HandlingProfile` and `StreamingProfile` do the same: an
## `@export` with a default is a second copy of the tuning table, and a second
## copy drifts. This file's did — it sat one arrangement behind the shipped
## `.tres` while the comments beside it described the new one, and
## `verify_hud.gd` was grading `new()` rather than what ships.
@export var design_size: Vector2

# ---- what P3-24 draws ----
#
# Placed off the Midtown Madness 2 reference, which is the closest analogue in
# the genre: the one driving game here that is about a real, named city and
# therefore the only one that has ever had to put a street map and a speed on
# screen at once.
#
# 🔴 **The arrangement follows one rule, and the rule is what a readout is
# ABOUT rather than where it fits.**
#
#   * **left is the car** — speed, and whatever `B4` adds about the drive;
#   * **right is the world** — the street you are on and the map of it, which
#     are the same question asked twice and therefore belong together;
#   * **top is the fare** — timer and meter, `P3-5a`'s;
#   * **the middle is the road**, and nothing goes in it.

## Speed, bottom-left. Raised clear of the left thumb rather than sitting in the
## very corner: MM2 is a keyboard game and could use it, and we cannot.
@export var speed: Rect2

## The bilingual street name plate, bottom-right, under the minimap slot.
##
## 🔴 **The middle of the frame is the road and nothing goes in it** — the
## vanishing point, the lane you are about to be in, and the car. And a street
## name belongs with the street map rather than with the speed: the two are one
## question, which is why they share this side.
##
## ⚠️ **This is the plate's MAXIMUM box and its anchor, not its drawn size.** A
## street sign is cut to its lettering, and a fixed-width one leaves
## `SHARP STREET` floating in a slab sized for `CROSS HARBOUR TUNNEL`.
## `hud.gd::_fit_plate` shrinks it against this rect's pinned edge and clamps to
## this width, so the reservation the check grades stays the honest worst case.
@export var street_plate: Rect2

## The wrong-way warning: a NO ENTRY sign, top-centre, blinking (`P3-25`).
##
## 🔴 **Top-centre has a claimant, and this SHARES the band rather than taking
## it.** `Q80` refused the street plate this slot and reserved it for
## `P3-5a`'s bilingual destination callout — the note further down says so, and
## it stands. What earns a place here is `Q80`'s own allocation rule read
## honestly: *prominence should track information rate against importance*. The
## street name was refused for being the screen's quietest reading in its
## loudest band; a wrong-way alarm is the opposite — near-zero duty cycle,
## maximum importance, and the one readout the player must act on **before**
## the destination they were driving to matters at all.
##
## ⚠️ **It is not a fourth category in the taxonomy.** *Left is the car, right is
## the world, top is the fare, the middle is the road* is about where a standing
## readout lives. An alarm does not stand anywhere: it is an **interrupt**, it is
## absent from every ordinary frame, and it pre-empts. Adding "and alarms" to
## "top is the fare" would be reading it as furniture.
##
## ⚠️ **This rect is 96 x 96 — 5% of frame width — precisely so that sharing is
## possible.** A worded banner would have forced `P3-5a`'s callout to hide while
## the warning was up; a small sign leaves the band under it free, which is where
## the callout goes. That is the whole of what `P3-5a` inherits from this: it
## starts below y 136, not at y 40.
@export var wrong_way: Rect2

# ---- planned, NOT held open, filled by P3-5a and P3-5b ----
#
# 🔴 **Plan the area; do not hold the space.** These rects say where the timer,
# meter and minimap will go, and the check keeps them honest — but what ships is
# placed as though they do not exist, because they do not. A gap held open for
# unbuilt UI makes every release before the last one look wrong, which is a cost
# paid many times over for a benefit that arrives once. A slot's contents
# arriving is a `.tres` edit.

## `P3-5b`. Bottom-right, where MM2 puts it — **not** top-left, which is where
## this layout had it before the references were looked at. A street map is
## glanced at mid-corner and belongs near the road, not in the far corner of
## the screen. The street plate sits below it, in the corner, because the two are
## one question.
@export var minimap: Rect2
## `P3-5a`'s fare timer. Top-left and large, which is where the arcade-taxi
## reference puts its game clock.
@export var timer: Rect2
## `P3-5a`'s fare meter, top-right, on the same reference's `$` readout.
##
## ⚠️ Named `meter` and not `target`: it was `target` while this layout still
## expected to hold a destination callout, and the references moved that into
## the world (see below). A rect whose name promises a destination is how the
## next task puts one back on the screen without meaning to.
@export var meter: Rect2

## ⚠️ **There is deliberately NO slot for the destination ARROW**, and that is a
## finding rather than an omission. Both references that have a destination put
## the arrow **in the world** — the arcade taxi floats a green arrow above the
## car, MM2 hangs a banner over the road — not in the HUD. It also sits better
## with `GAME_DESIGN.md`'s "navigate by memory, not by minimap" than a screen-
## edge chevron would. `P3-5a` should build a world-space marker.
##
## ⚠️ **The destination CALLOUT is a different thing and top-centre is its slot.**
## `GAME_DESIGN.md` announces destinations by name and bilingually, and that is
## HUD text: transient, the player's current objective, and the one readout that
## earns the most prominent band on the screen. It is left undeclared here
## because `P3-5a` owns it — and the street plate was evaluated for it and
## refused (`Q80`). ⚠️ **`P3-25` puts a 96 px NO ENTRY sign in the top of that
## band** — see `wrong_way` above for why an alarm is admitted where a standing
## readout is not, and note that it leaves the callout its space rather than
## displacing it.

# ---- where P2-4's thumbs go ----
#
# 🔴 **Two rects, not one, and the distinction is the whole point.** The first
# draft of this file had a single `touch_*` family covering the left and right
# halves below the top band, and required the HUD to be disjoint from all of it.
# That rule is wrong, and NFS No Limits is the proof: it is a touch game and it
# puts its speedometer squarely in the bottom-right where the right thumb
# steers.
#
# A touch **zone** is where a tap is detected. A **thumb** is what physically
# covers pixels, and it is about a fingertip resting in an outer bottom corner —
# not half the screen. Our Controls are all `MOUSE_FILTER_IGNORE`, so they
# intercept nothing whatever they overlap; the only real constraint is
# occlusion.
#
# So the zones are recorded for `P2-4` to read, and the **rests** are what the
# check enforces. Keeping the old rule would have permanently pushed this HUD
# away from the corners every shipped game in the genre uses.

## Where taps are detected. Informational to this HUD, which is explicitly
## ALLOWED to overlap them; `P2-4` reads them as the thumbs' homes.
##
## 🔴 **Named `touch_zone_*` and no longer `touch_steer_*`, because only one of
## them steers.** The old names date from before `Q83`, when both thumbs were
## spent on steering and three of five actions had nowhere to go — so
## `touch_steer_right` was pointing at what is now the *longitudinal* control.
## A rect whose name promises the wrong axis is how the next reader wires the
## throttle to the steering, the way `meter` was renamed from `target` further
## up this file.
##
## ⚠️ **Left steers, right drives, and `Q83` deliberately left that open.** It
## says "one outer corner" and "other outer corner" and never commits to a side;
## `Q97` chose, on the two touch racers `Q80` already cites as references. The
## sides are named here rather than in `input_router.gd` so that swapping them
## is one edit to a `.tres` reader and not a hunt through input code.
@export var touch_zone_left: Rect2
@export var touch_zone_right: Rect2

## Where a resting thumb actually covers the screen. **Nothing the HUD draws may
## intersect these.** Sized as a fingertip in each outer bottom corner.
@export var thumb_rest_left: Rect2
@export var thumb_rest_right: Rect2

## ⚠️ **There is no throttle rect, and auto-accelerate is no longer why.** Touch
## drives its own throttle since `Q83`, on the positive half of one vertical axis
## whose negative half is `brake_reverse` — a control that shares an axis with
## one already placed needs no rest of its own.
##
## 🔴 **A genuinely new control still lands a third rest here, and the check
## failing is the correct outcome rather than a regression to work around.** That
## rule used to stand on the prediction that a throttle is such a control, which
## `Q83` falsified. The rule is what survived, not the prediction.
##
## ⚠️ **Both thumbs are relative, which is why these rects did not have to grow.**
## An absolute slider needs travel, and there is none: `speed` and `street_plate`
## share a baseline at y 860 against rests starting at y 880, so 20 px of growth
## collides with a drawn readout.

## Path to the shipped table. Named here so `hud.gd` and `verify_hud.gd` cannot
## end up loading two different files — a check that names its own path can go
## green while the game loads something else.
const PATH: String = "res://tuning/hud_layout.tres"


## The three slots this HUD reserves and does not yet fill, by node name.
## Iterated by `hud.gd` to build them, so both ends stay statically typed —
## an array of `[name, rect]` pairs makes each element a `Variant` and defeats
## the enforced typing at exactly the point a wrong rect would be silent.
func reserved_slots() -> Dictionary[String, Rect2]:
	return {"MinimapSlot": minimap, "TimerSlot": timer, "MeterSlot": meter}


## Everything this HUD draws, by name.
##
## ⚠️ **A dictionary and not two parallel arrays.** The first version zipped
## `hud_rects()` against `hud_names()` by index, in three pairs, with the name
## halves `static` and the rect halves not — so adding a rect and forgetting its
## name would silently mislabel every later slot or read past the end, in the one
## file whose entire job is to be trusted about where things are.
func hud_slots() -> Dictionary[String, Rect2]:
	var slots: Dictionary[String, Rect2] = {
		"speed": speed, "street_plate": street_plate, "wrong_way": wrong_way
	}
	slots.merge(reserved_slots())
	return slots


## The fingertip rects the HUD must keep clear of.
func thumb_slots() -> Dictionary[String, Rect2]:
	return {"thumb_rest_left": thumb_rest_left, "thumb_rest_right": thumb_rest_right}


## The tap-detection zones. Recorded for `P2-4`; the HUD may overlap these and
## the check deliberately does not look at them.
func zone_slots() -> Dictionary[String, Rect2]:
	return {"touch_zone_left": touch_zone_left, "touch_zone_right": touch_zone_right}


## The zone thumb 2 steers in.
##
## 🔴 **Handedness lives in these two functions and nowhere else.** `Q83` left
## the side open on purpose — "one outer corner", "other outer corner" — so
## something had to choose, and a choice spread through `input_router.gd` as two
## literal rect names is a choice nobody can reverse. Swapping the bodies of
## these two swaps the scheme, and `P3-5b`'s "one-handed layout" is where a
## player-facing toggle would replace them.
func steer_zone() -> Rect2:
	return touch_zone_left


## The zone thumb 1 drives in: `accelerate` above its origin, `brake_reverse`
## below, on one bipolar axis (`Q83`).
func drive_zone() -> Rect2:
	return touch_zone_right


## Every (hud, thumb) pair that overlaps, as `"hud_name/thumb_name"`.
##
## ⚠️ **`Rect2.intersects` excludes touching edges by default**, which is what is
## wanted: a readout whose bottom edge is exactly a thumb rest's top edge is
## adjacent, not overlapping, and refusing that would force a gap nobody asked
## for.
func collisions() -> PackedStringArray:
	var found := PackedStringArray()
	var thumbs: Dictionary[String, Rect2] = thumb_slots()
	var huds: Dictionary[String, Rect2] = hud_slots()
	for hud_name: String in huds:
		for thumb_name: String in thumbs:
			if huds[hud_name].intersects(thumbs[thumb_name]):
				found.append("%s/%s" % [hud_name, thumb_name])
	return found


## True where every rect sits inside the design resolution. A slot half off the
## right edge is invisible on every device rather than on some of them, and it
## is the kind of thing a hand-edited `.tres` produces.
func within_design() -> PackedStringArray:
	var outside := PackedStringArray()
	var screen := Rect2(Vector2.ZERO, design_size)
	var all: Dictionary[String, Rect2] = hud_slots()
	all.merge(thumb_slots())
	all.merge(zone_slots())
	for slot_name: String in all:
		if not screen.encloses(all[slot_name]):
			outside.append(slot_name)
	return outside


# ---- placing a design-space rect on a real screen ----
#
# 🔴 **These live here rather than in `hud.gd` because there are two placers.**
# `P2-4`'s touch zones must land in the *same* frame the rects above reserve —
# same anchor derivation, same safe-area inset — or a thumb rest and the zone it
# sits in disagree by the width of a notch, on the one device where it matters
# and on no desk. A second copy of this arithmetic is exactly the drift
# `verify_hud.gd` exists to prevent, so there is one copy and it is here, beside
# the table it reads.


## Put `control` where the layout says, converting a design-space rect into
## anchors so the slot keeps its corner when the window is not 16:9.
##
## The anchor is **derived** from where the rect sits rather than passed in: a
## slot in the left third holds the left edge, one in the right third holds the
## right edge, and anything spanning the middle holds the centre. Per-slot
## anchor arguments would be a second table to keep in step with the first.
func place(parent: Control, control: Control, design: Rect2) -> void:
	parent.add_child(control)
	control.anchor_left = axis(design.position.x, design.end.x, design_size.x).x
	control.anchor_right = control.anchor_left
	control.anchor_top = axis(design.position.y, design.end.y, design_size.y).x
	control.anchor_bottom = control.anchor_top
	offsets(control, design, design)


## Write `control`'s offsets so it covers `rect`, against the anchors that
## `anchored_on` resolves to.
##
## The two rects differ only for the street plate, which is drawn smaller than
## the slot it is anchored in — and the anchor must stay the slot's, or the
## plate re-pins itself to the far edge the first time a short name shrinks it
## across a screen third.
func offsets(control: Control, rect: Rect2, anchored_on: Rect2) -> void:
	var origin := Vector2(
		axis(anchored_on.position.x, anchored_on.end.x, design_size.x).y,
		axis(anchored_on.position.y, anchored_on.end.y, design_size.y).y
	)
	control.offset_left = rect.position.x - origin.x
	control.offset_right = rect.end.x - origin.x
	control.offset_top = rect.position.y - origin.y
	control.offset_bottom = rect.end.y - origin.y


## Returns `(anchor, the design coordinate that anchor sits at)` for one axis.
static func axis(from: float, to: float, extent: float) -> Vector2:
	if to <= extent * 0.35:
		return Vector2(0.0, 0.0)
	if from >= extent * 0.65:
		return Vector2(1.0, extent)
	return Vector2(0.5, extent * 0.5)


## The full-screen Control everything anchored by `place` sits inside, already
## pulled in by the safe area.
##
## 🔴 **Shared for the same reason the placer is.** The zones and the HUD must
## resolve in one frame, and the frame is not only the inset — it is the root the
## inset is applied to. Two copies of this drift the day someone changes the
## anchor preset or the mouse filter in one of them, and the touch zones then
## resolve a notch away from the rests the HUD is keeping clear, invisibly.
##
## ⚠️ **`parent` is a `Node`, not a `Control`**: `hud.gd` parents to itself and
## the router to a `CanvasLayer` of its own, and neither is a `Control`.
static func safe_root(parent: Node) -> Control:
	var root := Control.new()
	root.name = "Safe"
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(root)
	inset_for_safe_area(root)
	return root


## Pull `root` in by the display's safe area, for a notch or a rounded corner.
##
## ⚠️ **Measured in screen pixels and applied in canvas units**, which are not
## the same thing under `canvas_items` stretch — the ratio is what converts
## them. Applying the raw pixel inset would over-inset by the stretch factor on
## every device whose panel is not 1920 wide, which is all of them.
static func inset_for_safe_area(root: Control) -> void:
	var screen: Vector2i = DisplayServer.screen_get_size()
	var window: Vector2i = DisplayServer.window_get_size()
	if screen.x <= 0 or screen.y <= 0 or window.x <= 0 or window.y <= 0:
		return

	# 🔴 **The safe area is measured against the SCREEN, not against the window,
	# and conflating the two deletes the whole HUD.** `get_display_safe_area()`
	# returns a rect in display coordinates; on a handset the window fills the
	# display and the two frames coincide, which is the case the API is for. In
	# a desktop window they do not — the window is smaller than the screen — so
	# `screen - window` came out *negative*, the root Control grew larger than
	# the viewport instead of smaller, and everything anchored to an edge was
	# pushed off it. The frame renders perfectly with no HUD on it, nothing is
	# logged, and `check.sh` is green: this was found by looking at a screenshot
	# and by nothing else.
	#
	# So the inset applies only where it means anything — a window that fills
	# the display — and every side is clamped at zero so that no arithmetic here
	# can ever make the HUD bigger than the screen again.
	if window != screen:
		return

	var safe: Rect2i = DisplayServer.get_display_safe_area()
	var canvas: Vector2 = root.get_viewport_rect().size
	# Not `scale` — `CanvasLayer` already has one, and the warnings sweep
	# promotes shadowing to an error. Naming it for what it is anyway. The ratio
	# converts screen pixels into canvas units, which `canvas_items` stretch
	# makes different numbers on every panel that is not 1920 wide.
	var canvas_per_pixel := Vector2(canvas.x / float(screen.x), canvas.y / float(screen.y))
	root.offset_left = maxf(0.0, float(safe.position.x)) * canvas_per_pixel.x
	root.offset_top = maxf(0.0, float(safe.position.y)) * canvas_per_pixel.y
	root.offset_right = -maxf(0.0, float(screen.x - safe.end.x)) * canvas_per_pixel.x
	root.offset_bottom = -maxf(0.0, float(screen.y - safe.end.y)) * canvas_per_pixel.y
