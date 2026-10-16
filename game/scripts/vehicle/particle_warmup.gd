class_name ParticleWarmup
extends RefCounted
## Compiles a slide's particles at load, not on the first slide. The web build
## runs the Compatibility renderer, which compiles a material the first time
## it is DRAWN, on the main thread: the smoke and the sparks first drew on the
## first drift, and the game stalled 90–195 ms a material there and never
## again (measured under `--rendering-method gl_compatibility`).
##
## The emitters draw for `FRAMES` frames with time stopped — `speed_scale` 0,
## so nothing is emitted and every particle stays at zero scale, which puts no
## pixel on screen — and are never culled meanwhile, wherever the camera is
## looking at boot. Then they are put back: speed restored, not emitting.

## Process frames to hold the emitters up. A frame's draw follows its
## `process_frame`, so two awaits span at least one draw.
const FRAMES: int = 2
## A margin past any frustum, so the warm-up draws whatever the camera sees.
const UNCULLED_M: float = 1.0e5


## Draws `emitters` for `FRAMES` frames, then leaves each one stopped. A
## coroutine: `await` it, and drive no emitter's `emitting` until it returns.
static func warm(emitters: Array[CPUParticles3D]) -> void:
	if emitters.is_empty():
		return
	var tree: SceneTree = emitters[0].get_tree()
	var speeds: PackedFloat32Array = PackedFloat32Array()
	var margins: PackedFloat32Array = PackedFloat32Array()
	for emitter: CPUParticles3D in emitters:
		speeds.append(emitter.speed_scale)
		margins.append(emitter.extra_cull_margin)
		emitter.speed_scale = 0.0
		emitter.extra_cull_margin = UNCULLED_M
		emitter.emitting = true
	for _frame: int in FRAMES:
		await tree.process_frame
	for k: int in emitters.size():
		var emitter: CPUParticles3D = emitters[k]
		if not is_instance_valid(emitter):
			continue
		emitter.emitting = false
		emitter.speed_scale = speeds[k]
		emitter.extra_cull_margin = margins[k]
