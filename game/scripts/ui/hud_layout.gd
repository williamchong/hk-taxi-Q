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
## that the hard way — see the block above `touch_steer_left` for the reference
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
@export var design_size: Vector2 = Vector2(1920.0, 1080.0)

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
#
# The middle mattered immediately: the plate started bottom-centre and sat over
# the vanishing point and the car. The pairing was the second correction — the
# plate was moved into the left column beside the speed, which put "where am I"
# next to "how fast" and left the map it belongs with in the other corner.

## Speed, bottom-left, big. Raised clear of the left thumb rather than sitting
## in the corner: MM2 is a keyboard game and could use the very corner, and we
## cannot.
@export var speed: Rect2 = Rect2(48.0, 660.0, 280.0, 200.0)
## The bilingual street name plate, stacked directly above the speed in the
## bottom-left column.
##
## 🔴 **Not bottom-centre, which is where it started**, and not the left column
## either, which is where it went next. The middle of the frame is the road —
## the vanishing point, the lane you are about to be in, and the car — and a
## bright white slab sat in it. The left column then put it beside the speed,
## which pairs it with an instrument; a street name and a street map are the
## same question, so it sits above the minimap instead.
##
## ⚠️ **This is the plate's MAXIMUM box and its anchor, not its drawn size.** A
## street sign is cut to its lettering, and a fixed-width one leaves
## `SHARP STREET` floating in the middle of a slab sized for
## `CROSS HARBOUR TUNNEL` — which is what makes it read as a dialog rather than
## as signage. `hud.gd::_fit_plate` shrinks it to its text about this rect's
## centre and clamps to this width, so the reservation the check grades stays
## the honest worst case.
@export var street_plate: Rect2 = Rect2(1412.0, 530.0, 460.0, 96.0)

# ---- reserved, drawn empty, filled by P3-5a and P3-5b ----

## `P3-5b`. Bottom-right, where MM2 puts it — **not** top-left, which is where
## this layout had it before the references were looked at. A street map is
## glanced at mid-corner and belongs near the road, not in the far corner of
## the screen. The street plate sits directly above it, because the two are one
## question.
@export var minimap: Rect2 = Rect2(1568.0, 600.0, 304.0, 260.0)
## `P3-5a`'s fare timer. Top-left and large, which is where the arcade-taxi
## reference puts its game clock.
@export var timer: Rect2 = Rect2(48.0, 48.0, 380.0, 150.0)
## `P3-5a`'s fare meter, top-right, on the same reference's `$` readout.
##
## ⚠️ Named `meter` and not `target`: it was `target` while this layout still
## expected to hold a destination callout, and the references moved that into
## the world (see below). A rect whose name promises a destination is how the
## next task puts one back on the screen without meaning to.
@export var meter: Rect2 = Rect2(1440.0, 48.0, 432.0, 170.0)

## ⚠️ **There is deliberately NO slot for the destination arrow**, and that is a
## finding rather than an omission. Both references that have a destination put
## the arrow **in the world** — the arcade taxi floats a green arrow above the
## car, MM2 hangs a banner over the road — not in the HUD. It also sits better
## with `GAME_DESIGN.md`'s "navigate by memory, not by minimap" than a screen-
## edge chevron would. `P3-5a` should build a world-space marker, and if it ever
## wants a screen slot it should add one here on purpose.

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

## Where taps are detected. Informational: `P2-4` reads these, and the HUD is
## explicitly ALLOWED to overlap them.
@export var touch_steer_left: Rect2 = Rect2(0.0, 480.0, 560.0, 600.0)
@export var touch_steer_right: Rect2 = Rect2(1360.0, 480.0, 560.0, 600.0)

## Where a resting thumb actually covers the screen. **Nothing the HUD draws may
## intersect these.** Sized as a fingertip in each outer bottom corner.
@export var thumb_rest_left: Rect2 = Rect2(0.0, 880.0, 280.0, 200.0)
@export var thumb_rest_right: Rect2 = Rect2(1640.0, 880.0, 280.0, 200.0)

## ⚠️ **Auto-accelerate is why there is no throttle rect.** `InputRouter`'s touch
## default is that the player only steers, brakes and drifts. If that default is
## ever reversed, a third rest lands here and the check will start failing
## against whatever the HUD has grown into — which is the correct outcome, not a
## regression to work around.

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
	var slots: Dictionary[String, Rect2] = {"speed": speed, "street_plate": street_plate}
	slots.merge(reserved_slots())
	return slots


## The fingertip rects the HUD must keep clear of.
func thumb_slots() -> Dictionary[String, Rect2]:
	return {"thumb_rest_left": thumb_rest_left, "thumb_rest_right": thumb_rest_right}


## The tap-detection zones. Recorded for `P2-4`; the HUD may overlap these and
## the check deliberately does not look at them.
func zone_slots() -> Dictionary[String, Rect2]:
	return {"touch_steer_left": touch_steer_left, "touch_steer_right": touch_steer_right}


## Every (hud, thumb) pair that overlaps, as `"hud_name/thumb_name"`.
##
## ⚠️ **`Rect2.intersects` excludes touching edges by default**, which is what is
## wanted: a readout whose bottom edge is exactly a thumb rest's top edge is
## adjacent, not overlapping, and refusing that would force a gap nobody asked
## for.
func collisions() -> PackedStringArray:
	var found := PackedStringArray()
	var thumbs: Dictionary[String, Rect2] = thumb_slots()
	for hud_name: String in hud_slots():
		for thumb_name: String in thumbs:
			if hud_slots()[hud_name].intersects(thumbs[thumb_name]):
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
