class_name Fare
extends RefCounted
## One fare, from the hail to the money (`P3-1a`, `Q141`): where it was hailed,
## where it goes, what the router said the drive is, how long it has, and what
## the 咪錶 reads. `FareSystem` writes it; the HUD (`P3-5a`) and the score
## (`P3-2b`) read it.
##
## **The kind is the DESTINATION's.** `GAME_DESIGN.md` names a short hop by its
## `pudo` and a standard fare by its `taxi_stand`; a trip is what it is by where
## it ends. Cross-harbour and long haul are `P3-1b`'s kinds and are not drawn.
##
## **The money is two numbers, and stays two.** `meter` is the tariff on what
## was driven and waited, honest to the cent; `tip_hkd` is everything the
## player *earned* — the seconds left on the allowance (`time_hkd`) and the
## skills paid on the way (`skills_hkd`, `P3-49`), later the style chain
## (`P3-2b`) — and both bank as one HK$ sum. A shortcut lowers the meter and
## raises the tip, which is the design. `awards` is the receipt: what each
## skill paid, in the order it was earned, so the HUD can say WHY there was a
## tip (`Q145`).

enum Kind { SHORT_HOP, STANDARD }

## What a skill is. Drift, speed and early arrival pay today; near miss and
## air are slots, waiting on `B3`'s traffic and on something to jump off.
## `CRASH` is the first PENALTY (`P3-50`, planned): an award whose `hkd` is
## negative, on the same receipt — the passenger docks the tip, never the
## meter, and the tip floors at zero.
enum Skill { DRIFT, SPEED, EARLY, NEAR_MISS, AIR, CRASH }


## One skill paid, in HK$ — negative for a penalty.
class Award:
	extends RefCounted
	var skill: Skill = Skill.DRIFT
	var hkd: float = 0.0

	func _init(paid_skill: Skill, paid_hkd: float) -> void:
		skill = paid_skill
		hkd = paid_hkd


## A published fare node resolved into the merged graph's frame: the stop
## point on the road, not the kerbside `pos` the passenger stands at.
class Stop:
	extends RefCounted
	var region: String = ""
	var id: String = ""
	var node: Dictionary = {}
	## `nearest_edge` as the merged graph names it; -1 where the region never
	## published it.
	var edge: int = -1
	var t: float = 0.0
	## `RoadGraph.point_at(edge, t)` plus the region's offset.
	var point: Vector3 = Vector3.ZERO
	## The street the stop is on, from the graph at load; "" where unnamed.
	var road_en: String = ""
	var road_zh: String = ""

	## What a passenger calls this stop (`Q142`) in `language`: the named
	## building the document put beside it, or the publisher's description of
	## the kerb where there is none. Either language may fall back on its own.
	func place(language: String) -> String:
		var found: String = _text(node.get("place", null), language)
		return found if not found.is_empty() else name(language)

	## The street the stop is on, in `language`; "" where unnamed.
	func road(language: String) -> String:
		return road_zh if language == Locale.CHINESE else road_en

	func name(language: String) -> String:
		return _text(node.get("name", null), language)

	static func _text(names: Variant, language: String) -> String:
		if not names is Dictionary:
			return ""
		var found: Variant = (names as Dictionary).get(language, null)
		return "" if found == null else str(found)

	func name_en() -> String:
		return name("en")

	func name_zh() -> String:
		return name("zh")

	func same_as(other: Stop) -> bool:
		return other != null and other.region == region and other.id == id


var kind: Kind = Kind.STANDARD
var pickup: Stop = null
var destination: Stop = null
## The legal route's length at the hail, in metres, or the plan distance where
## none was found — which cannot happen for a drawn destination, but is the
## defined answer rather than an assert (`Q137`).
var par_m: float = 0.0
var plan_m: float = 0.0
var route_found: bool = false
## Seconds granted at boarding, and seconds left now.
var allowance_s: float = 0.0
var remaining_s: float = 0.0
## The legal road distance still to drive, refreshed at the sample rate from
## wherever the car is; what the arrow and the pip read (`P3-5a`).
var remaining_road_m: float = 0.0
## The legal route itself, from wherever the car was last sampled to the
## destination (`P3-46`): the hail's from the pickup, then refreshed with
## `remaining_road_m`. Null until the hail; `found` false where the car's edge
## reaches nothing — the map then draws no line and says so by drawing none.
var route: RoadRouter.Route = null
## Where along `route.edges[0]` the route starts, 0..1: the pickup's `t` at the
## hail, the car's `Hit.t` after.
var route_from_t: float = 0.0
var meter: FareMeter = null
## The tip: `time_hkd` plus `skills_hkd`. Live while carrying — what the
## passenger would tip if they got out now — frozen at delivery, 0 on a bail.
var tip_hkd: float = 0.0
## The seconds left on the allowance, priced: falling while carrying, the
## door's value after delivery, 0 on a bail.
var time_hkd: float = 0.0
## Everything the skills paid, banked or not: the sum of `awards`.
var skills_hkd: float = 0.0
## Each skill paid, in the order it was earned. Kept on a bail too — the
## receipt then says what walked out of the door.
var awards: Array[Award] = []
## What delivery paid: the reading plus the tip; 0 on a bail.
var banked_hkd: float = 0.0


## How many of `awards` are `skill`.
func count_of(skill: Skill) -> int:
	var count: int = 0
	for award: Award in awards:
		if award.skill == skill:
			count += 1
	return count


## A destination node's kind. `taxi_stand` is standard and `pudo` a short hop;
## nothing else is drawn, so nothing else arrives here.
static func kind_of(node: Dictionary) -> Kind:
	return Kind.SHORT_HOP if str(node.get("kind", "")) == "pudo" else Kind.STANDARD
