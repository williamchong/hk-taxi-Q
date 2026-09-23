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
## player *earned* — here the seconds left on the allowance, later the style
## chain (`P3-2b`) — and both bank as one HK$ sum. A shortcut lowers the meter
## and raises the tip, which is the design.

enum Kind { SHORT_HOP, STANDARD }


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

	func name_en() -> String:
		var names: Dictionary = node.get("name", {})
		var found: Variant = names.get("en", null)
		return "" if found == null else str(found)

	func name_zh() -> String:
		var names: Dictionary = node.get("name", {})
		var found: Variant = names.get("zh", null)
		return "" if found == null else str(found)

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
var meter: FareMeter = null
var tip_hkd: float = 0.0
## What delivery paid: the reading plus the tip; 0 on a bail.
var banked_hkd: float = 0.0


## A destination node's kind. `taxi_stand` is standard and `pudo` a short hop;
## nothing else is drawn, so nothing else arrives here.
static func kind_of(node: Dictionary) -> Kind:
	return Kind.SHORT_HOP if str(node.get("kind", "")) == "pudo" else Kind.STANDARD
