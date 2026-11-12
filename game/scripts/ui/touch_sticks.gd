class_name TouchSticks
extends Control
## The thumbs' sticks on a touch screen (`Q204`, the user's ask, reversing
## `Q97`'s "no visible touch chrome").
##
## At rest, a faint hint where each thumb goes: a sideways track with ◀ ▶ for
## steering, an upright one with ▲ ▼ for the pedals. Under a thumb, the same
## track stands where the finger LANDED — both thumbs are relative (`Q83`) — and
## fills from there to the finger, clamped at the travel `touch.tres` gives, so
## the player sees how hard they are steering and pressing.
##
## 🔴 **Steering draws its sideways travel only and the pedals their upright
## travel only.** The other axis of each thumb drives nothing, and the driving
## thumb's sideways one is kept for the handbrake (`input_router.gd`): a stick
## that drew it would teach a gesture that is not there.
##
## One node and ONE draw, a vertex-coloured mesh as `HeadUpFrame` is; rebuilt
## only on a frame where a thumb moved.

## Points around a circle.
const ROUND: int = 24
## The track's share of its stick's ink: the travel faint, the push solid.
const TRACK_SHARE: float = 0.35
## `HudStyle.touch_look`: the bare tracks, or a car's controls — a wheel for
## the steering thumb, and pedals or a lever for the driving one. Every look
## reads the same thumbs the same way; only the drawing differs.
const LOOK_TRACKS: String = "tracks"
const LOOK_WHEEL_PEDALS: String = "wheel_pedals"
const LOOK_WHEEL_LEVER: String = "wheel_lever"
## How far the drawn wheel turns at full lock: a quarter turn and a third, so a
## half-lock reads as a turn and not a twitch.
const WHEEL_LOCK_DEG: float = 120.0

var style: HudStyle = null
## The current car's wheel, drawn under the steering thumb; null draws a bare rim.
var wheel: SteeringWheelLook = null
## Where each hint stands: the middle of its thumb's rest, placed by the
## layout's own placer so it moves with the safe area and the scale.
var _steer_home: Control = null
var _drive_home: Control = null
var _router: Node = null
## What was drawn last — both thumbs, and the steer and push the router read off
## them, which it writes a physics step after the points move — so an idle frame
## costs a comparison and no mesh.
var _steer_drawn := PackedVector2Array()
var _drive_drawn := PackedVector2Array()
var _values_drawn := Vector2.ZERO
var _mesh: ArrayMesh = null


## The sticks for `layout`, in `hud_style`, full-rect over the safe root.
static func make(hud_style: HudStyle, layout: HudLayout) -> TouchSticks:
	var sticks := TouchSticks.new()
	sticks.name = "TouchSticks"
	sticks.style = hud_style
	var car: CarSpec = load(CarSpec.PATH) as CarSpec
	if car != null:
		sticks.wheel = car.steering_wheel
	sticks.mouse_filter = Control.MOUSE_FILTER_IGNORE
	sticks.set_anchors_preset(Control.PRESET_FULL_RECT)
	sticks._steer_home = _home(sticks, layout, layout.thumb_rest_left, "SteerHome")
	sticks._drive_home = _home(sticks, layout, layout.thumb_rest_right, "DriveHome")
	return sticks


static func _home(parent: Control, layout: HudLayout, rest: Rect2, home_name: String) -> Control:
	var home := Control.new()
	home.name = home_name
	home.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layout.place(parent, home, rest)
	return home


func _ready() -> void:
	# By path: an autoload's identifier does not exist under a `--script` tool.
	_router = get_node_or_null(^"/root/InputRouter")


func _process(_delta: float) -> void:
	if _router == null:
		return
	var steer: PackedVector2Array = _router.steer_touch()
	var drive: PackedVector2Array = _router.drive_touch()
	var values := Vector2(
		_router.steer if steer.size() == 2 else 0.0,
		_router.accelerate - _router.brake_reverse if drive.size() == 2 else 0.0
	)
	if steer != _steer_drawn or drive != _drive_drawn or values != _values_drawn:
		_steer_drawn = steer
		_drive_drawn = drive
		_values_drawn = values
		queue_redraw()


func _draw() -> void:
	if style == null or _router == null:
		return
	var travel: Vector2 = _router.travel_px()
	var points := PackedVector2Array()
	var colours := PackedColorArray()
	var to_local: Transform2D = get_global_transform().affine_inverse()
	var steer: PackedVector2Array = _steer_drawn
	var drive: PackedVector2Array = _drive_drawn
	var steer_at: Vector2 = to_local * steer[0] if steer.size() == 2 else _centre(_steer_home)
	var drive_at: Vector2 = to_local * drive[0] if drive.size() == 2 else _centre(_drive_home)
	match style.touch_look:
		LOOK_WHEEL_PEDALS, LOOK_WHEEL_LEVER:
			_wheel(points, colours, steer_at, travel.x, _values_drawn.x, steer.size() == 2)
			var push: float = _values_drawn.y
			if style.touch_look == LOOK_WHEEL_PEDALS:
				_pedals(points, colours, drive_at, travel.y, push, drive.size() == 2)
			else:
				_lever(points, colours, drive_at, travel.y, push, drive.size() == 2)
		_:
			_stick(points, colours, Vector2.RIGHT, travel.x, steer, steer_at, to_local)
			_stick(points, colours, Vector2.UP, travel.y, drive, drive_at, to_local)
	if points.is_empty():
		return
	_mesh = CanvasMesh.of(points, colours)
	draw_mesh(_mesh, null)


func _centre(home: Control) -> Vector2:
	return home.position + home.size * 0.5


## One stick along `axis`: a track `travel` each way, a ring where the thumb
## landed, a knob where it is, and the stretch between them filled. With no
## thumb down, the faint hint with its two chevrons. `home` is where the thumb
## landed, or the hint's place while it is up.
func _stick(
	points: PackedVector2Array,
	colours: PackedColorArray,
	axis: Vector2,
	travel: float,
	touch: PackedVector2Array,
	home: Vector2,
	to_local: Transform2D
) -> void:
	var held: bool = touch.size() == 2
	var ink: Color = style.touch_live if held else style.touch_hint
	var origin: Vector2 = home
	var width: float = style.touch_px
	var radius: float = width * 2.5
	var track := Color(ink, ink.a * TRACK_SHARE)
	_bar(points, colours, origin - axis * travel, origin + axis * travel, width, track)
	_ring(points, colours, origin, radius, width * 0.5, ink)
	if not held:
		for side: float in [-1.0, 1.0]:
			_chevron(points, colours, origin + axis * side * travel, axis * side, radius, ink)
		return
	var reach: float = clampf((to_local * touch[1] - origin).dot(axis), -travel, travel)
	var knob: Vector2 = origin + axis * reach
	_bar(points, colours, origin, knob, width, ink)
	_disc(points, colours, knob, radius, ink)


## A steering wheel round the thumb: rim, three spokes and the stripe at the
## top that shows how far it has turned. At rest, the hint's chevrons beside it.
func _wheel(
	points: PackedVector2Array,
	colours: PackedColorArray,
	at: Vector2,
	travel: float,
	turn: float,
	held: bool
) -> void:
	var ink: Color = style.touch_live if held else style.touch_hint
	var width: float = style.touch_px
	var radius: float = travel * 0.55
	var spin: float = deg_to_rad(WHEEL_LOCK_DEG) * turn
	_ring(points, colours, at, radius, width, ink)
	if not held:
		for side: float in [-1.0, 1.0]:
			var tip: Vector2 = at + Vector2(side * (radius + width * 4.0), 0.0)
			_chevron(points, colours, tip, Vector2(side, 0.0), width * 2.0, ink)
	if wheel == null:
		return
	# The car's own wheel (`CarSpec.steering_wheel`): its horn pad, its spokes.
	var hub: float = radius * wheel.hub_share
	_disc(points, colours, at, hub, Color(ink, ink.a * TRACK_SHARE))
	_ring(points, colours, at, hub, width * 0.5, ink)
	for spoke_deg: float in wheel.spokes_deg:
		var out := Vector2.from_angle(deg_to_rad(spoke_deg) + spin)
		_bar(points, colours, at + out * hub, at + out * radius, width * wheel.spoke_share, ink)
	if wheel.top_stripe:
		# A racing wheel's stripe at twelve o'clock.
		var top: float = -PI * 0.5 + spin
		var a: Vector2 = at + Vector2.from_angle(top - 0.14) * (radius + width * 0.5)
		var b: Vector2 = at + Vector2.from_angle(top + 0.14) * (radius + width * 0.5)
		_bar(points, colours, a, b, width * 2.2, Color(ink, minf(ink.a * 1.6, 1.0)))


## Two pedals either side of the thumb: the accelerator above it, tall and
## narrow, the brake below it, wide — slide up onto the one, down onto the
## other. The pressed one fills as far as it is pushed.
func _pedals(
	points: PackedVector2Array,
	colours: PackedColorArray,
	at: Vector2,
	travel: float,
	push: float,
	held: bool
) -> void:
	var ink: Color = style.touch_live if held else style.touch_hint
	var width: float = style.touch_px
	var gap: float = width * 2.0
	var gas := Rect2(
		at + Vector2(-travel * 0.22, -gap - travel * 0.85), Vector2(travel * 0.44, travel * 0.85)
	)
	var brake := Rect2(at + Vector2(-travel * 0.36, gap), Vector2(travel * 0.72, travel * 0.5))
	_pedal(points, colours, gas, maxf(push, 0.0), 4, ink)
	_pedal(points, colours, brake, maxf(-push, 0.0), 3, ink)
	_ring(points, colours, at, width * 1.6, width * 0.5, ink)


## One pedal: filled as far as it is pressed, outlined, and ridged — the
## rubber's ridges are what say "pedal" and not "button".
func _pedal(
	points: PackedVector2Array,
	colours: PackedColorArray,
	box: Rect2,
	amount: float,
	ridges: int,
	ink: Color
) -> void:
	var width: float = style.touch_px
	_fill(points, colours, box, Color(ink, ink.a * lerpf(TRACK_SHARE * 0.5, 1.0, amount)))
	_outline(points, colours, box, width * 0.6, ink)
	var ridge := Color(0.0, 0.0, 0.0, ink.a * 0.5)
	var inset: float = box.size.x * 0.2
	for i: int in ridges:
		var y: float = box.position.y + box.size.y * (i + 1) / (ridges + 1)
		var left := Vector2(box.position.x + inset, y)
		_bar(points, colours, left, Vector2(box.end.x - inset, y), width * 0.4, ridge)


## A throttle lever: a slot the length of the travel each way, the handle where
## the thumb is, forward to go and back to brake.
func _lever(
	points: PackedVector2Array,
	colours: PackedColorArray,
	at: Vector2,
	travel: float,
	push: float,
	held: bool
) -> void:
	var ink: Color = style.touch_live if held else style.touch_hint
	var width: float = style.touch_px
	var slot := Rect2(at + Vector2(-width, -travel), Vector2(width * 2.0, travel * 2.0))
	_fill(points, colours, slot, Color(0.0, 0.0, 0.0, ink.a * 0.5))
	_outline(points, colours, slot, width * 0.5, ink)
	var handle: Vector2 = at + Vector2(0.0, -push * travel)
	if held:
		_bar(points, colours, at, handle, width * 2.0, Color(ink, ink.a * 0.6))
	_bar(
		points,
		colours,
		handle - Vector2(width * 3.5, 0.0),
		handle + Vector2(width * 3.5, 0.0),
		width * 2.4,
		ink
	)
	_disc(points, colours, handle, width * 1.6, ink)
	for side: float in [-1.0, 1.0]:
		var tip: Vector2 = at + Vector2(0.0, side * (travel + width * 3.0))
		_chevron(points, colours, tip, Vector2(0.0, side), width * 1.8, ink)


static func _fill(
	points: PackedVector2Array, colours: PackedColorArray, box: Rect2, ink: Color
) -> void:
	var y: float = box.position.y + box.size.y * 0.5
	_bar(points, colours, Vector2(box.position.x, y), Vector2(box.end.x, y), box.size.y, ink)


static func _outline(
	points: PackedVector2Array, colours: PackedColorArray, box: Rect2, width: float, ink: Color
) -> void:
	var corners: Array[Vector2] = [
		box.position,
		Vector2(box.end.x, box.position.y),
		box.end,
		Vector2(box.position.x, box.end.y)
	]
	for i: int in 4:
		var from: Vector2 = corners[i]
		var to: Vector2 = corners[(i + 1) % 4]
		var along: Vector2 = (to - from).normalized() * width * 0.5
		_bar(points, colours, from - along, to + along, width, ink)


static func _bar(
	points: PackedVector2Array,
	colours: PackedColorArray,
	from: Vector2,
	to: Vector2,
	width: float,
	ink: Color
) -> void:
	var along: Vector2 = to - from
	if along.length() < 0.5:
		return
	var side: Vector2 = along.orthogonal().normalized() * width * 0.5
	points.append_array([from + side, to + side, to - side, from + side, to - side, from - side])
	for _i: int in 6:
		colours.append(ink)


static func _disc(
	points: PackedVector2Array, colours: PackedColorArray, at: Vector2, radius: float, ink: Color
) -> void:
	for i: int in ROUND:
		var a: float = TAU * i / ROUND
		var b: float = TAU * (i + 1) / ROUND
		points.append_array(
			[at, at + Vector2.from_angle(a) * radius, at + Vector2.from_angle(b) * radius]
		)
		colours.append_array([ink, ink, ink])


static func _ring(
	points: PackedVector2Array,
	colours: PackedColorArray,
	at: Vector2,
	radius: float,
	width: float,
	ink: Color
) -> void:
	for i: int in ROUND:
		var a := Vector2.from_angle(TAU * i / ROUND)
		var b := Vector2.from_angle(TAU * (i + 1) / ROUND)
		var a_out: Vector2 = at + a * (radius + width)
		var a_in: Vector2 = at + a * radius
		var b_out: Vector2 = at + b * (radius + width)
		var b_in: Vector2 = at + b * radius
		points.append_array([a_in, a_out, b_out, a_in, b_out, b_in])
		for _j: int in 6:
			colours.append(ink)


## A filled arrowhead at `tip`, pointing along `towards`.
static func _chevron(
	points: PackedVector2Array,
	colours: PackedColorArray,
	tip: Vector2,
	towards: Vector2,
	size_px: float,
	ink: Color
) -> void:
	var back: Vector2 = tip - towards * size_px
	var side: Vector2 = towards.orthogonal() * size_px * 0.8
	points.append_array([tip + towards * size_px * 0.6, back + side, back - side])
	colours.append_array([ink, ink, ink])
