class_name Analytics
extends RefCounted
## Anonymous gameplay events to PostHog (`Q256`): the game's one runtime network
## call, and the only script that talks to the `PostHog` autoload. Every event
## goes through `track`, so what leaves the device is the list in
## `docs/ARCHITECTURE.md` "Analytics" and nothing else.
##
## ⚠️ **Nothing is sent unless `Main` says this run is a player's** (`start`,
## from `Main._records_run`): no menu, a menu page or sample flag, and every
## scripted run never set the client up. An editor build — `drive.sh`, the
## verify tools, the editor's own play — is off as well unless `--analytics=on`
## asks, so a test drive cannot pollute the numbers; `--analytics=off` beats
## everything.
##
## The player's switch is `Settings.analytics_on` (PRIVACY on the boot menu),
## and it is the one source of truth: the SDK keeps its own consent on disk,
## and `_apply` pushes this one onto it.
##
## Statics and a node looked up by name, not an autoload: a `--script` tool
## (`verify_menu`) compiles `StartMenu` with no autoload names in scope, so a
## script naming one fails to compile there.

const CONFIG_PATH: String = "res://tuning/analytics.tres"
const ARG: String = "--analytics="
const CLIENT: NodePath = ^"/root/PostHog"

## Whether `Main` has called this run a player's.
static var _eligible: bool = false
## Whether `PostHog.setup` has taken the config this run.
static var _started: bool = false


## Whether this build and these flags may send at all.
static func allowed() -> bool:
	if Cmdline.off(ARG):
		return false
	if Cmdline.value(ARG).to_lower() == "on":
		return true
	return not OS.has_feature("editor")


## `Main`, once, on a player's run: set the client up where the player has the
## switch on. Off, nothing starts until it is turned on.
static func start() -> void:
	_eligible = allowed()
	if _eligible and Settings.analytics_on():
		_apply(true)


## The PRIVACY switch: saved first, then pushed onto the client. Off clears
## what is queued and not yet sent; what the server already took stays there.
static func set_enabled(on: bool) -> void:
	Settings.set_analytics_on(on)
	if _eligible:
		_apply(on)


## One event, if the client is running. A player's OFF needs no check here:
## `opt_out` makes the SDK drop every capture until `opt_in`. `properties`
## holds numbers, enums and flags — never a name, a place, a position or free
## text.
static func track(event: String, properties: Dictionary = {}) -> void:
	var client: Node = _client() if _started else null
	if client != null:
		client.call(&"capture", event, properties)


static func _apply(on: bool) -> void:
	var client: Node = _client()
	if not on:
		if _started and client != null:
			client.call(&"opt_out")
		return
	if client == null:
		push_warning("analytics: no %s autoload; nothing is sent" % CLIENT)
		return
	if not _started:
		var config: Resource = load(CONFIG_PATH)
		if config == null:
			push_warning("analytics: %s did not load; nothing is sent" % CONFIG_PATH)
			return
		_started = bool(client.call(&"setup", config))
		if not _started:
			return
	if bool(client.get(&"is_opted_out")):
		client.call(&"opt_in")


static func _client() -> Node:
	var tree: SceneTree = Engine.get_main_loop() as SceneTree
	return tree.root.get_node_or_null(CLIENT) if tree != null else null
