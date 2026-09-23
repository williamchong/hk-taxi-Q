extends Node
## The fare loop's state on the dev overlay (`P3-1a`): what `FareSystem` is
## doing, where the passenger is going, the clock and the 咪錶, as text under
## `--debug-view=full`. Its only face until `P3-5a` gives it the HUD's.
##
## A sibling script rather than lines in `fare_system.gd`, on
## `road_graph_overlay.gd`'s pattern: this one names the `DebugHud` autoload
## and the system must not, because `tools/verify_fares.gd` loads the system
## before any autoload is registered, and a script naming one fails to compile
## there. Rebuilt on the system's `sampled` signal — 5 Hz — and never per
## frame: `Label.text` is a TextServer reshape, the cost `hud.gd` guards.

## The system this reads. Set by the scene.
@export var fares: FareSystem

var _label: Label = null


func _ready() -> void:
	if fares == null:
		push_warning("FareReadout has no FareSystem assigned; nothing to show.")
		return
	_label = Label.new()
	_label.name = "FareReadout"
	DebugHud.attach_readout(_label)
	fares.sampled.connect(_refresh)
	_refresh()


func _exit_tree() -> void:
	# A label parented to the autoload outlives this scene and would otherwise
	# stack up one per scene change. `debug_hud.gd::attach_readout` says so.
	if _label != null:
		DebugHud.detach_readout(_label)
		_label = null


func _refresh() -> void:
	if _label == null or not DebugHud.shows_readouts():
		return
	var lines: PackedStringArray = [
		(
			"fares  HK$%.1f earned  %d delivered  %d bailed  %d refused"
			% [fares.earned_hkd, fares.deliveries, fares.bails, fares.hail_refusals]
		)
	]
	var fare: Fare = fares.fare
	match fares.state:
		FareSystem.State.IDLE:
			lines.append("idle" if fares.armed() else "idle — leave the stand to hail")
			if fare != null:
				lines.append("last  HK$%.1f  (tip HK$%.1f)" % [fare.banked_hkd, fare.tip_hkd])
		FareSystem.State.BOARDING:
			lines.append(
				"boarding  → %s / %s" % [fare.destination.name_en(), fare.destination.name_zh()]
			)
		FareSystem.State.CARRYING:
			lines.append(
				(
					"→ %s / %s  par %.0f m  left %.0f m"
					% [
						fare.destination.name_en(),
						fare.destination.name_zh(),
						fare.par_m,
						fare.remaining_road_m
					]
				)
			)
			lines.append(
				(
					"meter HK$%.1f  clock %.0f / %.0f s"
					% [fare.meter.reading_hkd(), fare.remaining_s, fare.allowance_s]
				)
			)
	_label.text = "\n".join(lines)
