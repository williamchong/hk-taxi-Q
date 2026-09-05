## Checks the generated lamp posts against the data contract, headless.
##
## `P3-26` delivers LandsD's published lamp estate as static unlit geometry, and
## the facts that decision rests on are engine-side: whether the importer
## dispatched the shader on the material name, whether it built a collider it
## must *not* have, and whether every triangle still faces the way it was wound
## to. Run:
##
##     godot --headless --path game --script res://tools/verify_lamps.gd
##
## Exits non-zero if the lamps are present and fail any check.
##
## ⚠️ **Absence is a pass.** A city whose estate publishes no utility point layer
## draws none. What stops that becoming a silent skip is `verify_city.gd`, whose
## `_check_documents` asserts a *named* lamps asset exists and matches this
## file's constant — so a manifest naming `lamps.glb` with the file gone fails
## there.
##
## 🔴 **What this tool CANNOT see is the arm direction**, and that is the whole of
## `Q62` at a fifth layer. Which way a lantern reaches is derived from the kerb
## side because nothing published says, so there is no truth here to check it
## against and a whole city reaching the wrong way renders perfectly. The
## evidence for it is an A/B render at one fixed camera, and the ETL-side
## instrument is `lamps.json`'s `lantern_overhang_m` — deliberately **not** an
## `arms_against_kerb` counter, which would read 0 by construction (`Q72`).
extends SceneTree

const GeneratedLayer = preload("res://scripts/city/generated_layer.gd")
const GeneratedPlacements = preload("res://scripts/city/generated_placements.gd")
const MeshContract = preload("res://scripts/city/mesh_contract.gd")

## One surface per library mesh, so each is one draw call — `verify_signs.gd`'s
## rule, and before `P5-3` the merged mesh's: one primitive for the region.
##
## ⚠️ **Unlike the railings this layer does NOT split by class**, and it must not
## start: `railings.glb` ships three primitives because `Q61` found three
## distinct objects in one source layer, and this source publishes one code with
## one meaning. A second surface on a kind's mesh would be a second claim.
const SURFACES_PER_MESH: int = 1

## The material the lamps must end up with, mirroring `SHADERS` in
## `tools/generated_scene_import.gd` and `LAMPS_MATERIAL` in
## `etl/pipeline/lamps.py`.
##
## 🔴 **Checked through its `resource_path`, and that is the point rather than an
## implementation detail.** This layer *shares* `signs.gdshader` with the signs
## and the signals — a layer is a parameterisation, not a shader (`Q61`, `Q71`) —
## so `check_shader_source` would happily pass a lamp column handed `signs.tres`,
## which is a galvanised post lit as retroreflective sheeting. The path is the
## only thing that tells the three apart. Do not swap this for the shader check.
const LAMPS_MATERIAL: String = "res://tuning/lamps.tres"

## The share of the mesh that must stand upright.
##
## 🔴 **0.35 because the shipped mesh reads 0.50, and the first version of this
## line said 0.70 — a number nobody had measured.** It failed on its own asset at
## 18,484 of 35,880, which is the check working and the *comment* being the
## defect. Recorded rather than quietly corrected, because an invented figure in
## a threshold's justification is exactly what `Q34′` and `Q37` are about: a bar
## whose stated derivation is fiction cannot be re-derived when the geometry
## moves.
##
## The real number is enumerable, per lamp, at 40 triangles:
##
##     20  column sides (12) + the lantern's four vertical faces (8)   |n.y| 0.00
##      8  the bracket arm's flanks                                    |n.y| 0.48
##      4  the bracket arm's top and bottom                            |n.y| 0.95
##      8  column cap (4) + lantern top and bottom (4)                 |n.y| 1.00
##
## So 20 of 40 stand upright **by construction** — measured over the whole region
## and over every arm heading, the ETL mesh is exactly **17,940 of 35,880,
## 50.000%**, with four distinct `|n.y|` values and not one degenerate dropped
## (35,880 = 897 x 40 exactly).
##
## 🔴 **The IMPORTED mesh used to disagree, and chasing that is what found
## `Q82`'s compression finding.** It read **18,484 (51.52%)** while the ETL built
## 17,940, because Godot quantised positions over the mesh's own AABB — 1,646 m
## wide here, a **0.025 m** step, against a bracket arm of 0.06 m radius. The
## column, caps and lantern survived exactly (axis-aligned); the arm's 7,176
## flanks smeared off 0.477 across 0.10-0.70. ✅ **`meshes/force_disable_compression`
## is now `true` project-wide**, so this tool and the stage agree exactly, and
## `check.sh`'s `settings` step pins the value — it is in `project.godot` rather
## than beside the asset because `game/assets/generated/` is gitignored.
##
## A laid-flat mesh reads ~0, so 0.35 separates the two with fifteen points of
## headroom, and that headroom no longer moves with the AABB.
##
## ⚠️ **This check only catches a TOTAL lay-flat**, which is what it is for. It is
## not a quality bar and must not be retuned toward the measured 0.50 to make it
## "tighter" — that would fail an ordinary authored change to the arm.
const MIN_UPRIGHT_SHARE: float = 0.35


func _init() -> void:
	if not GeneratedLayer.is_present(GeneratedLayer.LAMPS):
		print("  skip  no %s shipped for this region" % GeneratedLayer.noun(GeneratedLayer.LAMPS))
		quit(0)
		return

	var packed: PackedScene = GeneratedLayer.load_layer(GeneratedLayer.LAMPS)
	if packed == null:
		# Present but unloadable, which is not the same as absent — the hint
		# about rebuilding would be the wrong advice here.
		printerr(
			(
				"  FAIL  %s exists but did not load as a scene"
				% GeneratedLayer.path(GeneratedLayer.LAMPS)
			)
		)
		quit(1)
		return

	var scene_root: Node3D = packed.instantiate()
	var problems: PackedStringArray = _check(scene_root)
	# Instantiated outside the tree, so nothing else will free it — and a
	# headless run that leaks buries its own result under exit warnings.
	scene_root.free()
	for problem: String in problems:
		printerr("  FAIL  ", problem)
	if problems.is_empty():
		print("  ok    ", GeneratedLayer.path(GeneratedLayer.LAMPS))
	quit(1 if not problems.is_empty() else 0)


## 🔴 **Since `P5-3` the asset is a LIBRARY — one mesh per drawn kind, its arm
## north — and the city is `lamps_placements.json`.** Every mesh check below
## runs per library mesh, which is every column in the city checked once; the
## upright bar in particular is now asked of the one column rather than of
## 892 copies of it, and reads the same share. The join is graded both ways
## by `GeneratedPlacements.check_join`, shared with `verify_signs.gd`.
func _check(scene_root: Node3D) -> PackedStringArray:
	var problems: PackedStringArray = []
	var library: Dictionary[String, Mesh] = MeshContract.library_meshes(
		scene_root, SURFACES_PER_MESH, problems
	)
	if library.is_empty():
		return problems
	for mesh_name: String in library:
		var mesh := library[mesh_name] as ArrayMesh
		for surface: int in mesh.get_surface_count():
			var where: String = "'%s' surface %d" % [mesh_name, surface]
			# `true`: this mesh ships `COLOR_0` and the shader reads it. The
			# no-texture guarantee runs on the default budget of 0, which is what
			# keeps this layer imageless — a lamp post carries no lettering, and the
			# moment one did it would owe `Q63`'s declaration.
			problems.append_array(MeshContract.check_surface(mesh, surface, where, true))
			problems.append_array(
				MeshContract.check_shader_material(mesh, surface, where, LAMPS_MATERIAL)
			)
			problems.append_array(
				MeshContract.check_stands_upright(
					mesh,
					surface,
					where,
					"lamps",
					"Lamps are columns on footways",
					MIN_UPRIGHT_SHARE
				)
			)
	problems.append_array(
		GeneratedPlacements.check_join(
			GeneratedLayer.placements_path(GeneratedLayer.LAMPS),
			GeneratedLayer.noun(GeneratedLayer.LAMPS),
			library
		)
	)
	problems.append_array(_check_has_no_collision(scene_root))
	return problems


## Street furniture must **not** collide, for the reason the signs must not.
##
## ⚠️ **The reasoning runs the other way from the arrows', and is weaker** —
## `verify_signs.gd`'s paragraph, and it applies here with one extra edge. A lamp
## column is a real obstacle a real car really would hit, so its absence is a
## **budget** decision rather than a correctness one: 892 columns is 892
## collision bodies, and `P2-6` has not measured a frame on the device floor. The
## extra edge is *how many*: this is the most numerous solid object in the
## bundle, ahead of the signs' 497 posts. `GAME_DESIGN.md` puts breakaway posts
## in `B3`, and the whole guard against one arriving early is the absence of a
## `-col` suffix on the kind name each library mesh is built under in `lamps.py`.
func _check_has_no_collision(scene_root: Node3D) -> PackedStringArray:
	return MeshContract.check_no_collision(
		scene_root, "the lamps", "library[kind].build(kind) in etl/pipeline/lamps.py"
	)
