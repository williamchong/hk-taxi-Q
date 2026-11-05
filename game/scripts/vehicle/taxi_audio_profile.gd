class_name TaxiAudioProfile
extends Resource
## The taxi's own sounds (`P3-79`): what `TaxiAudio` plays off the car and what
## `TaxiHire` plays off the fare. The rationale for each value is in
## `tuning/taxi_audio.md`; what each *is* is here.
##
## 🔴 **No `@export` here declares a default**, on `TaxiDoorProfile`'s convention:
## a missing key reads as zero, and `usable()` refuses a zero rather than fall
## back to a literal. The two exceptions are switches, where zero is a choice:
## `hybrid` and the decibel levels, which may be 0 dB.

## Path to the shipped table.
const PATH: String = "res://tuning/taxi_audio.tres"

@export_group("Engine")
## Which engine the taxi has: off is the Crown Comfort LPG's four through a
## 4-speed automatic, the car `crown_comfort.tres` describes; on is the Comfort
## Hybrid's, the EV motor's whine with the engine cutting in on a CVT.
@export var hybrid: bool
## The engine loops' reference rpm, low to high: each file is whole engine cycles
## at its rpm. Mirrors `tools/make_vehicle_sounds.py`'s `ENGINE_RPMS`.
@export var loop_rpms: PackedFloat32Array
## The engine at rest.
@export_range(300.0, 2000.0, 10.0, "suffix:rpm") var idle_rpm: float
## The engine's ceiling, where the rev limiter holds it.
@export_range(3000.0, 9000.0, 10.0, "suffix:rpm") var redline_rpm: float
## Rpm per kph in each forward gear, first to top: the gearbox and final drive.
@export var rpm_per_kph: PackedFloat32Array
## The box changes up at this rpm with the pedal down, and at
## `upshift_light_share` of it with the pedal light.
@export_range(1000.0, 9000.0, 10.0, "suffix:rpm") var upshift_rpm: float
@export_range(0.1, 1.0, 0.01) var upshift_light_share: float
## The box changes down under this rpm.
@export_range(500.0, 5000.0, 10.0, "suffix:rpm") var downshift_rpm: float
## Off the line the torque converter lets the engine run up to this over idle
## with the pedal down, before the wheels' speed takes it.
@export_range(0.0, 5000.0, 10.0, "suffix:rpm") var stall_rpm: float
## How fast the heard rpm follows the box's, in rpm a second.
@export_range(100.0, 50000.0, 100.0, "suffix:rpm/s") var rpm_slew: float
@export_range(-40.0, 12.0, 0.5, "suffix:dB") var engine_db: float
## How much quieter the engine is with the pedal up.
@export_range(0.0, 30.0, 0.5, "suffix:dB") var off_throttle_cut_db: float
## How long every loop takes to fall silent once the car is parked (the menu's
## showroom, HOME and REPORT). 0 cuts at once.
@export_range(0.0, 5.0, 0.05, "suffix:s") var park_fade_s: float

@export_group("Hybrid")
## The kph the EV whine's loop was made at (`EV_REF_KPH`).
@export_range(1.0, 200.0, 1.0, "suffix:km/h") var ev_ref_kph: float
@export_range(-40.0, 12.0, 0.5, "suffix:dB") var ev_db: float
## The engine starts over this speed, or over `engine_on_throttle` of pedal.
@export_range(0.0, 200.0, 1.0, "suffix:km/h") var engine_on_kph: float
@export_range(0.0, 1.0, 0.01) var engine_on_throttle: float
## The CVT holds the engine between these, by the pedal.
@export_range(500.0, 9000.0, 10.0, "suffix:rpm") var cvt_low_rpm: float
@export_range(500.0, 9000.0, 10.0, "suffix:rpm") var cvt_high_rpm: float

@export_group("Tyres and air")
## Slip, in multiples of the tyre's peak, at which the squeal is full. It starts
## at `SkidMarksProfile.mark_from_slip`, so the sound and the marks agree.
@export_range(1.0, 10.0, 0.05) var skid_full_slip: float
@export_range(-40.0, 12.0, 0.5, "suffix:dB") var skid_db: float
## The squeal's pitch rises by this share from its start to full.
@export_range(0.0, 1.0, 0.01) var skid_pitch_rise: float
## The speed at which a slide's squeal is at its full level; slower, it falls
## towards `skid_slow_share` of it.
@export_range(1.0, 200.0, 1.0, "suffix:kph") var skid_full_kph: float
## The share of the squeal a slide at a standstill keeps (a wheelspin).
@export_range(0.0, 1.0, 0.05) var skid_slow_share: float
## How far the squeal's pitch moves from a crawl to `skid_full_kph`, centred.
@export_range(0.0, 1.0, 0.01) var skid_speed_pitch: float
## The wind starts at one speed and is full at the other.
@export_range(0.0, 300.0, 1.0, "suffix:km/h") var wind_from_kph: float
@export_range(1.0, 300.0, 1.0, "suffix:km/h") var wind_full_kph: float
@export_range(-40.0, 12.0, 0.5, "suffix:dB") var wind_db: float

@export_group("Impacts")
## Under this speed into a contact there is no sound: a nudge. The bump and
## crash tiers are `SkillProfile.bump_min_kph` and `crash_min_kph`, the award's.
@export_range(0.1, 20.0, 0.1, "suffix:m/s") var tap_min_mps: float
## A second impact inside this is part of the first.
@export_range(0.01, 2.0, 0.01, "suffix:s") var impact_cool_s: float
@export_range(-40.0, 12.0, 0.5, "suffix:dB") var impact_db: float
## What a struck body is, by a piece of its node's name, first match wins: the
## top layer `top_<what>.wav` laid over the hit. A body matching none is a wall,
## and a wall has no top: the dead thud alone.
@export var materials: Dictionary[String, String]
## The scrape starts sliding along a wall at one speed and is full at the other.
@export_range(0.1, 50.0, 0.1, "suffix:m/s") var scrape_from_mps: float
@export_range(0.1, 50.0, 0.1, "suffix:m/s") var scrape_full_mps: float
@export_range(-40.0, 12.0, 0.5, "suffix:dB") var scrape_db: float
## A landing sounds after at least this long in the air.
@export_range(0.05, 5.0, 0.05, "suffix:s") var land_min_air_s: float

@export_group("Cabin")
@export_range(-40.0, 12.0, 0.5, "suffix:dB") var cabin_db: float
## At the delivery, one coin per this many HK$ of tip and time bonus, up to
## `coin_max`, `coin_gap_s` apart after the card reader's beep.
@export_range(0.1, 100.0, 0.1, "suffix:HK$") var coin_hkd: float
@export_range(1, 100, 1) var coin_max: int
@export_range(0.01, 1.0, 0.01, "suffix:s") var coin_gap_s: float
@export_range(0.0, 2.0, 0.01, "suffix:s") var coin_after_s: float


## Whether the table is whole. Pure over the table, so `verify_vehicle.gd` can
## ask it.
func usable(who: String) -> bool:
	var required: Dictionary[String, float] = {
		"loop_rpms": float(loop_rpms.size()),
		"idle_rpm": idle_rpm,
		"redline_rpm": redline_rpm,
		"rpm_per_kph": float(rpm_per_kph.size()),
		"upshift_rpm": upshift_rpm,
		"upshift_light_share": upshift_light_share,
		"downshift_rpm": downshift_rpm,
		"rpm_slew": rpm_slew,
		"ev_ref_kph": ev_ref_kph,
		"cvt_low_rpm": cvt_low_rpm,
		"cvt_high_rpm": cvt_high_rpm,
		"skid_full_slip": skid_full_slip,
		"skid_full_kph": skid_full_kph,
		"wind_full_kph": wind_full_kph,
		"tap_min_mps": tap_min_mps,
		"impact_cool_s": impact_cool_s,
		"scrape_from_mps": scrape_from_mps,
		"scrape_full_mps": scrape_full_mps,
		"land_min_air_s": land_min_air_s,
		"materials": float(materials.size()),
		"coin_hkd": coin_hkd,
		"coin_max": float(coin_max),
		"coin_gap_s": coin_gap_s,
	}
	return not TuningTable.any_zero(self, required, who, "the taxi is silent")


## The gear the box holds at `speed_kph` with `throttle` down, from `gear` (0 is
## first). One change a call: up past the upshift point, down under the
## downshift point.
func gear_after(gear: int, speed_kph: float, throttle: float) -> int:
	var top: int = rpm_per_kph.size() - 1
	gear = clampi(gear, 0, top)
	var up_at: float = upshift_rpm * lerpf(upshift_light_share, 1.0, clampf(throttle, 0.0, 1.0))
	if gear < top and absf(speed_kph) * rpm_per_kph[gear] > up_at:
		return gear + 1
	if gear > 0 and absf(speed_kph) * rpm_per_kph[gear] < downshift_rpm:
		return gear - 1
	return gear


## The rpm the box asks of the engine in `gear` at `speed_kph`: the wheels' own,
## or the converter's stall with the pedal down, whichever is higher; never under
## idle nor over the redline.
func rpm_in(gear: int, speed_kph: float, throttle: float) -> float:
	var wheels: float = absf(speed_kph) * rpm_per_kph[clampi(gear, 0, rpm_per_kph.size() - 1)]
	var stall: float = idle_rpm + stall_rpm * clampf(throttle, 0.0, 1.0)
	return clampf(maxf(wheels, stall), idle_rpm, redline_rpm)


## The hybrid's engine rpm, 0 when the engine is off.
func hybrid_rpm(speed_kph: float, throttle: float) -> float:
	if absf(speed_kph) < engine_on_kph and throttle < engine_on_throttle:
		return 0.0
	return lerpf(cvt_low_rpm, cvt_high_rpm, clampf(throttle, 0.0, 1.0))


## Each engine loop's share of the mix at `rpm`, crossfaded between the two
## loops either side of it in log rpm — so the louder of two plays within the
## square root of their ratio of its own pitch — and the pitch each plays at.
func loop_mix(rpm: float) -> Array[Vector2]:
	var out: Array[Vector2] = []
	var count: int = loop_rpms.size()
	var at: float = log(rpm)
	for i: int in count:
		var share: float = 0.0
		var here: float = log(loop_rpms[i])
		if at <= here:
			share = (
				1.0 if i == 0 else clampf(inverse_lerp(log(loop_rpms[i - 1]), here, at), 0.0, 1.0)
			)
		else:
			share = (
				1.0
				if i + 1 == count
				else clampf(inverse_lerp(log(loop_rpms[i + 1]), here, at), 0.0, 1.0)
			)
		out.append(Vector2(share, rpm / loop_rpms[i]))
	return out


## What `body` is, off `materials`: "" for a wall, or a body that is gone.
func material_of(body: Object) -> String:
	if not is_instance_valid(body):
		return ""
	var node := body as Node
	if node == null:
		return ""
	var name: String = String(node.name)
	for piece: String in materials:
		if name.contains(piece):
			return materials[piece]
	return ""
