# Architecture

## Stack

| Layer | Choice | Notes |
|---|---|---|
| Engine | **Godot 4.7** | MIT, no royalties or seat fees |
| Renderer | **Mobile** (primary), Compatibility for the web demo | Forward+ only if a desktop tier ever justifies it |
| Physics | **Jolt** — Godot's default since 4.4 | Trimesh collision, and `VehicleBody3D` for the car since `Q50` reversed `P0-5a` (2026-08-18) |
| Engine language | **GDScript**, statically typed | See below |
| ETL | **Python 3.11+** — numpy, pyproj, pyyaml, pyogrio | Build-time only |
| Targets | iOS, Android, Windows/macOS/Linux (Steam) | Web export reserved for the free demo slice |

### ⚠️ The importer can reinstate `VehicleWheel3D` behind your back

Godot's glTF importer converts nodes by **name suffix**. A node whose name ends in `_wheel` is
imported as a `VehicleWheel3D`, not as the `MeshInstance3D` the file describes — and the same
applies to `_col`, `_convcol`, `_navmesh`, `_occ`, `_rigid` and `_vehicle`.

`P3-11` shipped its tyre mesh as `taxi_wheel.glb`, so every wheel arrived wrapped in a
`VehicleWheel3D` with no `VehicleBody3D` above it. The wheels stopped drawing. **Nothing reported an
error**: the import succeeded, `tools/check.sh` passed, the driver printed `DRIVER OK`, and the only
symptom was a car that rendered without wheels. The mesh is now `taxi_tyre.glb`.

Worth its own heading because of *what* it reinstated. `P0-5a` had measured `VehicleWheel3D` and
rejected it — its friction is isotropic, so it cannot express a drift — and a filename put it back
into the scene tree. **A locked decision can be undone by a naming convention.** Check the
instantiated tree, not the source scene, when geometry goes missing.

⚠️ **`Q50` made the car a real `VehicleBody3D`, and that makes this trap worse rather than moot.**
The tyre mesh is now a child of an actual `VehicleWheel3D`, so a rename back to `taxi_wheel.glb`
would nest a wheel inside a wheel — which the engine accepts silently, because the outer one is
legitimately parented to the body. The mesh is `taxi_tyre.glb` and must stay so.

### Why GDScript, not C#

C# platform support in Godot 4.7 (re-verified against the official docs 2026-07-29): desktop fully
supported, **Android and iOS experimental**, **web not supported at all**. Mobile is a primary target
and the web demo is the planned marketing funnel, so C# compromises both. GDScript also hot-reloads,
which directly speeds up the vehicle-feel tuning loop that carries most of this project's risk.

**Performance escape hatch:** if a system profiles too slow, use **GDExtension** (C++, or Rust via
godot-rust). It preserves every export target, including web. Do not reach for C#.

> **Note for JS/TS developers:** GDScript is Python-like with optional static typing. Always annotate
> (`var speed: float = 0.0`) — it is faster *and* catches errors the untyped form won't.
> `signal`/`connect` is the event-emitter equivalent. `.tres` resource files are the idiomatic home
> for tuning data, roughly a typed JSON config.

---

## Project settings

✅ **`game/project.godot` is committed in the form Godot's own writer produces, so an editor save is
a no-op on it (`Q119`).** The writer — Project Settings in the editor and `ProjectSettings.save()`
alike — regenerates the file from memory, drops every comment, and **omits every key whose value
equals the engine's registered default**. That last rule is what three decision entries read as "the
editor dropped the settings": `native_method_override`, `get_node_default_without_onready` and
`onready_with_export` default to *error* already, and `rendering/renderer/rendering_method.web` is
registered by the engine with `gl_compatibility` as its default, so all four vanish from the file on
every save **while staying in force**. Nothing failed for three weeks because nothing was lost.
`run/max_fps.mobile` has no registered default, which is why it always survived. This table is the
durable record of *why*; the values are asserted by `tools/verify_settings.gd`, which reads each one
back through `ProjectSettings` — the value in force, not the line in the file — and is `check.sh`'s
`settings` step.

⚠️ **What that `.web` override buys is narrower than this file used to claim.** Between `78c077e`
(2026-08-01) and 2026-08-25 the line was absent and the claim was that its absence *silently breaks
web export because WebGL2 cannot run the mobile renderer*. **Measured on the shipped web build, it
does not**: the export reports `OpenGL ES 3.0 (WebGL 2.0) - Compatibility` in the browser console,
because Godot 4.7 forces Compatibility on web regardless — and, per `Q119`, because the override was
the engine default all along. Keep it stated: the project should say the renderer it wants rather
than inherit one, and `verify_settings.gd` asserts it whether or not the file carries the line.

✅ **Headless is safe, measured twice.** A full `tools/check.sh` — `--import` and the `--check-only`
sweep included — leaves the file byte-identical, and a headless editor open-and-quit writes nothing.
Only a GUI save writes it, and since `Q119` that write is a no-op.

🔴 **`.tres` and `.tscn` are rewritten by the same writer, and their rationale therefore lives in a
sidecar `.md` beside each file, never in the file (`Q119`, superseding `Q99`).** On 2026-09-07 the
1,334 comment lines then inside 26 resources moved to `<name>.md` next to each — `handling.tres`
reads `handling.md`, `city_drive.tscn` reads `city_drive.md` — each heading the line the block sat
above. Every resource was then re-saved through `ResourceSaver` and compared property by property
against its previous self: **0 differing stored properties across all 33 files**, the same
measurement `Q99` made on one. What the writer changes is form only — `load_steps` and `uid=`
attributes, float spelling (`4.0` → `4`), key order, and any value equal to its script's declared
default (`beams.tres` is empty for that reason: all three values equal `beam_profile.gd`'s
defaults, which that script names as its fallback). `check.sh`'s `tuning` step now requires the
sidecar, refuses any `;` line in a resource, and fails an orphan sidecar or a stale exemption.

| Setting | Value | Why |
|---|---|---|
| `rendering/renderer/rendering_method` | `mobile` | Locked decision. Set as the **base** value, not only as a `.mobile` override, so the editor and desktop builds preview the renderer the phone will run |
| `rendering/renderer/rendering_method.web` | `gl_compatibility` | Web export is WebGL2-only |
| `rendering/textures/vram_compression/import_etc2_astc` | `true` | Godot refuses to export **any** arm64 target without it — iOS, Android and Apple Silicon macOS alike |
| `rendering/anti_aliasing/quality/msaa_3d` | `2` (4x) | 🔴 **The one setting the performance budget below cannot see.** Draw calls and primitives are *byte-identical* at 0 / 2x / 4x — 63 and 716,912 on `city_drive` — because MSAA changes nothing about what is submitted; it costs fill rate and framebuffer bandwidth, which no row of that budget tracks, so "it passes the budget" means nothing here. ⚠️ **Turned on for thin geometry, not for silhouettes**: with no AA a stripe narrower than a pixel is lit only where a pixel centre falls inside it, so it breaks into dashes and then vanishes entirely. Measured on the chase rig (70&deg; vertical FOV, 1080 px, eye 2.4 m over the paint): the 0.1 m box junction hatch is **one pixel tall at 13.6 m** and its 0.3 m border at **23.6 m**, which is exactly where the hatch dies in a driven frame. `signs.glb`'s poles are 0.032 m and go the same way. ⚠️ **Total coverage is conserved and only continuity is lost** — the same world area renders 0.0580 vs 0.0574 yellow at two resolutions — so this cannot be fixed by brightening the paint or lifting it further; the renderer is already drawing the right *amount*. 🔴 **4x (`2`) and never 8x (`3`): WebGL2 reports `MAX_SAMPLES` 4**, so 8x is clamped on the web cut and would ship a different frame per platform for nothing. Verified in Chrome against a real export, both ways: 6,819 -> 9,170 distinct colours, 38,096 -> 45,950 partially-covered edge pixels. ⚠️ **Verified on BOTH renderers**, which is not one test — web runs `gl_compatibility` and native runs `mobile`; under Compatibility, 4.6% of the frame changes and partially-covered paint pixels go 2,463 -> 5,657. ⚠️ **No `.mobile` override, deliberately**: that tier is unbuilt (`P0-3b`) and this is a bandwidth cost nobody has a floor handset to measure, so it is a desktop-and-web decision that the mobile tier must re-take. Desktop cost is **unmeasured**: an M4 Pro holds the 120 Hz vsync cap at 0, 2x and 4x, which is a floor and not a number. `check.sh` pins the value (mutation-checked). `Q91` |
| `physics/3d/physics_engine` | `Jolt Physics` | Locked decision. The default since 4.4, but stated so the project does not silently follow a changed engine default |
| `application/run/max_fps.mobile` | `60` | Rendering uncapped on a 90/120 Hz panel buys nothing above the 60fps target and throttles the device. Desktop stays uncapped |
| `display/window/stretch/mode` | `canvas_items` | Resolution-independent UI; desktop is a target alongside phones |
| `[importer_defaults] scene.import_script/path` | `res://tools/generated_scene_import.gd` | Godot 4.7's glTF importer reads `COLOR_0` but leaves `vertex_color_use_as_albedo` **off**, so every generated tile imports as a white block. Nothing in the glTF can express it. Set as an importer *default* rather than per file: generated assets are gitignored, so their `.import` files do not survive a fresh clone |
| `[importer_defaults] scene.meshes/force_disable_compression` | `true` | 🔴 **Godot quantises imported vertex positions over the mesh's OWN AABB**, so the step scales with how wide the layer is, not with how big its objects are. Measured on `lamps.glb`: a **1,646 m** AABB gives a **0.025 m** step, against a bracket arm of **0.06 m** radius — the arm's 7,176 flank triangles leave a clean `\|n.y\|` of 0.477 and smear across 0.10-0.70, while the axis-aligned column and lantern survive exactly. ⚠️ **`signs.glb` is the worse case**: its poles are **0.032 m**, thinner than the step. Off costs **+958,720 B (+2.002%)** of PCK — 47,897,332 → 48,856,052, two exports one setting apart — and every generated mesh then imports exactly as the ETL built it, which is what lets a verify tool's count agree with the stage's own: `verify_lamps` went from 18,484 upright to the ETL's exact 17,940. ⚠️ **Project-wide rather than per asset, and not by preference**: the comment directly above this block already records why, since `game/assets/generated/` is gitignored and a `.import` there does not survive a fresh clone. Lamps alone would have been +69,264 B, and is not available durably. 🔴 **`[importer_defaults]` seeds only a NEWLY CREATED `.import`, so setting it does not migrate assets that already have one** — 133 of 141 sidecars kept `false` after the commit, including `hkcec.glb`, the bundle's largest mesh, which went on importing compressed. That is why this row first recorded **+446,128 B**: `hkcec.glb` was identical on both sides and fell out of the delta. Delete the sidecars and re-import after changing this key, and note `check.sh` pins the `project.godot` value and **cannot see a stale sidecar**. ⚠️ Three *authored* imports still carry `false` — the taxi body, the tyre and `central_plaza.glb` — left deliberately: their AABBs are metres, so the quantum is sub-millimetre, and re-importing the committed taxi would move `verify_vehicle`'s figures for nothing. ⚠️ **The 132 tiles and `roads.glb` never compress in either state** (40 B/vertex both ways), so a per-asset alternative would buy nothing on the bulk of the bundle. ⚠️ **Two exports of this setting differed by 80 B** — `project.godot`'s own comment churn getting packed as `project.binary` — so quote a delta from a baseline measured the same way. `check.sh`'s `settings` step pins the value (mutation-checked). `Q82` |

**Deliberately not set**, both measured rather than reasoned:

- `directional_shadow/soft_shadow_filter_quality` — Godot already ships a `.mobile` override of `0`,
  and feature overrides beat an explicitly-set base value, so setting the base only degrades desktop.
- `directional_shadow/size` — the engine default is already 4096 (`.mobile` 2048). The next step up,
  8192², is **~134 MB** of shadow map against a 512 MB desktop texture budget; measured, raising the
  atlas moved texture memory by exactly 134,217,728 B.

**Cascade count costs no VRAM.** Godot allocates one `size × size` depth texture whatever the split
mode and subdivides the rect per cascade — four 2048² quadrants and one 4096² measured identical at
79,592,192 B. Cascades buy geometry submission, not memory. There are no `lights_and_shadows/*` keys
in `project.godot` at all: cascade count and distance are node properties on the one shared sun.

**Autoloads:** three, and each is held to the test Godot's own guidance sets — a wide-scope system
that owns its own data and that other nodes register with rather than reach into (`Q119`):

- `DebugHud` — every dev readout; overlays hand it a label and ask what to show. The frame counter
  is a `Label` it builds, not a fourth autoload: `FpsCounter` was the one autoload whose `_ready`
  reached into another, which made the registration order in `project.godot` load-bearing.
- `InputRouter` — the one reader of raw input, and the action set every gameplay script samples.
  Reached by `NodePath` (`^"/root/InputRouter"` by default on `VehicleController` and
  `ChaseCamera`), never by its global name, so no gameplay script carries a compile-time dependency
  on an autoload being registered.
- `BeamBudget` — the renderer-global spot-light cap, dormant until a rig registers. It alters other
  nodes' state, which the guidance says belongs to a regular node; it stays an autoload because its
  "no arbiter" branch lights every beam, and a scene that forgot a regular node would take that
  branch silently — the 8-slot cliff it exists to stop.

All three run for the life of the process, so treat them as hot-path code.

### The debug overlay

`DebugHud` (`scripts/ui/debug_hud.gd`) owns every dev readout: the frame counter, the position block,
the text blocks overlays register with it, and — through `view_changed` — the road graph's chevrons.
**`F3` cycles off → minimal → full**, and `--debug-view=off|minimal|full` sets where a run starts.

| View | Shows | Draw calls |
|---|---|---|
| `off` | nothing. **The default, in every build** | 19 |
| `minimal` | position block and frame counter | 27 |
| `full` | plus registered readouts and 3D debug geometry | 38 |

Measured on `city_drive.tscn` at 2.0 s into the standard driver run — ⚠️ **before the drawn layers
from `P3-14` onward landed**, so the absolute numbers are stale (the HUD paragraph below was measured
on a later build and starts from 44–45); the *deltas* between views are what the table is for, and
`P2-6` re-measures the lot. Against the <150 budget that is affordable, but it is not free: left on,
a fifth of the scene's draw calls go on debug text — and it sits over every screenshot anyone judges
the city from. That second reason, more than the cost, is why the default is off.

`drive.sh` (`.claude/skills/run-hk-taxi-q/drive.sh`) is the exception: it appends
`--debug-view=minimal` unless the caller names a view, on the
grounds that a scripted run is someone debugging and a screenshot that cannot say where it was taken
cannot be acted on.

⚠️ **The player's HUD is separate from all of this and is ON by default**, because it is not dev
chrome — `--debug-view=off` does not touch it. It costs a measured **+5 draw calls** (44–45 → 49–51
on the same run), and unlike the overlay above it is paid in every shipped frame. **A clean frame for
art review therefore needs both `--debug-view=off` and `--hud=off`**, and `P3-9`'s arrow-disabled
drive needs the second one for a reason that is about the test rather than the picture (`P3-24`). The position block reports game metres **and** the source-CRS grid reference
(`CityManifest.to_grid`, the inverse of `crs.py`'s `to_game`), so a frame can be checked against the
ETL's own data rather than only against another frame.

⚠️ The toggle is a **raw key**, not an action: the `[input]` map is the game's, and dev keys stay out
of it (`free_look_camera.gd` set that precedent). So `drive.sh --hold=` cannot press it — scripted
runs use the flag.

---

## Checks

**Godot never signals failure through its exit code.** A script that fails to parse, a warning
promoted to an error, a dependency that will not compile — all of them print and exit `0`.
`tools/check.sh` exists to turn that output into an exit code, and is the only thing in the repo that
does. Running `--import` by hand tells you nothing unless you read the output.

**The rows are in run order, and that is not decoration.** Everything above `--import` must be
engine-free, because a `class_name` resolves only out of the cache the import scan writes — see the
note below the table. A new step goes in at its real position.

| Step | Covers | In CI |
|---|---|---|
| `gdformat --check` | Layout across all of `game/`. ⚠️ **The file count is asserted, not just the status** — pointed at a tree with no `.gd` it prints `0 files would be left unchanged` and exits 0 (`Q119`) | yes |
| `tuning` | That every `game/tuning/*.tres` and `game/scenes/*.tscn` has a non-empty sidecar `.md` unless `UNDOCUMENTED_OK` names it, that no resource carries a `;` comment, and that neither an orphan sidecar nor a stale exemption stands (`Q119`) | yes |
| `--import` | Autoloads and what they reach; also builds `game/.godot/` | yes |
| `settings` | `tools/verify_settings.gd` — the 21 warning promotions, every pinned value and both `[importer_defaults]` keys, read back through `ProjectSettings` rather than grepped, so a canonical editor-written file passes and a lost setting fails (`Q119`). ⚠️ **Runs AFTER `--import`, and that is load-bearing** — the `class_name` note below has why, and why obeying its rule would not have saved this step | yes |
| warnings sweep | `--check-only` per script, grepping for `treated as error`. ⚠️ **An empty file list is FATAL and the swept count is printed** (71 today): `cd` inside a `$( )` exits the subshell, so the step used to report `ok` having swept nothing. 🔴 **And the pattern is `treated as error|Parse Error`, never `$FATAL`** — a semantic parse error in a file no autoload reaches formats clean and matched neither term, so `check.sh` printed `All checks passed` over a script the engine cannot parse; `$FATAL` itself would fire on 4 healthy lines (`Q119`) | yes |
| `verify_beam_budget` | The spot-light cap — needs no built region, so CI can check it | yes |
| `verify_mesh_contract` | That the no-texture contract still refuses what it should — needs no built region, so CI can check it | yes |
| `verify_vehicle` | The taxi's shader binding, lamp channels, imported payload and beam aim — the taxi is committed, so this needs no built region either | yes |
| `verify_input` | The touch scheme, driven by synthetic fingers — needs no built region, which matters more here than anywhere: `P0-3b` has no handset, so this is the only thing that exercises touch at all | yes |
| `verify_hud` | The HUD layout against `hud_layout.tres`'s rects, both directions of the thumb-rest contract (`Q80`) — needs no built region | yes |
| `verify_city`, `verify_tiles`, `verify_road_surface`, `verify_road_graph`, `verify_city_streamer`, `verify_spawn`, `verify_landmarks`, `verify_tramway`, `verify_arrows`, `verify_boxjunctions`, `verify_railings`, `verify_signs`, `verify_roadmarks`, `verify_signals`, `verify_lamps` | The generated-asset contracts — one per asset the manifest names (`verify_signals` runs against the null manifest key the latent layer leaves, `Q77`) | **no** |

The sweep is separate from `--import` because `--import` does not do the job: measured, an untyped
variable planted in `greybox_builder.gd` went unreported, because the import step compiles only
autoloads and what they reach. **The sweep must run with `game/` as the project directory** — run
from elsewhere, `res://` does not resolve, every script silently analyses clean, and the check passes
having checked nothing.

⚠️ **A verify tool that appears to hang is a parse error, not slow work.** When a script fails to
compile, `_init` never runs, so `quit()` is never called and the SceneTree spins forever. Warnings
are promoted to errors here, so something as small as an unused parameter does it. If a step sits
there, read the log for `Parse Error` / `Compile Error` rather than waiting it out — and when
scripting a Godot run, give it a watchdog rather than a long timeout.

🔴 **A verify tool proves an asset is correct. Nothing proves it is in the world.**
`verify_roadmarks.gd` calls `GeneratedLayer.load_layer("roadmarks")` and grades the returned
`PackedScene` in isolation, so it passed while `roadmarks.glb` was in no scene at all — built,
exported, named by `city.json`, dispatched by the importer, and invisible. The player's report was
the only instrument that could see it (`Q73`). **Every layer here has the same blind spot**; the others
are on screen because they happened to get their node. When a layer is added, the node in
`city_drive.tscn` and `city_preview.tscn` is part of the task, and the check that it renders is a
frame someone looked at.

⚠️ **Verify tools `preload` every dependency rather than naming a `class_name` global**, and that is
load-bearing. Global classes resolve through the gitignored
`game/.godot/global_script_class_cache.cfg`, so on a fresh clone a tool referencing one fails to
*parse*, `_init` never runs, `quit(1)` is never reached, and the SceneTree exits **0** — the check
reports success having checked nothing. **Never reference a `class_name` global from a `--script`
tool.**

🔴 **Obeying that is not enough, and `Q119` proved it: the AUTOLOADS are instantiated around every
`--script` run, and they name globals whatever the tool does.** `verify_settings.gd` complies with
the rule above — `extends SceneTree`, no global named anywhere — and still went red on a fresh
clone, because `debug_hud.gd` and `input_router.gd` name `CityManifest`, `VehicleController`,
`TouchProfile` and `HudLayout` between them, and Godot loads both before the script. So the rule
binds a *tool* where what actually binds is the **project**: no Godot process may run above
`==> import` in `tools/check.sh` at all. ⚠️ The failure is also one step milder than the paragraph
above describes — the tool did print `ok`, but the parse errors reached stderr and `run_godot`'s
`FATAL` grep failed the step, which is that grep doing exactly the job it exists for.

⚠️ **Autoloads are registered on the first frame, not before, and a verify tool that loads a scene
should still `await process_frame` first.** Until `Q119` this was a compile-time trap: anything
loaded from `_init` compiled `vehicle_controller.gd` while the `InputRouter` global it named was
unresolvable, GDScript **cached the broken class**, and the scene instanced a `RigidBody3D` with a
*null script* — measured, and a run that printed `SCRIPT ERROR` having graded a car that never
loaded. No gameplay script names an autoload any more — `VehicleController` and `ChaseCamera`
resolve `InputRouter` by `NodePath` in `_ready`, as `vehicle_lamps.gd` always did for `BeamBudget` —
so the scripts compile anywhere; the frame now only decides whether the router and the arbiter are
in the tree when the car goes looking. `tools/verify_vehicle.gd` and `tools/skidpad_ablation.gd`
both keep the `await` for that. A scene instantiated but never added to the tree must also be `free()`d before `quit()`, or
Godot reports a page of `ERROR: ... leaked at exit` lines that read like a failure and are not one.

✅ **Running Godot no longer dirties the two config files** — both are committed in the writer's own
form (`Q119`) — but a headless `--import` still re-saves `game/assets/authored/greybox_wanchai.json`
with tab indentation (`Q115`). Run `git status` afterwards and `git checkout` that one file; never
commit it as a side effect.

⚠️ **The reason to restore is the EXPORT's comparability, not the `.web` line — measured
2026-08-27.** This paragraph used to call it "the line the web export needs"; removing it and
re-exporting produces a **byte-identical** PCK, so it does not reach the web artefact and no bundle
figure ever turned on it. What *does* turn on the restore is every two-export delta in
`PROGRESS.md`'s Bundle-size row: `project.godot` is packed as `project.binary`, so an unrestored
export carries its own stripped comments into the number — **48 B** on the pair that row publishes,
**80 B** on the compression pair above. ✅ **Given a restored `project.godot` the export is
byte-deterministic**: three independent runs at one tree land on 48,856,100 B under one sha256, and
the PCK resolves to **1 B** (+32 characters of `config/name` moves it +32 B). 🔴 **So a delta
measured across an unrestored export is not a feature's cost**, and `--headless --export-release`
was **not** what stripped the tree on 2026-08-27 — it left both files clean across all three runs.
Some other Godot invocation did, so restore-and-verify before an export rather than after one.

**Six grading tools sit beside the suite and are run by hand.** What makes them a set is not the
count: it is that each reads back what *shipped* and shares no code with the pipeline, because a
stage cannot mark its own work — ask the ETL's own sampler about the ETL's own output and it reads
|error| p90 0.02 m, which is the sampler agreeing with itself.

⚠️ **They are not the whole grading estate, and this table is not the list.** Later stages grade
themselves in their own `*.json` counters, and several carry a tool of their own —
`carriageway_margin.py`, `railing_error.py`, `sign_face_survey.py`, `kerbside_source_audit.py`,
`clearance_reconcile.py`. **`CLAUDE.md`'s "Before marking work done" is the list**, kept per change
rather than per tool; restating it here is how `CONTRIBUTING.md` drifted nine graders behind.

| Tool | Answers |
|---|---|
| `tools/deck_error.py` | `Q20` — how far the drawn carriageway sits from the deck beneath it, *vertically*, sampled down centrelines. Gates on \|error\| p90, deepest intrusion, and the share it managed to measure at all |
| `tools/overhang.py` | `Q22`/`Q23` — whether there is a deck beneath it at all, sampled *across the full drawn width*. A ribbon can pass the first and fail the second |
| `tools/ground_clearance.py` | `Q18`/`Q24` — whether the drawn ground stands *in* the at-grade carriageway. Sizes `buildings.ground_sink_m`, and gates the sink separately from the road's own shape |
| `tools/carriageway_occupancy.py` | `Q19` — whether anything **solid stands in the road at bumper height**, buildings and structure told apart by vertex colour. The only one that gates per *edge* rather than region-wide, because `RoadGraph` routes on edges and a share cannot tell a wall across the road from clutter beside it. ⚠️ **Fails today**. Since `Q51` it also grades a number the pipeline publishes for itself — `clearance.py`'s — which read 24 against this tool's 26, reconciled as plan cell size and ratcheted by `tools/clearance_reconcile.py`. ✅ **`--corridor-report`** (2026-08-21) prints the corridor profile per failing edge and asks what stands on the **centreline** at the binding station — `Q19`'s two decisive measurements, which lived in scratch scripts until then. ⚠️ Opt-in, and the default listing is byte-identical with it off; it reports and gates nothing |
| `tools/paint_clearance.py` | `Q92` — whether the **painted layers are above the road they are painted on**, or inside it. The only one whose subject is a marking rather than the surface, and the one that catches what a top-down raster structurally cannot: a mesh complete in *plan* and wrong in *Y*. Splits a burial into a kerb top reached past the drawn ribbon (registration, never gated) and a wrong height on the road it is drawn on (gated) |
| `tools/lane_paint.py` | `Q113`/`Q114` — whether the lane the markings shader paints is wide enough to be a lane. The strip is a quotient of two numbers no stage computes together: `lanes` is `carriageway.py`'s and the drawn half-width is `surface.py`'s, and neither stage can see the other's answer, so no counter either of them publishes can ask this. Reports edges, vertices **and metres** under a bar taken from the city's own `width_bounds.lane_m` (3.00 m), sweeps that bar, and carries the width's own verdict on the count from `carriageway_margin.lane_bracket` |
| `tools/kerbside_error.py` | `Q54` — how much of the kerbside yellow the source supports. Reads the shipped `roads.glb`, clips every carriageway triangle against the shader's own yellow locus, and weighs the chord by the junction fade and `COLOR_0.a`. ⚠️ **It does not grade the join** — the truth side is what `roadgraph.json` publishes, so a restriction on the wrong centreline is agreed with. What it sees is the half nothing else can: the rail the extent is written on, whether the alpha survived glTF, and whether the runs slid by a junction trim. Reads the ETL out tree, because the trims travel in `roadsurface.json` and that does not ship |

**`tools/narrowing.py` sits beside them and is not one of them.** It prices a *proposal* — what
`Q19`'s clearances would read at a lower `surface.floor_default_m` — rather than grading what shipped, and it
does that by importing `pipeline.clearance` and reusing it whole. That is the opposite of the rule
the graders above keep, and deliberate: the question is not whether the measurement is right, which
`carriageway_occupancy.py` answers, but what the same measurement says at a different width. A
second implementation would confound the two. Hand-run, reads the ETL out tree rather than the
shipped bundle, and needs no rebuild — buildings do not move when the ribbon narrows. It **refuses
to print a table whose baseline column does not reproduce `clearance.json` edge for edge**: the
1.60x column is the one thing in the sweep that can be checked against something, so it is a
precondition rather than a diagnostic.

`deck_error.py` owns the shared bundle reader (`bundle_arguments`, `load_bundle`, `log_bundle`,
`Faces`, `wears`, `nearest`); `overhang.py` owns the shared width sweep (`walk_width`,
`cross_section`, `left_of`, `half_width_at`), imported by `ground_clearance.py`,
`carriageway_occupancy.py` and — outside this table — `carriageway_margin.py`, because reimplementing
that walk means rediscovering its duplicated-vertex guard the hard way.

⚠️ **A tool that needs two passes over the carriageway must still *walk* it once.**
`carriageway_occupancy.py` genuinely needs two — the occupier index can only be pruned to the band
the road occupies, so the road has to be measured before the buildings are read — and writing the
walk out twice cost **22 s of a 47 s run** *and*, far worse, made the prune's superset property a
convention rather than a guarantee: pass one visiting less than pass two asks about reads as
**clear**, which is the one direction these tools must never flatter. It records the walk into a
`Lattice` and replays it instead.

### GDScript warnings

The `[debug]` block promotes 21 GDScript warnings to errors. This is the engine's own type-aware
checker, and the only one available that resolves types at all: a grammar-level linter sees `basis.z`
as an identifier and a dot, where the engine sees a `Vector3` on a `Basis`.

✅ **Three of the 21 are engine defaults and never appear in the file.** `native_method_override`,
`get_node_default_without_onready` and `onready_with_export` default to *error* in Godot 4.7, so the
writer omits them on every save; `Q75` read their absence after `78c077e` as a loss and restored
them at no cost, because they had never stopped applying (`Q119`). `tools/verify_settings.gd` names
all 21 and reads each level back through `ProjectSettings`, so a promotion swapped for another fails
and a canonical file passes. ⚠️ **Never edit that list down to match a regression** — a list edited
to match is a check that certifies the wrong state, which is what `Q72` was opened about.

**Level 1 is invisible.** Warnings only reach stdout at level `2`; a warning left at `1` shows up in
the editor's script panel and nowhere else, and the contributor workflow is deliberately headless.
Every enforced warning is therefore at `2`.

**Enforced (`=2`):** `untyped_declaration` · `shadowed_variable`, `shadowed_variable_base_class` ·
`confusable_identifier`, `confusable_local_declaration` · `integer_division`, `narrowing_conversion`
· `unused_variable`, `unused_parameter`, `unused_local_constant`, `unused_private_class_variable`,
`unused_signal` · `standalone_expression`, `standalone_ternary`, `redundant_await` ·
`incompatible_ternary`, `int_as_enum_without_cast`, `int_as_enum_without_match` ·
`get_node_default_without_onready`, `onready_with_export` · `native_method_override`.

**Deliberately not enforced**, with counts measured at the time:

- `inferred_declaration` (~25 hits). It flags `:=`, which *is* static typing — just inferred. The
  `CLAUDE.md` rule asks for static types, not for spelling every one of them out.
- `unsafe_method_access` / `unsafe_property_access` / `unsafe_cast` / `unsafe_call_argument` (~21)
  and `return_value_discarded` (~8). Both trace to a boundary the design chose: generated JSON
  arrives as `Variant`, and `Packed*Array.append()` returns a `bool` nobody reads. Revisit if the
  data contract ever gains a typed loading layer.
- The remaining ~22 sit at engine defaults. `unassigned_variable`, `unreachable_code` and
  `assert_always_false` look worth promoting and were measured as costing nothing.

**This is not a bug-catcher.** None of the four defects recorded under `P0-5b`/`P0-5c` — inverted
steering sign, framerate-dependent drag, an `@export`ed `Node3D` silently null from a hand-authored
`.tscn`, wheel raycasts accepting wall faces — would have been caught by any linter. A review pass
caught them.

### Formatting

`gdformat` (from `gdtoolkit`, in the `dev` extra) is the GDScript counterpart to `ruff format`. Its
default line length is 100, matching `ruff`, so it needs no config file. **`gdlint` is installed but
deliberately not wired in:** it reported 16 hits of one cosmetic rule across four preview scripts,
and it cannot check static typing, which is the convention that actually matters here.

### CI

`.github/workflows/ci.yml` runs on every push to `main` and every pull request, in two jobs: `ruff` +
`pytest` on Python 3.11 and 3.13, and `tools/check.sh` against the Godot version pinned in the
workflow. It runs the script rather than repeating its steps in YAML, for the reason the script
exists: reimplemented in YAML, the Godot steps would pass on failure.

**CI cannot check the generated-asset contracts.** `game/assets/generated/` is gitignored build
output, so a fresh checkout has no city. The workflow sets `VERIFY_GENERATED=0`, which skips those
tools and *prints that it skipped them* — an unannounced skip would be the same silence the script
was written to break. Giving CI a city means running the ETL there, whose first act is downloading
~320 MB from a government server; that is a deliberate non-goal on every push.

---

## Repo layout

```
hk-taxi-Q/
├── CLAUDE.md                    # agent instructions — read first
├── docs/
├── etl/                         # Python: geodata → game assets (build time)
│   ├── config/
│   │   └── hong_kong.yaml       # bounds, source URLs, tiling, vocabularies — the tunable city facts
│   ├── pipeline/
│   │   ├── config.py            # loads hong_kong.yaml — the only route config facts take in
│   │   ├── hongkong.py          # the constants that ARE the city: CRS pair, drive-on-left (Q100)
│   │   ├── crs.py               # projected coords -> game space; codes from hongkong.py
│   │   ├── fetch.py             # download from CSDI / data.gov.hk, cache to sources/
│   │   ├── documents.py         # read/write a stage's JSON + its schema check; no policy
│   │   ├── gltf.py              # glTF read + GLB write; no dependency
│   │   ├── gdb.py               # geodatabase layers + WKB → numpy; format only, no policy
│   │   ├── geometry.py          # plan-space helpers shared by the drawing stages
│   │   ├── polyline.py          # polyline walking/measure helpers
│   │   ├── mesh.py              # merge, partition, LOD collapse — geometry, no policy
│   │   ├── meshbuild.py         # the shared mesh accumulator the drawing stages feed (Q100)
│   │   ├── colour.py            # the authored palette, resolved; no stage owns a colour
│   │   ├── terrain.py           # terrain / structure mesh → sampleable height field
│   │   ├── podiums.py           # iB1000 blocks → podiums.json, the tower↔block boundary
│   │   ├── buildings.py         # sheets → vertex-coloured tiles + LOD tiers
│   │   ├── landmarks.py         # hero-building placement → landmarks.json
│   │   ├── roads.py             # Road Network geodatabase → roadgraph.json
│   │   ├── carriageway.py       # the width/lane survey roads.py publishes (Q94/Q95)
│   │   ├── kerbside.py          # NSR restrictions linear-referenced onto the graph
│   │   ├── surface.py           # roadgraph.json → roads.glb; ribbon, kerbs, junctions
│   │   ├── clearance.py         # what stands in the ribbon → clear width per station
│   │   ├── fares.py             # taxi stands + PUDO + POIs → fare nodes
│   │   ├── tramway.py           # published tram rails → tram.glb (P3-14)
│   │   ├── arrows.py            # published turn arrows → arrows.glb + arrows_placements.json (P3-15, P5-4)
│   │   ├── boxjunctions.py      # published box junctions → boxjunctions.glb (P3-18)
│   │   ├── roadmarks.py         # published stop / give-way lines → roadmarks.glb (P3-23)
│   │   ├── carve.py            # INFRASTRUCTURE cut back to the surveyed carriageway (P3-28, Q19)
│   │   ├── railings.py          # published railings → railings.glb + railings_placements.json (P3-19, P5-5)
│   │   ├── signs.py             # published traffic signs → signs.glb (P3-16)
│   │   ├── sign_sheets.py       # TD's sign drawings, rasterised (P3-20)
│   │   ├── sign_text.py         # sign lettering → signs_text.png (P3-20, Q68)
│   │   ├── signals.py           # published signal heads → signals.glb (P3-17, latent — Q77)
│   │   ├── lamps.py             # published lamp posts → lamps.glb + lamps_placements.json (P3-26, P5-3)
│   │   ├── placements.py        # a prop library's stands: entry shape, pitch, drawn totals, writer (P5-3, P5-4)
│   │   ├── export.py            # → city.json, assembles and validates the stage outputs
│   │   └── __main__.py          # `python -m pipeline` — 19 stages, in order
│   ├── sources/<source>/        # raw downloads — GITIGNORED
│   ├── out/<region>/            # pipeline output — GITIGNORED
│   └── tests/
├── game/                        # Godot project
│   ├── project.godot
│   ├── export_presets.cfg       # COMMITTED — never put signing credentials here
│   ├── scenes/
│   │   ├── main.tscn            # Main / World / GUI — the boot scene
│   │   ├── city_drive.tscn      # the level World holds: streamer, layers, taxi, chase camera
│   │   ├── dev/                 # grey-box circuit, skidpad, city preview
│   │   ├── vehicle/             # taxi.tscn
│   │   └── world/               # shared rigs: lighting, sky
│   ├── scripts/
│   │   ├── core/                # pure logic, minimal engine coupling
│   │   ├── city/                # tile streaming, road graph runtime
│   │   ├── vehicle/  traffic/  fares/  input/  ui/  camera/
│   ├── assets/
│   │   ├── generated/           # ETL output — GITIGNORED, build artefact
│   │   ├── authored/            # hero buildings, vehicles, UI — COMMITTED
│   │   └── shaders/
│   ├── tuning/                  # .tres resources: handling, streaming, fares, scoring
│   └── tools/                   # headless scripts — import fixups, verify tools
└── tools/                       # dev scripts: check, sync, export, grading
```

⚠️ **`scenes/dev/` is not shipped.** `run/main_scene` boots `scenes/main.tscn` — `Main` with a `World`
that instances `scenes/city_drive.tscn` and a `GUI` that holds the HUD, the shape Godot's own
guidance names, so a level change swaps `World`'s children and the HUD stays (`Q119`). Still a
knowing placeholder: the level needs the gitignored `assets/generated/`, so a fresh clone boots to an
empty world with only a `push_warning`. An export is a demo rather than a build until there is a
menu in front of it — but since `P2-1` put `CityStreamer` on the boot path in place of
`tile_preview.gd`, it is no longer a demo that blows the frame budget: 268,709 primitives at the
spawn against the 1.16 M the preview cost.

**Why the ETL is a separate Python project:** it runs rarely, at build time, and needs GDAL — which
has no good Godot equivalent.

---

## Data contract

The interface between ETL and game. **Versioned — change both sides together and bump
`schema_version`.** All positions are game-space metres.

> **When to bump:** where a consumer would be **wrong** to keep its old interpretation, not wherever
> bytes change. `P2-7` bumped `roadgraph.json` because `polyline.y` began meaning something new while
> looking identical — the case a diff cannot show you — and did *not* bump `roads.glb`, whose
> geometry moved but whose attributes kept their meaning.

### `city.json` — manifest

```json
{
  "schema_version": 21,
  "city_id": "hong_kong",
  "region_id": "wan_chai",
  "source_crs": "EPSG:2326",
  "origin": { "easting": 835765.0, "northing": 816125.0, "elevation": 0.0 },
  "city_offset": [38379.0, 0.0, 32826.0],
  "bounds_game": { "min": [-32.0, -13.049, -73.571], "max": [1704.698, 378.532, 923.142] },
  "tile_size_m": 150,
  "tiles": [
    {
      "id": "t_00_00",
      "lods": ["tiles/t_00_00_lod0.glb", "tiles/t_00_00_lod1.glb"],
      "aabb": [[8.37,4.935,-16.588],[167.562,70.801,165.268]]
    }
  ],
  "road_graph": "roadgraph.json",
  "road_surface": "roads.glb",
  "carriageway": [
    { "edge": 651, "half_width_m": [5.12, 5.12, 4.32, 3.2],
      "clear_width_m": [-1.0, 10.24, 8.5, 0.0] }
  ],
  "lane_width_m": 3.2,
  "car_width_m": 1.8,
  "fares": "fares.json",
  "tramway": "tram.glb",
  "arrows": "arrows.glb",
  "boxjunctions": "boxjunctions.glb",
  "lamps": "lamps.glb",
  "railings": "railings.glb",
  "signs": "signs.glb",
  "signs_text_atlas": "signs_text.png",
  "roadmarks": "roadmarks.glb",
  "signals": null,
  "landmarks": "landmarks.json",
  "fence": "fence.json",
  "landmark_assets": ["landmarks/hkcec.glb"],
  "etl_version": "0.1.0",
  "generated_utc": "2026-07-30T20:04:03Z"
}
```

⚠️ **`lane_width_m` and `car_width_m` are two bars over one measurement, and merging them is the
one thing `Q19` forbids here.** The first is what `P3-3`'s traffic is *routed* on (`RoadGraph.is_passable`,
`Q51`); the second is what the **player** is fenced at (`RoadGraph.fits_car`, `P3-29`). Both read the
same `carriageway[].clear_width_m`. At the car's bar the router would be sent down `e207`'s 1.95 m;
at the lane's the player would be fenced out of `e781`'s 3.50 m. `car_width_m` is `null` where the
city declares no `clearance:` block, which reads as "nothing is fenced" — a missing bar is not a bar
of zero.

⚠️ **`fence` is named unconditionally, unlike the optional assets.** `pipeline/fence.py` writes its
document on every run, so an empty `barriers` list means the fence found nothing to close and a
*missing file* means the stage never ran — two states a build has to be able to tell apart.

`origin` is computed by the ETL from the region bounds, never authored — `floor(min_easting)` and
`ceil(max_northing)`, i.e. the region's **north-west** corner. The game never needs it; it is what
puts a game-space position back on the source map.

**The manifest names the other documents, it does not contain them.** The road graph is 0.65 MB on
disk and ~6 MB parsed, and `RoadGraph` wants it at a different moment from when `CityStreamer` wants
the tile list. Each of the three is separately versioned. A build ships exactly what the manifest
names — **147 files and 54.1 MB** for Wan Chai, which the `export` stage prints on every run. The
PCK it exports to is a separate measurement and lives in `PROGRESS.md`'s Bundle-size metric, because
it is measured from the PCK and never summed from these files.

**The game must read the manifest to find its tiles — there is no fallback.** In the editor `res://`
is a real directory and `DirAccess.get_files_at` lists it; in an exported build it is a PCK archive
Godot's virtual filesystem will not enumerate, so the same call returns nothing and the city renders
empty **with no error**. `scripts/city/city_manifest.gd` is the only supported route.

⚠️ **`carriageway` is the drawn half-width, and the game cannot derive it.** `roadgraph.json`
publishes the street itself — **measured** where two publishers license a reading and authored
elsewhere (`Q95`, `width_source`) — while `surface.py` draws the ribbon at
`max(width_m, floor_for(...))`: a **10.24 m** floor by default, 12.48 m at 70 kph, and **0.0 m on
structure**, where the deck is a fixed width the ribbon must not overhang. So a consumer must read
this table rather than assume the drawn width exceeds the authored one — 🔴 **since `Q95` it can be
exactly equal at grade**, on any street already wider than its floor, which is what turned the
engine's old "must be wider" assertion into "must not be narrower". The widening lives on the ETL's surface style, deliberately: *"the
graph is a description of the city, this is how wide and how kerbed to draw it. A change here never
changes `roadgraph.json`."* Without it a lane centre falls short by a quarter of the widening —
0.96 m on a two-lane street — putting a car that much nearer the seam where opposed ribbons overlap
and a suspension ray hunts between two coplanar triangles.

⚠️ **One value per station since schema 4**, indexed by that edge's `roadgraph.json` polyline and the
same length as it. `elevation_level` is an attribute of a whole edge, but a road becomes a bridge
partway along one. Reading `[0]` as if it covered the edge is right on 769 of the region's 797 edges
and 0.96 m out on the rest, which is exactly the error this table exists to prevent. `RoadGraph`
warns and falls back to the authored width rather than failing; `verify_road_graph.gd` treats the
table's absence as an error.

⚠️ **`clear_width_m` is what *stands in* the tarmac, and no consumer can derive it either.**
Published since schema 9 (`Q51`), one value per station beside `half_width_m` and indexed the same
way, so both come off one station. It is the widest continuous gap a car could get through at that
cross-section, measured by `clearance.py` between 0.30 m and 2.00 m above the deck — the same band
`Q19` measures over, so the two stay comparable. **`-1.0` means no cross-section was judged there**,
because `surface.py` had held the ribbon back for a junction cap; negative rather than zero because
no real clearance can be, and zero is the one value that would read as *blocked solid* on precisely
the stations that are not. `lane_width_m` travels with it as the bar: `roadgraph.json`'s `width_m`
is a **survey** since `Q95` — measured where publishers license a reading, authored elsewhere,
never `lanes × lane_width_m` — so dividing it back does not recover this number. `RoadGraph` reads
the pair as `is_passable` / `is_routable` and — deliberately
— does **not** fold either into `nearest_edge`. What a query does instead is **report** it:
`Hit.clear_width_m` is the gap at the segment the hit landed on, so a consumer that must not put a
car in a wall can guard itself without the index deciding for every other caller. `RoadSpawn` is
that consumer (`Q52`), and it too reports rather than refuses — `verify_spawn.gd` is what fails.

⚠️ **`bounds_game` is the union of the content, not the region rectangle.** Wan Chai's declared
region is 1650 × 887 m; its geometry spans 1737 × 997 m, because a building is assigned to a tile
whole and may overhang, and because the road ribbon is drawn outward from centrelines that run right
up to the edge. A consumer sizing a spatial partition, framing a camera, or placing diegetic map
edges off the rectangle will clip real geometry.

`generated_utc` is a build stamp and the **only** field that changes between two builds of identical
inputs — verified by rebuilding from a clean `out/` and diffing. Strip it before diffing two builds.

#### Tiles

`lods` is ordered nearest-first, one file per tier, matching `lod_cell_sizes_m` in city config —
except where `class_lod_cell_sizes_m` holds a mesh class back. A tier is **not** a single cell size:
a building decimates at 1.5 m and an elevated road deck at 0.5 m, because a deck thinner than the
cell flattens into it. The tile is still one mesh and one draw call, because each class is collapsed
separately and merged afterwards. See `ART_DESIGN.md` "LOD policy".

⚠️ **The ground is decimated before it is tiled, not after** (`Q25`). Every other class is cut into
tiles and then decimated per tile — which is safe for a building, because a building is assigned to
one tile whole and never cut. Cutting a *continuous surface* first makes each side of a boundary
average over different vertices, so the two land in different places and the sheet tears: measured
at **15.65%** of probes within 2 m of a tile boundary with no ground over them, against 0.61%
beyond 10 m. Decimating the region's ground once and cutting the result closes that by construction.

⚠️ **`tiles[].aabb` is the union of the tiers a build actually ships, not of the source geometry.**
Decimation moves corners and drops anything thinner than a cell, so a source box can describe
geometry no shipped mesh contains — one Wan Chai tile declared a height 19 m past its own LOD0. Nor
is tier 0's box enough on its own: `collapse` buckets on `floor(position / cell_m)` and averages, so
a coarser grid can leave an extreme vertex alone in its cell and preserve it where a finer grid
averaged it inward, measured at 12.03 m on `t_01_02`. `verify_city.gd` asserts every tier is
contained and the union is tight to 1 cm.

**A tile's `aabb` can be larger than the tile.** Buildings are assigned to a tile whole, by their
centre, so one may overhang its neighbour by half a footprint — measured at up to 222 m across a
150 m tile. **Use the `aabb` for culling and streaming distance, never the tile's grid position.**
Tile vertices are in region game space, so a tile needs no transform; that is why `city.json` gives
tiles an `aabb` but no position.

**Tile output carries no textures.** One material, one primitive, colour in `COLOR_0` — that is what
makes a tile one draw call, checked in-engine by `verify_tiles.gd`. Since `P3-7` it also carries
`TEXCOORD_0`, which is **not** a texture coordinate: no image is sampled, and `merge` still refuses a
textured mesh outright.

⚠️ **"No textures" is stricter than it sounds, and the strict part is enforced in code rather than
only stated here.** `scripts/city/mesh_contract.gd` walks **every shader uniform** and fails on any
that holds a `Texture`, not just the `BaseMaterial3D` albedo/normal/ORM slots — *"a sampler bound here
would ship an image into a bundle specified to carry none while every other check passed."* So a
single region-wide data map sampled by world position — a sky-visibility or AO bake, which needs no
UVs and adds no draw call — is **not** a loophole in this contract. It is a deliberate amendment to
it, and it has to change `mesh_contract.gd` and this paragraph together. The check exists to force
that conversation rather than to make it impossible.

| Attribute | Meaning |
|---|---|
| `COLOR_0.rgb` | The surface's albedo, **sRGB-encoded**, as normalised `uint8`. Every consumer must linearise it — see the warning below |
| `TEXCOORD_0.x` | Metres above **that source object's own base**. A vertex knows its world Y, not where its building starts, and the region's ground moves 40 m — so world Y is not even a proxy. Metres rather than a 0-1 fraction because the floor *count* is the signature the window shader exists to carry |
| `TEXCOORD_0.y` | `floor()` is a `SurfaceClass` marker — 0 façade, 1 ground, 2 structure. `fract()` is a per-object phase in 1/256 steps, so neighbouring towers do not line their window rows up |
| `TEXCOORD_1` | 🚫 **Not shipped since schema 20** (`Q102`). From schema 6 to 19 `x` held a packed façade-survey state — `code = glz + 4·tint + 1024·grammar`, every field's 0 meaning "refused → fall back to the hash" — and `y` was reserved at a documented layout for `Q42`'s riders (storey pitch, podium floors, balconies, emphasis). The only producer of a committed value was `Q41`'s vision reader, withdrawn on cost, so the channel could carry nothing but the refusal sentinel. It was **removed rather than shipped all-zero**: zero was a legal code, so an all-sentinel tile is indistinguishable from a survey that ran and declined every building, and the bundle would have claimed a survey it did not carry. `verify_tiles.gd` now asserts the attribute's *absence*, which is also what catches a lightmap unwrap synthesising one |
| Material name | **`city_facade`**, and the name is the contract. glTF cannot say "use this shader", so `tools/generated_scene_import.gd` dispatches on the name and hands the tile `tuning/city_facade.tres`; everything else in the bundle keeps its `BaseMaterial3D` |

⚠️ **The `TEXCOORD_1` codec constants were contract rather than tuning, and the rule outlived
them.** The bin ranges and field multipliers were mirrored in `etl/pipeline/buildings.py`
(`facade_state`) and `assets/shaders/city_facade_clean.gdshader` (`SURVEY_*`), with this table as
the tiebreak, because a one-sided "tuning" of a bin edge decodes every surveyed building silently
wrong. All three copies went at `Q102`. The rule stands for the codecs that remain — `roads.glb`'s
marking state below, and the tramway's class — and it is why none of them lives in the city yaml.

⚠️ **Data-supplied podium metres enter through the floors field, not around it** (`Q47`, argued
2026-08-11). `Q47`'s route makes an iB1000 `P` block the boundary authority where a tower meets one —
in metres — and bits 7–11 still carry floors. The two agree by construction: the pack converts
metres → floors against the same packed storey pitch (bits 0–6) the shader multiplies back, so the
round-trip lands within half a pitch, and a boundary between floor lines was never renderable
anyway — window rows exist only on the storey grid. A separately-quantised metres field would add a
second grid that cannot agree with the first. Full-precision metres, the block references and the
mechanism that won (`authored > data > survey > hash`) stay in the ETL intermediate `podiums.json`,
which `export.py` never names: the runtime does not branch on provenance, and `R4`'s grading — its
only consumer — runs in the pipeline. Nothing in this route bumps `schema_version`: `y` is still all
zeros, and `R4`'s eventual write remains the "filling a reserved field" case above, whose
`verify_tiles.gd` range check moves in that commit.

⚠️ **The phase is quantised to 1/256 because float32 rounds it into the next marker otherwise.** The
raw seed reaches 1 − 2⁻³², and float32's spacing near 2.0 is ~2.4e-7, so `STRUCTURE + 0.9999999998`
becomes exactly `3.0` — an unknown marker with a lost phase, on whichever viaduct drew a high seed.
1/256 is exactly representable at every marker, so `floor` and `fract` round-trip in the shader.

⚠️ **The marker is derived from the palette, not from a config key.** A class with a flat
`class_materials` entry is one whose colour does not depend on its height, which is exactly the set
with no floors to band; anything the height ramp colours is a façade. So a later region gets the right
answer from its own palette, and no class name reaches pipeline logic (hard rule 3).

⚠️ **Three places have to agree and only one of them can fail loudly.** The ETL names the material,
the import script recognises the name, the shader reads the payload — and if any link breaks, every
tile keeps its default `BaseMaterial3D` and renders in flat vertex colour, which is what the city
looked like *before* `P3-7`. There is no error and nothing on screen that reads as broken.
`verify_tiles.gd` therefore asserts both the payload and the resolved material path.

**The finest tier ships collision; no other tier does.** The tier-0 mesh is named `<tile_id>-col`,
and Godot's glTF importer reads that suffix into a `StaticBody3D` carrying a
`ConcavePolygonShape3D` — the same mechanism `roads.glb` uses, chosen for the same reason: the
collider is part of the asset, so `CityStreamer` builds no shape at load and the collider cannot
drift from the geometry it is drawn from. Only the finest tier, because a tier is selected by
distance and the coarse one is resident only *beyond* the 250 m near band, where nothing can touch a
building. `verify_tiles.gd` asserts it in both directions — present on tier 0, absent on every other
— because a suffix that spread would be invisible in every screenshot and show up only as bundle
bytes. **Measured cost: 5.17 MB of PCK** (21.10 → 26.27 MB, one variable changed), not the 14.91 MB
tier 0's 434,149 triangles come to as raw faces; the pack compresses them.

**Terrain ships in the tile primitive since `P3-10`.** It is one more entry in `buildings.classes`,
so it collapses at its own cell size (4 m / 8 m) and then merges with the massing: **+87,649
triangles at LOD0, no texture, and no extra draw call.** No `schema_version` bumped — nothing was
added, removed or renamed, and no attribute changed meaning. A consumer reading a tile is not
*wrong* to keep its old interpretation; it simply draws more. `tiles[].aabb` and `bounds_game` grew
(1668 × 942 m → 1737 × 997 m, quoted as 1728 until `P3-7` rebuilt and checked it against a `HEAD`
baseline) and the region gained a 66th tile, because ground reaches corners no
building did.

⚠️ **The tier-0 collider now includes the ground, and nothing in the ETL says so.** The suffix goes
on the *merged* mesh, so anything in `classes` collides at that tier whether or not it was asked to
— which is what makes the pavement drivable, and is worth knowing before adding a third class.
`buildings.ground_sink_m` drops the ground under the kerb so the two surfaces do not fight;
`tools/ground_clearance.py` grades it.

**The vertex stream gained `TEXCOORD_0` in `P3-7`, and `schema_version` went 4 to 5.** Its meaning is
in the table above. Two things about what it cost:

⚠️ **It ships float32, not the "~2 bytes/vertex quantised" this file predicted, and the prediction
was out by more than the encoding.** Measured from PCKs with one variable changed: **32.36 → 36.37 MB,
+4.01 MB**, against 937,889 vertices across both tiers — 7.50 MB of raw VEC2 that the pack compresses
by 47%. Quantising to `unorm16` would halve the raw side and save perhaps 2 MB, at the price of a
scale factor in the contract on both sides. **Not done, because the bundle budget is 200 MB and the
build is nowhere near it** — `PROGRESS.md`'s Bundle-size row owns the current figure (the 36.37 here
is the build as measured then); the note is here so a later region short of room knows where 2 MB is
hiding.
Peak ETL RSS went **800 → 900 MB** on the same machine, from materialising 8 bytes a vertex through
the bucket phase where `colour_for` gets away with a broadcast view.

**The vertex stream gained `TEXCOORD_1` in the `Q40`/`Q41` plumbing at `schema_version` 6, and
lost it again at 20** (`Q102`). It carried the measured façade verdicts — reader-glazed, binned
glass tint, five-state grammar — packed as one integer state code per building, with the second
float reserved at a documented layout for `Q42`'s riders. It cost **+0.24 MB of PCK** (36.32 →
36.57, measured with one variable changed): 7.50 MB of raw VEC2 that the pack compressed by 97%,
far cheaper than `TEXCOORD_0`'s +4.01 MB because the payload was a per-building constant with `y`
all zeros. That is the figure the removal gives back.

⚠️ **The removal is the interesting half, and its argument is not the bytes.** The reader was
withdrawn on cost, which left every field able to hold only its own `0` — and `0` meant "refused →
fall back to the hash". A channel that can only say "refused" is not a cheap channel, it is a
bundle asserting a survey it does not carry, and no consumer could tell that state from a survey
that ran and declined every building. So the attribute goes, `verify_tiles.gd` asserts its
**absence**, and `schema_version` bumps on `P3-6`'s removal precedent.

⚠️ **The importer hazard outlived the payload.** `meshes/light_baking = 2` (Static Lightmaps) makes
Godot's importer generate its own UV2 unwrap; it used to overwrite the payload with fractions in
`[0, 1]` that pass every visual inspection, and now it would *fabricate* a channel the contract
forbids. The tiles ship `= 1` (Static), `verify_tiles.gd` asserts that setting directly, and its
absence check catches the same regression a second way — more cheaply than the per-vertex codec
scan it replaced, and with no legal value to be confused with a corrupt one.

⚠️ **The ground marker was reserved here rather than left to a later task.** Merging bought the
ground a free draw call and cost it its own material, so a ground-only treatment — slope blending, a
PBR-ish roughness variation, any ground shader — had nothing to select on. `SurfaceClass.GROUND` is in
the payload now and the shader ignores it, which cost one commit instead of a second schema bump. What
it does **not** buy is a usable height: `TEXCOORD_0.x` measures from each source mesh's own base, and
the ground's meshes are sheet-shaped, so the value is not comparable across a sheet boundary.

⚠️ **`COLOR_0` is sRGB-encoded, and every consumer has to linearise it itself.** The ETL picks
colours in CIELAB and writes the sRGB bytes, because sRGB is what 8 bits are *for* — it spends its
codes where the eye can tell them apart, and a linear `uint8` would starve the shadows to gild
highlights nobody can separate. The cost is that nothing downstream converts for free. Godot 4 has no
`vertex_color_is_srgb` **render mode** (it survives only as a `BaseMaterial3D` flag), so every shader
in the bundle takes a shared `vertex_srgb_to_linear` from `assets/shaders/colour.gdshaderinc`, and
`generated_scene_import.gd` sets the flag for everything that names no shader.

⚠️ **The two branches are exclusive, and moving an asset from one to the other is a silent
regression waiting to happen.** `P3-12` moved the road surface off the flag and onto a shader, so
`road_markings.gdshader` had to pick the conversion up in the same commit — nothing fails loudly
when that is forgotten; the surface just lightens and stops varying with its own albedo.
`colour.gdshaderinc` exists because that was the **fourth** copy of the function, which is the
trigger `city_facade.gdshader` had written down in advance.

⚠️ **The same trigger fires on whole shaders, not just on functions inside them** (`Q71`). The turn
arrows, the box junctions and the stop lines each shipped a `.gdshader` that was byte-identical to
the other two but for a default colour; they share `marking_paint.gdshader` now, on the precedent
`railings.gdshader` already set with `railings` / `bollards` / `barriers`. **A layer is a
parameterisation, not a shader** — the colour is in each `.tres`, and
`MeshContract.check_shader_material` still holds every layer to its own material by `resource_path`,
so sharing the shader cost the dispatch check nothing.

This was silent until `Q27`. Skipping the conversion does not merely lighten the city: sRGB read as
linear is *brighter than it should be*, and brightness the albedo did not ask for is brightness that
does not vary with albedo. Measured, **57%** of a lit facade pixel's luminance was albedo-independent,
and a per-building albedo difference reached the screen at **a third** of its size. No lighting change
touches it, which is why it survived a full sweep of the rig. If a future consumer of `COLOR_0`
forgets this, the symptom is a pale city whose palette "does not seem to do anything" — reach for
`tools/frame_stats.py` before reaching for the lights.

⚠️ `COLOR_0.a` is a constant `255` today and looks like the cheaper place for a shader mask. It is
not: `generated_scene_import.gd` sets `vertex_color_use_as_albedo` project-wide, and an opaque
`BaseMaterial3D` ignores albedo alpha only until somebody enables transparency on a tile — after
which the city renders see-through with no error. `TEXCOORD_0` has no such failure mode.

### `roadgraph.json` — drivable network

```json
{
  "schema_version": 11,
  "nodes": [{ "id": 1, "pos": [120.5, 4.0, 300.2], "kind": "junction" }],
  "edges": [
    {
      "id": 1, "from": 1, "to": 2,
      "polyline": [[120.5, 4.0, 300.2], [180.0, 4.1, 305.0]],
      "on_structure": [false, false],
      "structure_bounded": [false, false],
      "direction": "both",
      "lanes": 3,
      "lanes_source": "measured",
      "width_m": 11.0,
      "width_source": "two_way_span",
      "width_publisher": "hyd_pavement+ib1000",
      "speed_limit_kph": 50,
      "bus_lane": false,
      "tram_tracks": false,
      "elevation_level": 0,
      "road_name": { "en": "Gloucester Road", "zh": "告士打道" },
      "kerbside": [{ "side": "near", "from_m": 12.4, "to_m": 88.1, "kind": "double" }]
    }
  ],
  "turn_restrictions": [{ "from_edge": 1, "via_node": 2, "to_edge": 5 }]
}
```

| Field | Source |
|---|---|
| `direction` | `TRAVEL_DIRECTION` (1 = bidirectional → `both`, 3 = one-way → `forward`). Closed vocabulary: **only `both` and `forward` are ever written.** A city whose source codes direction against its own digitisation declares `backward` in config, and the ETL normalises it away by reversing the polyline |
| `turn_restrictions` | `TURN_ID` + `EDGE(1-8)FID`. Edge references are **indices into `edges`**, not source ids |
| `speed_limit_kph` | `SPEED_LIMIT` layer where present, joined on `ROUTE_ID`; otherwise the city default. Hong Kong signs only exceptions, so **the default covers ~90% of edges** |
| `bus_lane` | `BUS_ONLY_LANE` layer, joined on `ROUTE_ID` |
| `tram_tracks` | ⚠️ **Hand-authored.** Not in the source. A list of street names in city config |
| `lanes` | 🔴 **Measured on 210 of the 292 surveyed edges since `Q94`**, and authored on the rest. Nobody publishes a lane *count* — Road Network v2 carries no lane field in any layer — but three sources publish the *width*, so `pipeline/carriageway.py` brackets its measured carriageway against TPDM 4.3.9.8's **3.0-3.65 m** through lane. ⚠️ **Never divided by `lane_width_m`**: 3.2 m is the authored constant the question is about, and dividing by it makes the instrument agree with the value under test. Where TD's range resolves to one integer the count is published — **153 `measured`**. 🔴 **Where it does not, the arrows settle it**: a row of turn arrows across a carriageway is the count written down, and it is the one lane reading owing nothing to a width, so it resolves **57** ambiguous brackets as `arrows`. ⚠️ **A row of ONE arrow is refused** — the row counts *painted* lanes, so it is a lower bound and at one abreast it states a marking; 81 edges do that. ⚠️ **Ambiguous brackets only**, so a measured `lanes_source` implies a measured `width_source` by construction. The remaining **82** edges keep `lanes_for(speed_limit_kph)`; `lanes_source` says which. 🔴 **`lanes` CAN BE 1 since `Q114`, and a consumer may not assume otherwise** — that is why schema 11 bumped. A resolved bracket of one used to be published as **two**, on `RoadGraph.lane_offset`'s need to keep a lane centre off the centreline; that floor is now in `lane_offset` itself as `LANE_FLOOR`, and **60 edges** publish a single lane. There is no `floored` source any more. 🔴 **And `deck_capped` is a REFUSAL, not a reading**: off-grade nothing publishes a count at all, so `lanes` is the speed-limit table, and where that names more lanes than the edge's own deck can hold under 4.3.9.8 the count is cut to the deck's ceiling — **6 of 36** deck edges, while 8 authored *below* their ceiling are left untouched. ✅ **19 of 306** arrow-carrying edges imply more lanes than they have. ✅ And **0 of 208** measured counts disagree with `tools/carriageway_margin.py`'s independent bracket |
| `width_m` | 🔴 **Measured on 292 of 737 level-0 edges since `Q95`** (260 at `Q95` itself; HyD's polygons then added and refined edges), from what the publishers drew; authored `lanes x lane_width_m` on the rest, with `width_source` saying which. ⚠️ **A consumer may no longer invert `width_m / lanes`** — that is why the schema bumped. The authored value it replaced was `2 x 3.2 = 6.4 m` on 720 of 737 edges, below TD's published **7.3 m** minimum for a two-lane single carriageway (6.75 m being allowed only *per direction* of a dual): invented *and* out of range. ⚠️ **This is the street, never the ribbon** — `surface.py` draws `max(width_m, floor)` |
| `width_publisher` | 🔴 **Which publishers supplied the stations behind `width_m`, joined on `+`; empty where authored** (`Q94`, schema 7). The publishers do not measure the same quantity: HyD's `pavement_polygon` carves traffic islands, run-ins and car parks out of the carriageway, so it reads the **trafficable** surface where TD's and iB1000's lines run on to the kerb — p10 **-3.39 m** apart over the 4,925 stations both span. ⚠️ **A set, not a winner**: the survey picks a publisher per *station*, so 201 edges here read `ib1000`, 62 `hyd_pavement+ib1000`, 21 `hyd_pavement`, and 8 carry a `traffic_aids` combination. ⚠️ It records who was **used**, not who could have answered — the loop stops at the first publisher to span a station |
| `elevation_level` | `ELEVATION` integer attribute (−1/0/1 in this region). An ordinal level, **not** a height, and never a height — it says which deck a road is on, not where that deck is. Since `P2-7` it is also **not** what decides `y` |
| `polyline` / `pos` | Game-space metres, `y` measured **from ground level, not from the vertical datum**. Since schema 2 an off-grade edge's `y` is **sampled from the map sheets' `INFRASTRUCTURE` structure**, so it follows the real deck and varies along an edge — median grade 2.47%, p90 8.04%. Level-0 edges meeting a node another level also reaches are lifted onto the ramp they sit on, and off-grade ones are ramped **down** to such a node where the structure stops before reaching it (`Q90`). Where the structure covers nothing, `elevation_levels` in city config supplies the flat offset. A node's `y` is the **level nearest grade** among the edges meeting it, and the highest end on that level |
| `on_structure` | ⚠️ **Derived, not published by any source.** One flag per vertex, added in schema 3: true where that station's height came from sampled structure. `elevation_level` says which deck an edge *belongs to*; this says which of its stations are *standing on one*, and the two differ because a road becomes a bridge partway along an edge. Only `roads.py` can produce it — `y` cannot stand in, since `ground: terrain` puts an at-grade hill road at 49 m. All-false for a city that samples no decks. ⚠️ **Also false where an off-grade station was ramped down to the node its structure stops short of** (`Q90`) — that station's height came from the street, not from a deck, and the field says so. **872 stations** in Wan Chai, **546 m** of level-0 centreline |
| `structure_bounded` | 🔴 **Derived, per vertex, added in schema 8** — true where structure stands *beside* the carriageway at that station. `on_structure` cannot stand in: it is height provenance, so an approach ramp walled on both sides but sampled off the terrain reports every station off structure (`e233`, `e55`, `e398`). A consumer reading `on_structure` as "is this carriageway bounded" is **wrong** about the whole Wan Chai Interchange — that is why the schema bumped. **427 stations** in Wan Chai |
| `road_name` | `STREET_ENAME` / `STREET_CNAME` — **bilingual names ship in the source.** The null sentinel has four spellings; normalise NFKC and fold dashes before comparing |
| `kerbside` | `NSR`, added in schema 4 (`P3-13`, closes `Q54`). Runs of one kerb a published no-stopping restriction covers. ⚠️ **The only overlay here that is not a key join** — `NSR` carries street codes, not `ROUTE_ID`, so `pipeline/kerbside.py` linear-references it onto the finished graph. `side` is the ribbon's own, `near` at `TEXCOORD_0`'s `U = 0` and `off` at `U = lanes`; `from_m`/`to_m` are measured along **this** polyline, so a consumer drawing on the trimmed ribbon subtracts its own `trim_start_m`. `kind` is `double` (a 24-hour restriction) or `single` (posted hours), from `TIME_ZONE`. ⚠️ **Only `VEHICLE_TYPE = 1` is here** — a taxi, PLB or goods-vehicle restriction is a sign, and `5` "Others" names no class. Runs are ordered and disjoint per side. **26,065 m over 650 edge sides** in Wan Chai |

**Nodes are formed where centrelines share an endpoint, and nothing else.** Not where they cross: two
roads crossing in plan at different `ELEVATION` share no endpoint, so no junction is invented.
Conversely `ELEVATION` is deliberately **not** part of a node's identity — every place two levels
meet at a shared endpoint is a ramp touching down, and splitting there severs the elevated network
from the ground one.

**Geometry is clipped to the region, not kept whole.** Unlike a building — assigned to a tile whole
and allowed to overhang — a road feature is cut at the boundary, because a polyline cut in two is two
polylines with nothing to seam. Without it, 14% of the region's road length is geometry the player
cannot reach, including a tunnel running 570 m out into the harbour.
⚠️ **That is also why two regions cannot yet be joined (`Q116`).** "Nothing to seam" holds for one
region alone; two neighbours each cut on their own rectangle meet at a hard edge with no continuing
graph, ribbon, kerb run or lamp row. `P5-7` moves the cut onto the graph — an edge belongs whole to
one region and a boundary node is published by both — and the rectangle stays as the sheet selector.
Until then Phase 5's second region is blocked on it, and no streaming unit changes that.

`node.kind` is `junction` where three or more edge ends meet and `endpoint` otherwise. Degree, not
the source's intersection layer: two centrelines meeting end to end is one road continuing through a
geometry break, and the source records those as intersections too.

### `roads.glb` — the drivable surface

One vertex-coloured mesh for the whole region, generated from `roadgraph.json` by `surface.py`. Not
tiled: at 32k triangles it is a small fraction of the massing, it is on screen whenever the player is, and
splitting it would buy nothing but seams and draw calls.

| Property | Value |
|---|---|
| Mesh name | `road_surface-col` |
| Primitives | 1 — one draw call, like a tile |
| Attributes | `POSITION`, `NORMAL`, `COLOR_0`, `TEXCOORD_0`, `TEXCOORD_1`; no texture |
| `TEXCOORD_0` | **U is a lane coordinate**, 0 at the **nearside** kerb line and `lanes` at the offside, so an integer U is a lane boundary whatever the widening did to the metres. V is metres along the carriageway. Junction caps carry `(0, 0)` — a junction is not a length of lane |
| `TEXCOORD_1.x` | The packed **marking state** (`P3-12`), a non-negative integer, constant per edge: `code = class + 4·lanes + 64·direction + 256·bus_lane + 512·tram_tracks`. `class`: 0 carriageway · 1 kerb · 2 junction cap. `lanes` 1–15. `direction`: 1 both · 2 forward, **0 = absent**, so an unrecognised value draws no centre line rather than a guessed one. `bus_lane`, `tram_tracks`: 0/1. `offside_kerb` (1024): 1 where `U = lanes` is a real kerb, **0 = not known to be** — on one half of a dual carriageway it is the middle of the road. `centre` (2048, 6 bits): where an opposed pair's two flows meet, in sixteenths of a lane beyond the centreline, `k − 1` steps, 0 = not half of a pair. `kerb_near` (131072, 2 bits) and `kerb_off` (524288, 2 bits) since `P3-13`: what kind of kerbside no-stopping line that side carries — 0 absent · 1 known unrestricted · 2 single · 3 double. ⚠️ a U-lane is `2·half_width / lanes` on the ground (5.12 m on a widened two-lane street), **not** `lane_width_m`. Max legal code **2,097,151** ≪ 2²⁴, so every code is exact in float32; consumers decode with `floor(x + 0.5)` first |
| `TEXCOORD_1.y` | The edge's **drawn length** in metres — after the junction trims, so it is the ribbon as drawn and not the published centreline. Junction caps carry `0.0`. Distance to the nearer end is `min(V, length − V)`, computed by the consumer |
| `COLOR_0.a` | **Where the kerbside restriction applies** (`P3-13`, `Q54`), 0 or 255, **per rail** — so it is per side of the road, because the two rails of the carriageway strip are the two kerbs. 255 everywhere else: kerbs and caps carry no extent. `TEXCOORD_1` says what kind of line; this says how far along it runs, and `surface.py` inserts a station pair 0.25 m either side of each boundary so the interpolation ramps over half a metre rather than over a city block. ⚠️ Not opacity. A consumer that hoists the sRGB conversion of `COLOR_0.rgb` into a `flat` varying — the shader does — must keep this one **non-flat** |
| Material name | **`road_markings`**, and the name is the contract, exactly as `city_facade` is on a tile. `tools/generated_scene_import.gd` dispatches on it and hands the surface `tuning/road_markings.tres` |

Nearside means left of travel, because Hong Kong drives on the left. The sign is not a free
convention: flip it and every asymmetric marking — a kerbside bus lane, a nearside double yellow —
lands on the wrong side of the road while the geometry still renders perfectly. Since `P3-13` the
sign decides which *rail* an `NSR` restriction is written to as well, so `etl/tests/test_kerbside.py`
asserts it against `surface.mitres` itself rather than against this paragraph.

⚠️ **The `TEXCOORD_1` codec constants are contract, not tuning** — mirrored as `MARKING_*` in
`etl/pipeline/surface.py`, `assets/shaders/road_markings.gdshader` and
`tools/verify_road_surface.gd`, the same standing as the tiles' survey codec, and this table is the
tiebreak. They do not belong in the city yaml: a codec has no per-city meaning.

⚠️ **`TEXCOORD_0` cannot be drawn on by itself, which is why the second channel exists.** The kerbs
run off **both** ends of the lane range — the nearside lip spans `U ∈ [−outside, 0]` and the offside
riser and lip sit at `[lanes, lanes + outside]`, where `outside = kerb_width_m / lane_width_m ≈
0.156` — so `fract(U)` on a kerb lip lands in `[0, 0.156]` and paints a lane line down it. And a
fragment at `U = 3.0` is the offside kerb on a three-lane road but an interior lane boundary on a
four-lane one; no arithmetic on `TEXCOORD_0` separates them. `class` and `lanes` answer both.

⚠️ **A cap's `(0, 0)` is an in-range value, not a sentinel.** `U = 0` *is* the nearside kerb line, so
a kerbside marking keyed on U alone floods every junction in the city. The cap says what it is in
`TEXCOORD_1` instead.

⚠️ **`TEXCOORD_1.y` is a length and deliberately not the distance-to-nearer-end the consumer wants.**
That distance is a V with its kink at the midpoint, and a strip interpolates linearly between its
stations — so on an edge Douglas–Peucker left with two, both stations *are* ends, both read zero, and
the whole street interpolates flat to zero. **204 of the region's 797 edges carry two stations**;
only edges lifted onto structure are resampled. The length is constant per edge, so it survives any
station spacing, and being constant it packs the way the tiles' survey channel does.

**Measured cost: +41,344 B of PCK** (40,702,784 → 40,744,128, one variable changed) against
**279,532 B** of raw VEC2 across 34,924 vertices — the pack compresses it by 86%. No triangle moved,
no draw call and no material was added.

**The `-col` suffix is load-bearing**, for the same reason as on tiles. `verify_road_surface.gd`
checks that it survived, because nothing on the Python side can see it.

**Opposed carriageway pairs are drawn as two overlapping ribbons and deliberately not merged**:
measured across the region's six pairs, the widening already closes every gap between them.

**Junctions are capped per elevation level.** The cap is the convex hull of the carriageway corners
each arm presents to the node, which is what makes it meet every arm across its full width. Arms at
different levels are never joined.

⚠️ **A cap overlaps its arms rather than abutting them** where they stop at different distances from
the node — 210 of the region's 1,398 trimmed ends, 6,051 m² of 52,985 m² of cap area. Invisible
while cap and carriageway are the same colour at the same height in one material; it becomes visible
the moment anything is drawn under it. The fix is a non-convex cap — the union boundary rather than
the hull — which is polygon clipping and is deliberately not built yet.

✅ **`P3-12` landed the markings shader this predicted, and the overlap did not bite** — because the
shader fades its markings out before the trim, which is what real lane lines do anyway. The depth
was then measured rather than guessed: derived per arm end from the published trims, the cap reaches
p90 **1.17 m**, p99 **3.62 m** and a worst **4.21 m** back over the ribbon beneath it, across 203 of
1,398 ends — reproducing this paragraph's 210 from a different direction. The shipped 6 m fade
clears every one of them. ⚠️ **The 6,051 m² is still there.** Anything drawn *on* a cap — a box
junction, a stop line — re-exposes it immediately and wants the non-convex cap first. `Q53`.

### `fares.json` — pickup and dropoff nodes

```json
{
  "schema_version": 1,
  "city_id": "hong_kong",
  "region_id": "wan_chai",
  "nodes": [
    {
      "id": "f_001",
      "pos": [420.0, 3.5, 610.0],
      "kind": "taxi_stand",
      "stand_category": "cross_harbour",
      "name": { "en": "Times Square", "zh": "時代廣場" },
      "nearest_edge": 42,
      "edge_t": 0.6382,
      "pickup": true,
      "dropoff": true
    }
  ]
}
```

`kind` ∈ `taxi_stand` | `pudo` | `poi`. `stand_category` is null unless `kind` is `taxi_stand`.

**`poi` has a producer since `P3-14`**: TD's 19 in-region tram stops. ⚠️ **`name` is null in both
languages for all of them, and that is the source** — Tram Stop Location publishes `OBJECTID`,
`STOP_ID` and a revision date and nothing else. `name_en`/`name_zh` are therefore **optional roles**
in a fare group; the alternatives were shipping `"99101"` as a place name or pointing the config at
a column that does not exist. ⚠️ **`pickup` and `dropoff` are both false**: a tram stop is somewhere
a *tram* stops, and `FareCategory` defaults both to true, so it must be said. No schema bump — `poi`
was always in this vocabulary and `pickup`/`dropoff` always carried the distinction.

**`pos` is the source position — the kerbside, not the carriageway.** 11 of Wan Chai's 29
**taxi-stand and PUDO** nodes lie outside even the widened road surface, because the published
points sit on the pavement and the ribbon is drawn from centrelines. ⚠️ **29 is the population that
measurement was taken over, not the region's fare-node count** — `P3-14`'s 19 tram stops took it to
48, and one of those is outside too. This is where the *passenger* stands. Where the *taxi* stops is
`nearest_edge` at `edge_t`, and that is derivable while the kerbside position would not be if it
were overwritten. `pos.y` comes off the snapped edge rather than the terrain.

⚠️ **The snap considers `elevation_level == 0` edges only**, so a point under a flyover takes the
street's height rather than the deck's. It did not until 2026-08-21, and one of `P3-14`'s tram stops
shipped 8.6 m in the air for it (`Q15`). No schema change — the fields' meanings are unaltered, and
a reader that kept its old interpretation is now reading a corrected value, not a different one.

**`edge_t`** is the fraction along that edge's plan length. Without it `nearest_edge` names a road
that can be 200 m long, and the game would have to redo the projection the ETL already did.

**`pickup` and `dropoff`** say what may happen at the node. Both are true at a taxi stand; a quarter
of Hong Kong's published pick-up/drop-off points are **drop-off only** (66 of 275 territory-wide, 4
of the region's 15), and letting a player hail a fare at one would be wrong in a way a local would
notice.

### `tram.glb` — the published tramway (`P3-14`)

Two rails and a bed per track, at the position iB1000's `CartoTransLine` tramway code publishes.
One primitive, one material named `tramway`, one draw call, and **no collider**.

⚠️ **`city.json`'s `tramway` key is optional and may be `null`.** A city whose estate publishes no
tramway ships none, and that is the honest answer rather than a missing file. It is deliberately not
in `DOCUMENT_KEYS`, which `REQUIRED_KEYS` and `shipped()` both treat as always-present.

⚠️ **This is geometry rather than a marking, and that is measured, not stylistic.** `roads.glb`
carries a `tram_tracks` bit and always has; the rails are still not drawn from it, because they are
not on that ribbon. 80 of the 86 flagged edges are one-way, so the reserve runs *between* two opposed
carriageways — **18.8%** of cross-sections have both tracks on the drawn surface, **1.5%** on
Hennessy, and the outer rail sits a median **3.26 m** past the drawn kerb. `Q58`.

⚠️ **It must not collide.** It lies on ground solid since `P3-10`, and a 30 mm rail as collision
geometry is a kerb with no visible cause — landing in the population `carriageway_occupancy.py`
already fails on. The whole guard is the absence of a `-col` suffix in one string, so
`verify_tramway.gd` fails on *any* collider: the inverse of every other asset here.

| Channel | Carries |
|---|---|
| `COLOR_0.rgb` | The material's colour — `steel_rail` or `concrete_sooty` from `materials:`. Constant per strip, which is what lets the shader convert to linear `flat` |
| `TEXCOORD_0` | `x` a fraction **across** the strip (0 and 1 on the two edges), `y` metres along. `x` is what shades the polished rail head |
| `TEXCOORD_1` | `x` the class — **0 bed, 1 rail**; `y` metres along, again |

⚠️ **`TEXCOORD_1.y` duplicates `TEXCOORD_0.y` on purpose**, the same shape `roads.glb` uses. Godot's
16-bit vertex compression applies to a mesh whose attributes fit the representable range: `roads.glb`
escapes it because its marking codes reach 2,097,151, and this mesh does not escape it. A contract
read off `TEXCOORD_0` is read off a quantised copy — the first `verify_tramway.gd` reported the
tramway starting at **-0.009 m** against an exact float32 zero.

⚠️ **`tramway.json` publishes the join's own grade, and the useful field is not the obvious one.**
`off_gauge_stations` — the stations the trim threw away — plus `pairs` against `tracks` is what sees
a pair joined across two tracks. `drawn_gauge_m` is bounded by `pair_tolerance_m` by construction and
cannot read outside it. `Q58`.

⚠️ **The class is shipped rather than derived.** Inferring it from strip width works today and
inverts the day `rail_width_m` and `bed_width_m` converge; inferring it from vertex colour makes the
`materials:` table load-bearing for shading rather than for colour.

### `arrows.glb` — the published turn arrows (`P3-15`, `P5-4`)

One flat glyph per marking symbol TD publishes, laid `lift_m` above the carriageway. One material
named `arrows`, and **no collider**.

🔴 **Since `P5-4` (`Q115`) the file is a LIBRARY, and the city is `arrows_placements.json`** — on
`signs.glb`'s terms, with one mesh per `RM` code (**7 meshes / 42 triangles** for Wan Chai against
the 3,246 the merged build carried), each drawn flat at the origin with its nose north, and stood
**747** times at the symbol's heading as `rot_y_deg` plus a **`pitch_deg`** between the deck heights
under its tail and its nose. ⚠️ **The glyph is rigid where the merged build sheared it** — the
old draw held every vertex at its plan position and ramped the height along the shaft, which is not
a rotation and has no transform — so the stood library is *not* the merged mesh to the millimetre:
row for row the two differ by **p50 0.06 mm, p99 3.8 mm, max 18 mm** at the steepest arrow (7.69°
on WAN CHAI ROAD), the plan footprint shortening by `length × (1 − cos pitch)`. The rigid form is
the faithful one: TD's `LENGTH` is the length painted *on* the road. `arrows.json`'s `triangles`,
`vertices` and `aabb` still describe what is drawn; `library_*`, `placements*` and `pitch_deg`
(p50 0.27°, p99 4.05°, max 7.69°) are the new keys, and `arrows.json` is schema **2**, `city.json`
**25**. `inverted` is asked of the **stood** copies, not of the library, because the pitch is a
second rotation and a stand pitched past vertical faces the ground while its glyph faces the sky —
reachable, which `Q72` requires of a counter. `tools/paint_clearance.py` expands the library under
its placements and reproduces its table to within one triangle (in-carriageway 1.48 → 1.45%).

| | |
|---|---|
| Primitives | one per library mesh — one per `RM` code (`P5-4`); before it, one for the whole region's arrows |
| Attributes | `POSITION` and `NORMAL` only — **no `COLOR_0`, no `TEXCOORD_0`, no `TEXCOORD_1`**, no texture |

⚠️ **`city.json`'s `arrows` key is optional and may be `null`**, on the same terms as `tramway`, with
one extra state: it is also null where the block is declared and **every** symbol failed the join,
because the stage names its asset from what it drew rather than from a constant.

⚠️ **No `COLOR_0`, and the absence is a decision rather than an omission.** An arrow is the same
paint as a lane divider, and `Q53` deliberately put the marking colours in
`game/tuning/road_markings.tres` rather than in `hong_kong.yaml`'s `materials:` table — outside
`Q33`'s exposure rule, because paint is not cladding. So the arrow's white lives in
`game/tuning/arrows.tres` beside it, and `MeshContract.check_surface` takes an
`expect_vertex_colours` parameter so the exception is stated at its one call site rather than by
skipping the check.

⚠️ **There is no codec here, and that is the point of the stage.** `roads.glb` needs nine packed
fields because a fragment there must reconstruct which lane it is in; every vertex of this mesh is
already where `pipeline/arrows.py` decided it goes. What that buys is immunity to the two things that
made an arrow undrawable on the ribbon: `road_markings.tres`'s 6 m junction fade, which blanks
exactly the approach an arrow is about, and the 6,051 m² cap overlap, which anything drawn *on* a cap
re-exposes.

⚠️ **The first draft shipped a `TEXCOORD_0` of glyph-local metres that nothing sampled**, on the
reasoning that a later shader might want it. That is what `Q54` found `COLOR_0.a` had been doing —
broadcasting an unread 255 down the whole road mesh — and it cost **59,300 B** of a 257 KB asset. A
channel earns its place when something reads it.

⚠️ **Winding, not the normal attribute, decides whether this is visible** — `marking_paint.gdshader` is
`cull_back`. `arrows.json` publishes `inverted` and it must be **0**. ⚠️ **Godot winds front faces
clockwise and glTF winds them counter-clockwise**, so the importer reverses every index triple and
the engine-side and ETL-side tests of the same expression have **opposite signs**. Both are right
about their own side; `Q59` records how that was established, and against which two shipped meshes.

⚠️ **`arrows.json` publishes residual distributions at p90/p99/max, not p10/p50/p90.** Every one of
them is a residual whose *tail* is the finding — `axis_residual_deg` is where a match to the wrong
road goes — and a median near zero is also what a wholly broken join looks like. `Q58`'s
`drawn_gauge_m` lesson, applied before rather than after.

### `boxjunctions.glb` — the published yellow box junctions (`P3-18`)

Border and cross-hatch per surveyed `DTAD_YL_BOX_POLY` polygon, the hatch laid `lift_m` above the
junction and the border `border_lift_m` above that (both below the arrows — they paint over boxes,
as the street does). One primitive, one material named `boxjunctions`, one draw call, and
**no collider**.

| | |
|---|---|
| Attributes | `POSITION` and `NORMAL` only — no `COLOR_0`, no UVs, no texture |

⚠️ **`city.json`'s `boxjunctions` key is optional and may be `null`**, on exactly `arrows`' terms,
including the every-box-failed-the-join state.

⚠️ **The engine re-quantises every imported mesh to a 16-bit lattice over its own AABB** —
`span / 65535`, ~17 mm for a region-spanning mesh — and a triangle thinner than that pitch can come
back with its winding flipped, which `cull_back` culls. This stage measured it (217 flipped
triangles that did not exist in the shipped GLB) and ships nothing thinner than two lattice cells;
`boxjunctions.json` publishes `slivers_dropped` and `import_quantum_m`. Any future stage shipping
thin geometry inherits the same constraint. `P3-18`.

⚠️ Winding and the p90/p99/max reporting follow `arrows.glb`'s paragraphs above, unchanged.

### `roadmarks.glb` — the published stop and give-way lines (`P3-23`)

`RM1011` STOP LINE, `RM1012` STOP LINES and `RM1013` GIVE WAY LINES from `DTAD_RD_MARK_LINE`, drawn
at their surveyed extents and laid `lift_m` above the carriageway. One primitive, one material named
`roadmarks`, one draw call, and **no collider** — a stop line crosses every approach in the city, so
a collider would be a 16 mm step the player mounts at every junction while braking.

| | |
|---|---|
| Attributes | `POSITION` and `NORMAL` only — no `COLOR_0`, no UVs, no texture |

**Its own mesh for `arrows.glb`'s reason, in the stronger form.** The 6 m junction fade in
`road_markings.tres` "blanks exactly the approach an arrow is about", and the 6,051 m² cap overlap
re-exposes anything drawn on a cap. A stop line does not merely approach the junction — it *is* the
junction's edge, drawn on the cap, inside the fade. Painted on the ribbon it would be invisible by
construction.

🔴 **The host edge is picked by transversality, not proximity, and this is the one place a stage
here departs from that.** `arrows.py` and `boxjunctions.py` both take the nearest level-0 edge and
both are right to; a stop line sits at a junction *mouth*, so the nearest centreline is usually the
road it is parallel to. Measured, the two joins disagree on **44%** of stop lines and **43%** of
give-way lines. A wrong host does not move the paint — the extent is published — it moves the
height. `roadmarks.json` publishes `host_disagreement` as the counter that can see this regress;
`axis_residual_deg` cannot, because it grades a rule that optimises what it reports. `Q69`.

⚠️ **`lift_m` is 0.016, deliberately above `arrows`' 0.015.** A legibility order rather than a fact
about paint: the bar is the boundary the player must not cross, the arrow an instruction already
read. A clear millimetre, not a hair — the engine re-quantises Y on import too.

⚠️ **`city.json`'s `roadmarks` key is optional and may be `null`**, on exactly `boxjunctions`'
terms, including the every-marking-failed-the-join state.

⚠️ The import-lattice constraint, the winding rule and the p90/p99/max reporting follow
`boxjunctions.glb` and `arrows.glb` above, unchanged.

### `lamps.glb` — the published lamp posts (`P3-26`, `Q82`, `P5-3`)

A 9 m hexagonal column standing `outset_m` outside the drawn carriageway edge, a bracket arm sloping
`arm_reach_m` out and `arm_drop_m` down over the carriageway, and a lantern box centred on the far
end — one per `LPO` point in iB1000's `UtilityPoint` that clears the road. **No collider**, on
`signs.glb`'s terms: 892 columns is 892 collision bodies and `P2-6` has not measured a frame on the
device floor. Breakaway is a `B3` question.

🔴 **Since `P5-3` (`Q115`) the file is a LIBRARY, and the city is `lamps_placements.json`** — on
`signs.glb`'s terms below, with one mesh per drawn *kind* (`LPO`: **1 mesh, 40 triangles** for Wan
Chai against the 35,680 the merged build carried), drawn at the origin with its arm pointing north
and stood at the compass bearing of the arm each column was given. The column's prism ring is seeded
from that arm rather than from world `X`, so the stood library *is* the column drawn in place and
not a copy 15° of ring away from it; `tests/test_lamps.py` pins the two equal. `lamps.json`'s
`triangles`, `vertices` and `aabb` still describe what is drawn and read the merged build's own
numbers; `library_*`, `placements` and `placements_document` are the new keys, and `lamps.json`
is schema **2**, `city.json` **24**. The entry shape, the rounding, the drawn totals and the
document writer are `pipeline/placements.py`'s, shared with the signs so a third layer cannot drift
from the first two; the rotation is still `gltf.placed_positions`' one statement.

| | |
|---|---|
| Primitives | one per library mesh — one per drawn kind (`P5-3`); before it, one for the whole region's lamps |
| Attributes | `POSITION`, `NORMAL`, `COLOR_0`; no `TEXCOORD_0`, no texture |
| `COLOR_0` | One colour, from `hong_kong.yaml`'s `materials:` table via `lamps.column_material`. ⚠️ **Carried although the layer is monochrome**, because `signs.gdshader` reads it and a mesh not supplying it renders white |
| Material name | `lamps` → `res://tuning/lamps.tres`, the third `.tres` on `signs.gdshader` |
| Collider | none |

✅ **The one layer here whose vocabulary the publisher DEFINES.** `UTILITYPOINTTYPE` carries a
coded-value domain inside the geodatabase (`LPO - Lamp post`), where `railings.classes` and
`signals.head_prefixes` are whitelists read off code strings with nothing published behind them.
`lamps.json` publishes `refused_by_kind` over the rest of the domain regardless.

🔴 **The position is registered rather than read, and the guarantee that no column stands in the
drawn carriageway comes from TWO refusals.** `_register` pushes a column outward — `Q78`'s clamp, so
one already clear keeps the surveyed point — to `half_width + outset_m` of its **host** edge, or
refuses past `max_shift_m`. That says nothing about the edge next door, so the placed point is
re-snapped against **every** edge and refused where it lands inside any drawn ribbon: junction
mouths and dual carriageways, where 1.6x ribbons overlap and no footway survives. `lamps.json`
publishes `min_kerb_clearance_m` as the invariant.

⚠️ **The arm direction is derived from the kerb side and cannot be graded against anything published**
(`Q62`). What ships instead of a counter over it is `lantern_overhang_m` — a counter over the
direction itself would read 0 by construction, which is `Q72`'s tautology.

⚠️ **`UtilityPoint` publishes no elevation**, so unlike every sibling stage there is nothing to
refuse a flyover lamp on and one is drawn on the street underneath. `nearest_is_elevated` reports how
often that is possible.

### `railings.glb` — the published street furniture (`P3-19`, `Q61`, `P5-5`)

A vertical strip `height_m` tall standing `outset_m` outside the drawn carriageway edge, one quad
per `station_m`, for every run of `DTAD_RAILING_LINE` this city draws — and **no collider**, which
is a *design* decision rather than a rendering one: `GAME_DESIGN.md` lists railings under
"deliberately diverge on — omit or make breakable", because Hong Kong's streets faithfully railed
are a traffic simulator with no room to be reckless. Breakaway is a `B3` question.

⚠️ **One primitive per *class*, not one per file, since `Q61`.** The layer publishes more than one
kind of object and the stage draws each as its own mesh, named for its class and carrying a material
of the same name. Three classes in Hong Kong — `railings`, `bollards`, `barriers` — so three
primitives and three draw calls. A city's classes are `hong_kong.yaml`'s `railings.classes` table
and nothing here fixes the list; what is fixed is that **a class id is the mesh name and the glTF
material name at once**, which is the channel `tools/generated_scene_import.gd` dispatches on.

🔴 **Since `P5-5` (`Q115`) the file is a LIBRARY, and the city is `railings_placements.json`** — one
unit panel per class, `panel_m` wide (2.0 / 1.5 / 3.0 m, each the post pitch in that class's `.tres`
and bound to it by test), drawn at the origin along north with the road to its east, and stood
**5,035** times (4,425 / 304 / 306) along every visible piece of every run: `floor(length / panel_m
+ 0.5)` rigid copies centred on the piece, yawed to the chord under each and pitched to the deck.
The join, the registration, the buried-kerb cut and the two `Q112` repairs are untouched; what
tiling costs is **published**: `metres_snapped` (228.89 / 21.47 / 34.08 m — the run ends moved to
a panel multiple, never a stretched panel), `joints` with the far-face wedge each opens as
`joint_gap_m` (max 59 mm), and `bends` above `bend_report_deg` (79 / 2 / 12). `drawn_m` is the
tiled metres — 8,850.0 against the strip's 8,827.69 — and `railings.json` is schema **3**,
`city.json` **26**. `facing_away` is asked of the panel, because a stand turns winding and normal
together. `railings.glb` is **1,375,964 → 4,172 B**; the document is 1,067,116 B pretty-printed.

| | |
|---|---|
| Primitives | one library mesh per class — `railings`, `bollards`, `barriers` in this region — each drawn as one `MultiMesh` (`P5-5`); before it, one merged primitive per class |
| Attributes | `POSITION`, `NORMAL`, `TEXCOORD_0`; no `COLOR_0`, no texture |
| `TEXCOORD_0.x` | Metres **along the panel**, `0` to `panel_m`, so the shader's post stands on every joint (`P5-5`). Before it, the fence line's own arc length along the run — not the centreline's, which differs on a bend by the ratio of their radii — restarting at zero for each run |
| `TEXCOORD_0.y` | Metres above the **ribbon deck**, so `0.0` is the ground line wherever the run stands: `-base_sink_m` at the buried foot, `+height_m` at the top |

⚠️ **`TEXCOORD_0` is not a texture coordinate** — nothing samples an image, and `mesh_contract.gd`
walks every shader uniform and would refuse the bundle if anything did. It is the same kind of
shader payload a tile's storey height travels in (`P3-7`), and it is what `railings.gdshader` cuts
the balusters, posts and rails out of. ⚠️ **The classes share that one shader** and differ only in
the mask numbers in their `.tres`, so a class handed the wrong material is a picket fence standing
where a bollard should be; `verify_railings.gd` checks the dispatch per class.

⚠️ **`city.json`'s `railings` key is optional and may be `null`**, on exactly `boxjunctions`' terms,
including the nothing-survived-the-join state.

⚠️ **`railings.gdshader` is `cull_disabled`, and it is the only generated mesh here that is.** A
fence is one quad thick and the car passes it on both sides, so back-face culling would make half of
them invisible — `Q58`'s failure-to-nothing in a new place, and the mesh would be byte-identical.
`verify_railings.gd` reads the render mode out of the shader's own source because that is the only
channel Godot offers.

⚠️ **So the winding decides *lighting* rather than visibility.** Every quad is wound to look at the
carriageway, `railings.json` publishes `facing_away` **per class**, and each must be 0: a flipped
quad still draws, lit from the wrong hemisphere, which reads as a black panel rather than as a
missing one.

⚠️ **`railings.json` is `RAILINGS_MANIFEST_SCHEMA` 3 and carries no top-level `drawn_m`.** Every
counter below the join lives under `classes[<id>]`; the total was **removed rather than broadened**
at schema 2, because at schema 1 it meant railing metres and at schema 2 it would mean fence plus
bollard plus vehicle barrier — a reader keeping the old meaning would be wrong, which is hard rule
5's own bar. Schema 3 (`P5-5`) makes a class's `drawn_m` the tiled metres and adds `panels`,
`metres_snapped`, `joints`, `joint_gap_m`, `bends` and the `library_*` / `placements*` keys. The
read counters above the join stay shared: it is one read of one layer.

⚠️ **The position is registered, not read** — the one place in the bundle where a *published extent*
is moved. `Q59`'s widening puts the drawn kerb a median 0.9 m past the surveyed railing, so **67.9%
of the region's railing metres fall inside the drawn ribbon** and drawing them where surveyed is a
picket fence down the middle of the road. The longitudinal extent is read and never stretched; the
lateral offset is a rigid move, bounded by `max_shift_m` and priced by `shift_m`. `Q60`.

⚠️ **`roadsurface.json` gained `carriageway[].kerb_hidden_m` for this stage** (`SURFACE_MANIFEST_
SCHEMA` 4 → 5) — the ribbon-metre ranges where a side draws no kerb because a neighbour covers it.
Only `surface.py` can know it, and without it 11.1% of the region's railings stand in merged tarmac.
An intermediate, like `trim_m`; the game reads neither.

⚠️ **And `caps` for the markings** (`SURFACE_MANIFEST_SCHEMA` 5 → 6, `Q92`) — each junction cap's
hull ring in x/y/z, which with the ribbon heights is the whole of the drawn surface. Only
`surface.py` can know it, for `kerb_hidden_m`'s reason restated: the ring depends on where every
arriving ribbon actually ended. `surface.DrawnSurface` is the reader, and without it a marking guesses
the road's height and sinks into it.

### `signs.glb` — the published traffic signs (`P3-16`)

A plate per whitelisted sign, standing on the pole `DTAD_TS_POLE_PT` surveyed, and **no collider** —
which is a *budget* decision rather than a design one, unlike the railings above: a sign post is a
real obstacle a real car would hit, and 699 of them is 699 collision bodies before `P2-6` has
measured a frame on the device floor. Breakaway posts are a `B3` question.

🔴 **The position comes from the pole, not from the sign.** `DTAD_TS_ABV_PT` is the publisher's
*"Traffic sign abbreviation point"* — a drawing label, a median **2.63 m** from the pole and never on
it — so it is read as data and the pole supplies the geometry, joined through `GG_NAME`. And
🔴 **nothing publishes which way a sign faces**: the spec calls `ANGLE` the *Ustn* symbol-cell
rotation, so the facing is **derived** from the host edge, the kerb side and drive-on-left. `Q62`
records what that still owes.

🔴 **Since `P5-2` (`Q115`) the file is a LIBRARY, and the city is `signs_placements.json`.** One
mesh per drawn face variant — `TS115`, a mirrored deviation board as `TS414_mirrored` because a
mirror cannot be a transform under `cull_back` — plus a unit `pole` and one `signs_text_<code>`
quad per lettered code; **24 meshes, 455 triangles** for Wan Chai against the 20,234 the merged
build carried. Each is drawn at the origin facing north, and a placement is `landmarks.json`'s
transform shape (`pos`, a compass `rot_y_deg`) plus an optional `scale`, which the pole uses to
stand at its own height. `layer_preview.gd` draws one `MultiMesh` per library mesh — **24 draw
calls where there were 2**, and on the throttle route **+35** once the shadow passes are counted —
and `verify_signs.gd` grades the library per mesh and the join in both directions: every entry
names a mesh, every mesh is stood, and a negative scale is refused as no transform at all.
`signs.json`'s `triangles`, `vertices` and `aabb` still describe what is drawn, and read the
merged build's own numbers; `library_*` and `placements` are the new keys.

| | |
|---|---|
| Primitives | one per library mesh — a face variant, the pole, a lettering quad per lettered code (`P5-2`); before it, one for the whole region's signage |
| Attributes | `POSITION`, `NORMAL`, `COLOR_0`; no `TEXCOORD_*`, no texture |
| `COLOR_0` | The plate livery as **sRGB bytes**, straight from `hong_kong.yaml`'s `signs.colours` |

⚠️ **This is the only generated road-furniture mesh that carries `COLOR_0`, and the departure is the
decision.** `arrows.glb` and `boxjunctions.glb` are one paint each, so `Q53` put their colour in
their `.tres`. A sign plate is four colours inside one draw call, so the colour has to ride the
vertex — which makes `colour.gdshaderinc`'s `vertex_srgb_to_linear` mandatory in
`signs.gdshader`, exactly as `marking_paint.gdshader` warned in advance. ⚠️ It is also the one exemption to
`Q33`'s palette-exposure rule; `test_config.py` argues it.

⚠️ **`signs.gdshader` is `cull_back`**, inverting the neighbour above: a fence has no back and a
sign does, so every plate is drawn twice — face forward, grey reverse. `signs.json` publishes
`facing_away` and it must be **0**; the first build read **3,200**, every pole triangle in the
region, with everything else correct.

⚠️ **`city.json`'s `signs` key is optional and may be `null`**, on `boxjunctions`' terms — and null
is a more ordinary answer here than for any other layer, because a region whose signs are all text
plates draws none and is right to.

🔴 **The facing is derived per POST, and then turned per PLATE** (`Q72`). `_facing_from_side` reads
the host-edge tangent and the kerb side to point a post at the traffic it addresses; almost every
face agrees with it. The NO ENTRY family does not — it stands at the mouth a driver must *not* enter
by, so it addresses traffic coming the other way and is turned 180° from its own post by
`_plate_facing_deg`. ⚠️ **Without that step back-to-back plates are unrepresentable**, and 74 of Wan
Chai's 503 posts carry a NO ENTRY beside a GIVE WAY, a mandatory disc or a ONE WAY plate.
⚠️ **This read 82, and 82 was never this measurement** — re-measured 2026-08-24 at **74**, whose
combination breakdown reproduces `Q72`'s own (`TS102`+`TS115` x22, `TS102`+`TS107`+`TS115` x19,
`TS115`+`TS182` x8) exactly. `TS101` does not move it: 6 STOP plates share a post, none with a
NO ENTRY. Which faces
turn is **config** (`SignFace.faces_against_traffic`), not code. `signs.json` publishes
`plates_turned` and `no_entry_against_flow`; the latter must be 0 and is a regression guard rather
than proof — nothing published grades a facing, which is `Q62`.

🔴 **The lettering's atlas ships as `signs_text.png`, beside the asset and named by the manifest**
(`Q70`, schema 16 → 17). It used to ride inside `signs.glb` as an embedded buffer view, and the
reason it no longer does is not glTF's, it is Godot's: `gltf/embedded_image_handling` defaults to
*Extract Textures*, so the importer unpacked it into `signs_0.png` — a file in
`game/assets/generated/` that `city.json` had never heard of, in a directory where the manifest
names everything else. `sync_generated.sh` deletes exactly that, so it did, on every run, and
`verify_signs.gd` failed until someone forced a re-import by hand. An external URI is not extracted.

⚠️ **Nothing in the game loads the atlas by path, and it is named anyway.** It reaches the renderer
through `signs.glb`, which references it, and `tools/generated_scene_import.gd` deliberately reads
the texture the importer resolved rather than hard-coding a second name for the same file. The
manifest key exists for `shipped()` — which is to say, for the sweep. ⚠️ **The key is optional and
nullable twice over**: null for every region that ships no signs, *and* for one whose drawn faces
carry no lettering.

⚠️ **`signs.json`'s `bytes` is `signs.glb` alone and no longer covers the image**; the atlas is
`text_atlas_bytes` beside it. Two numbers where there was one, on purpose — they are added up
deliberately or not at all.

### `signals.glb` — the published traffic signal heads (`P3-17`, **not shipped**)

🚫 **Dropped from the bundle by `Q77`.** `hong_kong.yaml` declares no `signals:` block, so the key
is `null` and no asset ships. Everything below describes what the stage still builds if a city
declares one — the code, the material, the verify tool and the preview node all remain. The reason
is not a defect: an unlit head asserts a signal out of service, and a lit one cannot be derived
honestly from what this repo knows. `Q77` has the measurements.

One head on one post per signal assembly, drawn where TD surveyed it and registered onto the drawn
kerb, and **no collider** — the same budget decision the signs record, with one extra edge: a signal
post stands at a junction mouth, exactly where the player is braking and turning, so this is the
layer whose colliders would be felt most. `B3` revisits it.

🔴 **The code on a feature is a GATE, never a look.** `DTAD_TRAFFIC_LIGHT_PT.REFNAME` has no
published domain — no Index Plan sheet defines it, the fgdb specification gives it eight characters
of untyped text, and `signCatalogue.json` is `TS`-only — so all 33 admitted codes draw the same
head, and `signals.json` publishes `drawn_by_code` and `refused_by_code` over the whole 46-code
vocabulary because that is the only thing that can grade a spelling rule (`Q76`).

🔴 **One head stands for a whole assembly, and the count of features is not the count of heads.**
This layer publishes no `GG_NAME`; what it publishes is coincidence — 470 of 913 points within
0.05 m of another — and those are the parts of one installation rather than heads to stack. The
first build stacked them and drew **8.53 m** masts, with both partitions closed, `facing_away` 0 and
`check.sh` green. `signals.json`'s `drawn` counts **features** and `posts_drawn` counts **heads**;
`assembly_size` is the collapse between them.

⚠️ **`ANGLE` is not a facing and is consumed by nothing.** Re-measured on this layer rather than
inherited from `P3-16`: p50 44.3° off the host edge axis, 21.3% along / 19.3% across against 22.2%
for a uniform distribution. The facing is derived from the host edge and the kerb side, and is
**ungraded** — there is no published subset to check it against (`Q62`), so the evidence is an A/B
render.

⚠️ **It shares `signs.gdshader`**, on `Q61`/`Q71`'s rule that a layer is a parameterisation rather
than a shader — so a change to that shader is a change to **two** layers, and `check.sh` exits 0 on
one that fails to compile. `verify_signals.gd` checks the dispatch by `resource_path`, because
`check_shader_source` would pass a head handed `signs.tres`. ⚠️ `sheeting_glow` is **0** here: a
signal lens with its lamp off is dark glass, and any glow makes an unlit aspect read as a lit one —
an instruction this game deliberately does not give.

### `landmarks.json` — hero building placement

```json
{
  "schema_version": 2,
  "city_id": "hong_kong",
  "region_id": "wan_chai",
  "landmarks": [
    {
      "id": "hkcec",
      "asset": "res://assets/generated/landmarks/hkcec.glb",
      "transform": { "pos": [102.5, 4.0, 84.0], "rot_y_deg": 0.0 },
      "name": { "en": "Convention Centre", "zh": "會展" },
      "replaces_source_ids": ["B358761603301063"],
      "excluded_bounds": [[8.37, 3.99, -73.57], [209.63, 71.92, 275.45]],
      "triangle_budget": 120000
    }
  ]
}
```

Written by `export.py` from the city config's `landmarks:` block (`P3-6`) — ~2 entries derived
from config plus one CRS conversion, which is why the *document* is not a stage of its own. The
manifest names it under the `landmarks` key; `game/scripts/city/landmarks.gd` places the models,
and `generated_landmarks.gd` is the locator. The mesh-sourced *models* do have a stage:
`pipeline/landmarks.py` extracts each `source_paint` landmark's own source mesh, slices it at the
ribbon elevations so vertex colour can hold a crisp band, repaints it, and writes it into the out
tree — the manifest lists those files under `landmark_assets`, `shipped()` carries them, and
`sync_generated.sh` copies them like any tile.

**`triangle_budget`** (schema 2) is the ceiling `verify_landmarks.gd` holds the placed model to —
per entry, because the authored heroes budget 8k where a mesh-sourced hero pins its measured
count. Schema 1 → 2 was bumped for the asset set, not the added field: a v1 document names a
committed `assets/authored/landmarks/hkcec.glb` that no longer exists, and a stale bundle would
draw a hole where the hero stands — the same "version gates the whole asset set" argument as
`city.json` 7 → 8.

`replaces_source_ids` tells the ETL to **exclude** those buildings from the generated tile mesh so
the hand-made model doesn't z-fight with the extruded one. Its entries are **stems** — the
cross-dataset building key `DATA_SOURCES.md` establishes, the same keying as the façade survey and
`P3-7a`'s override table. `export.py --check` holds the set equal, in both directions, to what the
building stage actually dropped.

**`excluded_bounds`** is the game-space AABB union of the meshes each entry excluded, recorded by
`buildings.py` at exclusion time — the only moment a mesh still has an identity, since `merge`
erases it. `verify_landmarks.gd` probes the shipped tier-0 tiles against its interior core, which
is the in-engine half of "source geometry excluded"; `null` means no stem matched, which
validation refuses.

**`transform.pos`** is game-space metres with `y` the building's base elevation; models are
authored footprint-centred with `y = 0` at the base. **`rot_y_deg` is a compass bearing** — 0 at
north, rising eastward, the `CityManifest.bearing_deg` convention — and the one conversion to a
Godot rotation lives in `generated_landmarks.gd::placement_of` (game north is -Z, so a bearing is
a negative rotation about +Y).

The `.glb` assets come in two kinds, and the licence is what separates them (`LICENSING.md`). An
*authored* hero (Central Plaza) is **committed** under `game/assets/authored/landmarks/`
(CC BY-SA 4.0, generated by `tools/make_landmark.py`); it is not build output, so `shipped()`
never lists it and `sync_generated.sh` never touches it. A *mesh-sourced* hero (HKCEC) is the
government's own building mesh repainted by `pipeline/landmarks.py` — generated city data under
government terms, gitignored, shipped from `game/assets/generated/landmarks/`, and never
committed. The config's `source_paint` block is what declares the second kind, and it forces
`rot_y_deg: 0.0` because the extracted mesh keeps its source orientation.

### Not part of the contract

`buildings.json` and `roadsurface.json` are ETL intermediates written beside their stage outputs, so
that each stage stays independently runnable. `city.json` is the versioned interface and `export.py`
is what writes it. **Nothing in the game should read either**, and `sync_generated.sh` keeps them out
of the bundle by copying only what the manifest names.

---

## Coordinates

| Item | Value |
|---|---|
| Source CRS | HK1980 Grid, **EPSG:2326** |
| Vertical datum | Hong Kong Principal Datum |
| Game space | Local ENU metres, Y-up, **origin at region NW corner** |

```
game_x =  (easting   - origin_easting)
game_y =  (elevation - origin_elevation)
game_z = -(northing  - origin_northing)
```

**`etl/pipeline/hongkong.py` is the only module permitted to state EPSG:2326** (`Q100`); `crs.py`
holds the arithmetic and takes the codes as arguments, so the conversion stays testable against any
pair. Everything else reads the CRS through the config object.

**The negation on `z` is forced, not chosen.** Godot is right-handed and Y-up, so rotating `+X` by
90° counter-clockwise about `+Y` lands on `−Z`: if east is `+X` then north must be `−Z`. Flip it and
the city is mirrored — a plausible-looking map no local recognises.

**The origin sits at the north-west corner.** Because the Z sign is forced, anchoring at the
*northern* edge is the only way to keep the region in the positive quadrant: X runs east from 0 and Z
runs south from 0, so tile indices are natural numbers with row 0 at the north, as in a raster.
Origin easting is floored and origin northing is **ceiled** — rounding outward keeps every offset
inside the region non-negative, and rounding at all stops a sixth-decimal difference between PROJ
releases renumbering every tile.

⚠️ **Non-negativity is a property of the region, not of the source data — so clipping to the region
bbox is a requirement of this contract, not an optimisation.** `fetch.py` deliberately downloads
every map sheet that *intersects* the region, so the building data on disk extends past all four
edges. Any vertex north or west of the region still yields a negative coordinate and a negative tile
index. Whatever consumes the sheets must clip before indexing.

### Two frames, and why

Each region's geometry is authored in its **own** local frame, origin at its own NW corner. That is
what keeps the numbers the player interacts with small: Wan Chai spans 0–1650 m, where float32
resolves to well under a millimetre.

`city_offset` is the translation from a region's local frame into a **city-wide** frame shared by
every region — anchored on the city's declared `bounds`, not on any region:

```
city_space = region_local + city_offset
```

**A region loaded on its own can ignore `city_offset` entirely.** It exists so two regions can be
placed correctly relative to each other without either giving up its local precision. Anchoring
everything in city space would put Wan Chai ~38 km from the origin, where float32 spacing is ~3.9 mm
— invisible on a building and awkward on a vehicle whose suspension sag is 50 mm.

⚠️ **A city's `bounds` must not change once a `city.json` has shipped.** Every region's `city_offset`
is measured from them, so moving them silently relocates every region already published. They are
declared rather than derived from the regions that exist, for the same reason. `config.py` checks
every region lies inside them.

---

## Runtime systems

| System | Responsibility | Status |
|---|---|---|
| `CityStreamer` | Load/unload tile meshes by camera distance; owns the LOD tier | ✅ `P2-1` |
| `Landmarks` | Place the authored heroes from `landmarks.json`; always resident, no LOD | ✅ `P3-6` |
| `RoadGraph` | Runtime queries over `roadgraph.json` — nearest edge, lane centre, routing | ✅ `P2-2` |
| `RoadSpawn` | Where a car starts, resolved from a fare node through `RoadGraph`, and what it is standing in (`Q52`) | ✅ `P2-3` |
| `VehicleController` | Player car. `VehicleBody3D` + arcade overrides — steering rate, top-speed taper, coast drag, drift, collision response, auto-right | ✅ `P0-5`/`P2-3`/`Q50` |
| `InputRouter` | Abstracts touch / gamepad / keyboard into one action set | 🟡 keyboard + gamepad; `P2-4` |
| `DebugHud` | Every dev readout, behind `F3` | ✅ |
| `TrafficSystem` | AI vehicles following road-graph splines; trams as scripted blockers | ⬜ `P3-3` |
| `tram.glb` | The published tramway, drawn where iB1000 prints it — **not** a marking on the ribbon (`Q58`). One primitive, one draw call, **no collider** | ✅ `P3-14` |
| `arrows.glb` | The published turn arrows, registered into the lane the ribbon actually has — **not** paint on the ribbon, because the junction fade blanks the approach they are about (`Q59`). **A library since `P5-4`** — one flat glyph per `RM` code, stood by `arrows_placements.json` — one draw call per library mesh, **no collider** | ✅ `P3-15`, `P5-4` |
| `arrows_placements.json` | Where the arrow library stands: one entry per drawn arrow, in `landmarks.json`'s transform shape plus a `pitch_deg` between the deck heights under its tail and its nose. ⚠️ Nothing else — the first build wrote the host edge and lane beside it and nothing read them, 14.6% of the document (`Q54`). Written beside `arrows.glb` and null on its terms | ✅ `P5-4` |
| `boxjunctions.glb` | The published yellow box junctions, drawn at the extents the estate surveyed and lifted under the arrows that paint over them. Ships nothing thinner than the import lattice. One primitive, one draw call, **no collider** | ✅ `P3-18` |
| `roadmarks.glb` | The published stop and give-way lines, drawn at the extents TD surveyed and hosted by the road each one *crosses* rather than the road it is nearest — the two disagree on 43% of the layer. One primitive, one draw call, **no collider** | ✅ `P3-23` |
| `signs.glb` | The published traffic signs, standing on the poles TD surveyed rather than at the abbreviation points that name them — those are drawing labels, a median 2.6 m away. Shape-faced signs only; anything whose meaning is its text is refused (the no-texture contract). **A library since `P5-2`** — one mesh per face variant plus a unit pole, stood by `signs_placements.json` — one draw call per library mesh, **no collider** | ✅ `P3-16`, `P5-2` |
| `signs_placements.json` | Where the sign library stands: one entry per plate, per lettering quad and per pole, in `landmarks.json`'s transform shape plus a `scale` for the pole. Written beside `signs.glb` and null on its terms | ✅ `P5-2` |
| `lamps.glb` | The published lamp posts, standing on the kerb the ribbon actually drew rather than where LandsD surveyed them — 64.1% of those are inside it — with a bracket arm reaching over the carriageway. The one layer whose vocabulary the publisher defines. Unlit, deliberately: `Q38` bakes the exposure at build time and `Q26` has not chosen a look. **A library since `P5-3`** — one mesh per drawn kind, stood by `lamps_placements.json` — one draw call per library mesh, **no collider** | ✅ `P3-26`, `P5-3` |
| `lamps_placements.json` | Where the lamp library stands: one entry per column, in `landmarks.json`'s transform shape, the `rot_y_deg` being the compass bearing of the column's bracket arm. Written beside `lamps.glb` and null on its terms | ✅ `P5-3` |
| `railings.glb` | The published street furniture — railings, bollards, vehicle barriers — registered onto the kerb the ribbon drew. **A library since `P5-5`**: one unit panel per class, its `.tres` post pitch wide, tiled along every run by `railings_placements.json`; three draw calls, `cull_disabled`, **no collider** by design | ✅ `P3-19`, `Q61`, `P5-5` |
| `railings_placements.json` | Where the panels stand: one entry per panel, in `landmarks.json`'s transform shape plus a `pitch_deg` along the deck. What tiling cost is in `railings.json` per class — `metres_snapped`, `joint_gap_m`, `bends` — never closed by a stretched panel. Written beside `railings.glb` and null on its terms | ✅ `P5-5` |
| `FareSystem` | Fare state machine: idle → hailed → carrying → delivered/failed | ⬜ `P3-1` |
| `ScoreSystem` | Base fare, time bonus, **style chain** and **fare combo** — two distinct multipliers | ⬜ `P3-2` |
| `HUD` | The player's HUD. Speed and the bilingual street plate ship; the minimap, timer and meter are **reserved, empty, checked** slots. Flat-shaded like the city — chamfered polygons, one fill, one keyline — with white for the city's voice and dark for the car's. `--hud=off` for `P3-9` and for art frames | 🟡 `P3-24`; meter, timer and the **world-space** destination marker are `P3-5a` |
| `AudioDirector` | Engine, radio, callouts, ambience buses | ⬜ Phase 5 |

**Architectural rule:** `scripts/core/` holds pure logic — scoring, fare state, traffic rules — with
no `Node` inheritance and no rendering calls. It should be unit-testable headlessly and portable if
the engine ever changes.

**A vehicle's drive layout is scene data, not code.** `VehicleWheel3D.use_as_traction` is authored
per wheel in each vehicle scene, so RWD and FWD need no code change; each vehicle gets its own
`HandlingProfile`, and `centre_of_mass_offset_y` plus `roll_influence` already cover a tall van's
height. The roster this serves is in `ART_DESIGN.md`.

⚠️ **This is why drift bias is derived from chassis geometry, not from a wheel's role.**
`VehicleController._group_axles` splits the wheels by their position along the chassis. Had it keyed
off `use_as_traction` or `use_as_steering` — which since `Q50` are the roles a `VehicleWheel3D`
carries — the front-wheel-drive Crown would have had its drift bias inverted, silently, and only on
the second vehicle anyone built.

### Script map

| Path | Role |
|---|---|
| `scripts/city/city_manifest.gd` | **`city.json`, typed.** The shipping route into the generated city: the tile list, their AABBs, the per-edge carriageway widths and clearances, the lane-width bar, the resolved document paths |
| `scripts/city/city_streamer.gd` | Loads and frees tiles by distance to their published `aabb`, off the main thread, and owns the LOD tier |
| `scripts/core/tile_streaming.gd` | The streaming **policy**, pure — distance to an `AABB` in, tier out. No `Node`, no `load()`, so the decision table is testable headlessly and a tile cannot be rejected *after* being loaded |
| `scripts/core/plan_lattice.gd` | An even grid of plan positions over a region's bounds. Both region-sweeping verify tools take their sample points from it — counted, not float-accumulated, so the far row and column cannot be dropped |
| `scripts/city/streaming_profile.gd` | Schema for distance bands, hysteresis and per-frame budgets. Numbers live only in `tuning/streaming.tres` |
| `scripts/city/road_graph.gd` | One parse per scene, nearest-edge and lane-centre queries over a plan grid. Refuses off-grade edges (`Q13`), and **expresses** — never enforces — passability on the rest (`Q51`) |
| `scripts/city/road_spawn.gd` | `basis_facing` builds the rotation from a direction, which is what deleted the hand-written transform literal and its transpose trap; `Pose.blocked` is why a start line in a wall fails a check rather than reaching a driver (`Q52`) |
| `scripts/city/generated_document.gd` | Parse and version-check a JSON document the ETL wrote. Shared by the locators and by `CityManifest`, so the stale-copy message exists once |
| `scripts/city/generated_layer.gd` | Locator for the nine `.glb` layers — four of them libraries with a placements document since `P5-2`–`P5-5` — `road_surface`, `tramway`, `arrows`, `boxjunctions`, `roadmarks`, `signals` (latent, `Q77`), `railings`, `lamps`, `signs` — one table, id constants, and the per-layer absence terms that used to be nine files (`P5-1`, `Q115`). Also owns the sign text-atlas budget (`Q63`) |
| `scripts/city/generated_*.gd` | Locators for the JSON documents — `road_graph`, `fares`, `landmarks`, `fence` — one definition each, two readers. `generated_fares.gd` is the one place that knows that document's shape, and `generated_landmarks.gd::placement_of` is the one place the compass bearing becomes a Godot rotation |
| `scripts/city/landmarks.gd` | Places the authored heroes where `landmarks.json` puts them. ~2 models, always resident — no streaming, no LOD |
| `scripts/city/mesh_contract.gd` | The mesh rules every generated asset is held to, plus `triangles` and `bounds`. Read by every verify tool that touches geometry, the previews, and `CityStreamer`. Also the two checks a payload-carrying asset needs — that it landed on the shader its material name asked for, and that the importer settings which would silently overwrite a `TEXCOORD_1` have not drifted — both hoisted here when `P3-12` gave the road surface a second copy of them |
| `scripts/city/preview_draw.gd` | Flat ribbons and the unshaded vertex-colour material, shared by the dev previews |
| `scripts/city/*_preview.gd` | Dev previews: `tile`, `road` and `fare` are their own scripts, and `layer_preview.gd` draws any of the nine `.glb` layers by the `layer` id set on its node — nine nodes in each scene, `signals` latent (the manifest names no asset, `Q77`). 🔴 **Adding a drawn layer means adding its node to `city_drive.tscn` AND `city_preview.tscn`** — `verify_city.gd` now holds both scenes' `layer` ids against `generated_layer.gd`'s table in both directions (`Q115`), which is the check `Q73` could not have. `roadmarks` had everything else and no node at all (`Q73`); `lamps` then shipped into the preview scene only, so it was built, verified, and **invisible in the game** — found by driving it, not by a check (`Q82`). ⚠️ **Two nodes are deliberately preview-only and are NOT counterexamples**: `road` is `P1-3`'s graph diagnostic, kept hidden because it z-fights the surface, and `city_drive.tscn` carries `GraphOverlay` instead; `fare` is `P1-5`'s pins, and `P3-1a` has not started. Everything that draws a *generated mesh* is in both. They instantiate what the manifest names so a layer can be looked at on its own. **Not performance measurements** |
| `scripts/city/road_graph_overlay.gd` | Dev: the resolved edge, lane centre and legal travel direction under the moving car |
| `scripts/city/drive_harness.gd` | Dev: place the car on the resolved start line, and return it there when it leaves the world. On the scene root so its `_ready` runs after the car's |
| `scripts/camera/free_look_camera.gd` | Dev fly camera. Bypasses `InputRouter` so dev keys stay out of the shipped action map |
| `scripts/ui/debug_hud.gd` | The one owner of dev chrome. Off by default |
| `scripts/ui/fps_counter.gd` | Frame rate and frame time — a `Label` `DebugHud` builds, styles and tells what to show (`Q119`); it stops counting while hidden |
| `scripts/ui/hud.gd` | The player's HUD. Samples speed at 10 Hz and the road graph at 5 Hz, sets label text only on a change, and registers a raw-versus-displayed readout with `DebugHud` — the one thing that can see a wrong street plate |
| `scripts/ui/hud_layout.gd` | Every HUD rect **and** `P2-4`'s touch geometry. ⚠️ Two touch families and the distinction is load-bearing: `touch_zone_*` is where taps are detected and the HUD may overlap it; `thumb_rest_*` is what a fingertip covers and the HUD may not (`Q80`). Also holds the shared placer — `place`, `axis`, `inset_for_safe_area` — because the HUD and `P2-4`'s zones must resolve in the *same* frame (`Q97`) |
| `scripts/ui/hud_style.gd` | The HUD's palette, chamfer and type scale. Deliberately **not** the road's paint constants (`Q53`). ⚠️ Declares **no `@export` defaults**, like `HandlingProfile` and `StreamingProfile` — a default is a second copy of the tuning table, and this one drifted (`Q80`) |
| `scripts/ui/chamfer_panel.gd` | The HUD's one shape: a flat polygon with cut corners. Not a `StyleBox` — a chamfer is not a corner radius, and this bundle ships no UI textures |
| `scripts/ui/accent_bar.gd` | A `ChamferPanel` that also carries one signed reading — the speed chip's acceleration bar. Split out so the plate and the reserved slots are not carrying five inert speedometer properties. `bar_span` is a pure static precisely so `verify_hud.gd` can grade the bar's **direction**, which is the one thing here that renders perfectly while being wrong |
| `scripts/core/street_tracker.gd` | Pure: which street the plate should say you are on. Owns the dwell that stops it strobing at a junction, the rule that an unnamed edge is not evidence, and the `changes` counter that grades both |
| `scenes/world/golden_hour.tscn`, `scenes/world/clean_daylight.tscn` | The two lighting rigs — `clean_daylight.tscn` is the one both dev scenes instance (`clean_daylight.tres` carries the comparison between them). Instance a rig rather than authoring a second Environment |
| `tools/verify_tiles.gd` | The mesh contract, per tier of every tile the manifest names |
| `tools/verify_city.gd` | `city.json` — georeferencing, per-tier AABB containment, `bounds_game`, and that the named documents exist |
| `tools/verify_road_surface.gd` | `roads.glb` — one draw call, UVs, trimesh collision |
| `tools/verify_road_graph.gd` | `RoadGraph`'s queries — the off-grade refusal, edge resolution, lane placement against the published carriageway width, per-station width on a genuinely mixed edge, `Q51`'s passability (every edge measured, `is_routable` agreeing with the published blocked set, and `nearest_edge` **still** answering on a blocked edge), and query time against a 1 ms budget over a region-wide lattice |
| `tools/verify_city_streamer.gd` | The streaming policy — band edges, hysteresis both ways, and a region-wide residency sweep against the draw-call budget |
| `tools/verify_spawn.gd` | The start line — orientation against its edge vector, nearside-lane placement, drop height, the resolved edge against the fare node, and since `Q52` that a car **fits** where it is set down. **Builds the transposed basis and requires it to fail**, and builds five start lines whose clearances are known and requires each answer — nothing in the shipped city can fire the clearance guard, which stands in 9.00 m of a 3.20 m lane |
| `tools/verify_landmarks.gd` | `landmarks.json` — assets load with mesh and `-col` collision, triangle budget, placed AABB near `bounds_game`, and no tier-0 tile triangle inside each excluded footprint's interior core |
| `tools/verify_{tramway,arrows,boxjunctions,roadmarks,railings,signs,signals,lamps}.gd` | One per drawn layer — the mesh contract, the draw-call and collider claims, and the per-class material dispatch. ⚠️ `verify_railings.gd` checks the dispatch **per class**, so a new railing class needs a row there, in `generated_scene_import.gd` and in the config, and `check.sh` fails if the three disagree |
| `tools/verify_beam_budget.gd` | `BeamBudget` — the spot-light cap is never exceeded **or under-spent**, the nearest cars win when registered farthest-first, a beamless rig takes no slot, and a despawn hands its slot on. ⚠️ One of the three verify tools that need **no built region**: it builds its own stub rigs, so it runs whatever `VERIFY_GENERATED` says |
| `tools/verify_hud.gd` | The HUD's contracts — the thumb-rest reservation (and that overlapping a tap *zone* stays legal), the style's light-plate/dark-chip rule, the plate's font and substitution table, and the street tracker's behaviour from both sides of its dwell. ⚠️ Needs **no built region**: the layout is committed tuning and the tracker takes synthetic samples, which matters because what it protects is `P2-4`'s future screen space |
| `tools/verify_mesh_contract.gd` | The `Q63` amendment itself — an undeclared texture is refused, a declared one inside its budget is admitted, one over budget is refused, and a declared texture that **never arrives** is refused. ⚠️ It asserts the *failures*, because every other verify tool proves an asset conforms and the risk here is the opposite one: a check that has quietly stopped catching anything. ⚠️ Needs **no built region** — it builds its own one-triangle meshes — which matters because no shipped asset declares a texture, so nothing else exercises these branches at all |
| `tools/verify_input.gd` | The touch scheme (`P2-4`) — zone geometry, both relative axes, two thumbs at once, and that touch **overrides** the action map per axis rather than replacing it. Drives the router's `_input` directly with invented fingers, so the events stay out of the real queue. ⚠️ Needs **no built region**, and unlike the others it is the *only* exercise the touch path gets until `P0-3b` lands a handset. ⚠️ It also covers `--touch=mouse`, which no scripted run can reach because `driver.gd` presses the action map and cannot move a pointer. 🔴 **It carries a watchdog and the others do not**: a `SceneTree` tool that aborts before its `quit()` never exits, so a depended script failing to compile wedges `check.sh` instead of failing it — which is worse than the green-over-nothing run `verify_hud.gd` warns about, and it happened here on the first run. ⚠️ **A wedged instance also rewrites `project.godot`**: the one from that first run was alive seven hours later and stripped every comment plus three warning promotions on shutdown, which is the editor incident this document records, reached with no editor (`Q97`) |
| `tools/verify_vehicle.gd` | The taxi's engine-side wiring — the body renders with `vehicle_body.tres` through the import's name channel, the channels `vehicle_lamps.gd` writes are instance uniforms the renderer lists, the imported `UV` payload is integral and inside those channels on lens vertices only, the rig hangs where the script looks, and every beam is authored dark with its cone below horizontal. ⚠️ Needs **no built region** (the taxi is authored and committed), and ⚠️ **sees no frame** — it cannot tell you the shader compiled |
| `tools/generated_scene_import.gd` | Import fixup — see `[importer_defaults]` above |

---

## Input architecture

Desktop/Steam is a target, so input is abstracted from day one via a single action set. Three
schemes feed it and no gameplay script knows which one is live.

| Action | Router type | Keyboard | Gamepad | Touch (`P2-4`) |
|---|---|---|---|---|
| `steer` | `float`, −1…1 | `A` / `D`, ← / → | Left stick X (axis 0) | ✅ thumb 2, horizontal from touch origin |
| `accelerate` | `float`, 0…1 | `W`, ↑ | RT (axis 5) | ✅ thumb 1, **above** touch origin |
| `brake_reverse` | `float`, 0…1 | `S`, ↓ | LT (axis 4) | ✅ thumb 1, **below** touch origin |
| `drift` | `bool` | `Space` | A / Cross (button 0) | ⬜ thumb 2, held past the drift threshold |
| `look_back` | `bool` | `C` | B / Circle (button 1) | ⬜ unplaced |

Deadzones are **0.2** on the axes and **0.5** on the buttons, set in `project.godot`'s `[input]` map.

🔴 **Touch ships three of those five since `Q97`, and the two it does not are the two whose numbers
need a handset.** `drift` wants a threshold and a hysteresis that `Q83` says no desk can pick, and
`look_back` has never been placed at all — so thumb 2's vertical axis is **read and discarded**
rather than lent to something else, because a control that borrows it now is a control that has to
be taken away again.

🔴 **The touch values are merged in `InputRouter` and never fed through the action map.** Both were
tried. `Input.action_press(action, strength)` would have needed no router change and cannot work:
the four axis actions carry the 0.2 deadzone above, and `get_action_strength` returns 0 beneath it,
so the first fifth of every thumb's travel would vanish on a control whose whole design is that
small travel is available.

⚠️ **Touch OVERRIDES the action map per axis; it does not replace it.** An axis with no finger on it
is still the keyboard's. That is not politeness — every scripted drive in this repo runs on
`Input.action_press` (`drive.sh --hold=`), so a router that took its axes from touch state
unconditionally would read zero through every regression run in the repo and each would still exit
`DRIVER OK`.

### The three schemes

**Keyboard** is digital on every action. `steer` comes from `Input.get_axis`, so it arrives as a
float, but only ever −1, 0 or 1; `VehicleController`'s `steer_attack_s` / `steer_release_s` are what
turn that step into a rate, and on this scheme they are doing all of the smoothing there is.

**Gamepad** is analog on the three that matter — stick X for steering, and both triggers for the
longitudinal pair. `drift` and `look_back` are digital face buttons. ⚠️ **Both triggers are already
spent**, so there is no free analog axis for an analog drift, and `drift` stays a `bool` at the
router. Giving it duration is the vehicle's job and ⬜ **is not built** — today the drift ends on the
tick the input stops (`Q50`, `Q83`).

**Touch** is two thumbs and five actions, and the allocation is the whole design. Both axes of both
thumbs are used:

| | Horizontal | Vertical |
|---|---|---|
| **thumb 1** (bottom **right**) | free — `look_back` candidate | `accelerate` above origin, `brake_reverse` below |
| **thumb 2** (bottom **left**) | `steer` | `drift` while held past the threshold |

🔴 **Left steers and right drives since `Q97`, and `Q83` deliberately left that open** — it says "one
outer corner" and "other outer corner" and never commits. The side was chosen on the two touch
racers `Q80` already cites as references, and it lives in `HudLayout.steer_zone()` /
`drive_zone()` rather than in the input code, so swapping it is one edit to a `.tres` reader.

⚠️ **The rects are `touch_zone_left` / `touch_zone_right` and were `touch_steer_*`.** The old names
date from before `Q83`, when both thumbs steered — so `touch_steer_right` was pointing at what is
now the *longitudinal* control, which is how a name gets a throttle wired to a steering axis.

🔴 **Both thumbs are *relative*, not absolute.** The thumb lands anywhere in its zone, that point
becomes the origin, and travel from it is the input. Absolute sliders were rejected because they
need real travel area and there is none: `speed` and `street_plate` share a baseline at y 860 with
the thumb rests starting at y 880, so a slider with usable throw collides with the HUD at **20 px**
of growth (`Q83`). Relative axes keep the rests fingertip-sized and move nothing.

🔴 **`brake_reverse` is the negative half of one longitudinal axis, not a second control**, which is
why touch gains a throttle without gaining a third thumb rest. It also matches what the vehicle
already does: `P0-5b/c/d` made one pedal serve brake *and* reverse, so the axis reads as a single
continuous longitudinal intent — forward, coast, slow, back — and centre-is-coast is exactly the
lift-off that `P0-5b/c/d` requires in order to park.

⚠️ **`drift` is a held vertical offset on thumb 2, and it is deliberately not a tap, an origin latch
or a screen-edge zone** — all three were considered and `Q83` records why each fails. The state is
where the thumb *is*, so it is self-describing and reversible without lifting; exiting a drift never
costs steering. Its threshold needs **hysteresis** — a larger offset to enter than to leave — or a
thumb resting on the boundary toggles the drift every physics tick.

⚠️ **A thumb sweeps an arc, not a rectangle.** The drift threshold is a distance from the touch
origin, not a horizontal line, for that reason; a straight boundary is crossed at a different
horizontal position depending on how far the thumb is extended, which would inject steering into
every drift entry.

⚠️ **The geometry of those zones already exists, in `tuning/hud_layout.tres`.** `P3-24` declared it
so the HUD could be checked against it before `P2-4` was written; `P2-4` reads the same rects rather
than choosing its own, and `verify_hud.gd` fails the day the two disagree. 🔴 **It reads them
through `HudLayout`'s own placer, not by re-deriving them** — the zones are two invisible
`MOUSE_FILTER_IGNORE` Controls anchored exactly as the HUD's slots are, so they inherit the same
anchor rule and the same safe-area inset. A second copy of that arithmetic would put a zone and the
thumb rest inside it a notch apart, which is invisible at a desk and wrong on exactly one device.
⚠️ **On their own `CanvasLayer`, not the HUD's**: `--hud=off` frees the HUD outright, and a touch
layer parented to it would take the player's steering with it — including on `P3-9`'s acceptance
drive, which is a *driving* test that turns the HUD off. 🔴 **Read `Q80` before
using them**: `touch_zone_*` is where a tap is *detected* and non-interactive UI may sit over it —
every HUD Control is `MOUSE_FILTER_IGNORE` — while `thumb_rest_*` is what a fingertip *occludes* and
is the only part the HUD must keep clear. Conflating the two reserves ten times the area that is
actually at stake.

`InputRouter` emits the action set; no gameplay script reads raw input events. It samples in
`_physics_process`, not `_process`: Godot runs every physics step before idle processing, so a
vehicle polling from `_physics_process` would otherwise read a sample one render frame stale — a
guaranteed extra ~16.7 ms of latency, doubling whenever the render rate falls below the physics tick.
Autoloads are the first children of `root`, so the router runs before any gameplay node in the same
tick.

---

## Performance budget

⚠️ **One tier ships today, the desktop one.** Nothing in `game/scripts/` reads `OS.has_feature`,
`OS.get_name` or any quality setting — the only platform branching in the project is the `.mobile` /
`.web` suffixes in `project.godot`. The mobile tier is unbuilt and blocked on `P0-3b`, which needs a
signing identity and the two floor handsets.

| Metric | Mobile tier | Desktop tier |
|---|---|---|
| Target | 60 fps @ 1080p | 60 fps @ 1440p |
| Draw calls | < 150 | < 400 |
| Visible triangles | < 300k | < 1M |
| Texture memory | < 128 MB | < 512 MB |
| Bundle size | < 200 MB (iOS cellular threshold) | no hard limit |
| Shadows | Vehicle blob shadow only ⚠️ | Two directional cascades at 400 m |

⚠️ "Vehicle blob shadow only" deserves re-examination before anyone implements it: shots with shadows
*off* looked markedly worse than the line implies — flat and blown out, the canyon losing its depth.
A real mobile tier needs the ambient and tonemap re-tuned around a blob shadow, not the shadow
switched off.

**Device floor:** iOS **A13** (iPhone SE 2nd gen / iPhone 11); Android **Adreno 618** tier, Vulkan
1.1, 4 GB RAM. Two separate decisions — the iOS floor is a support-matrix question, the Android floor
is the one that constrains the budget.

Key techniques, in order of what they buy:

1. **Merge aggressively at build time.** Untextured buildings with vertex colours merge into one mesh
   per tile — no atlas packing, no texture juggling. This is the main reason the untextured dataset
   was chosen.
2. LOD via ETL-generated tiers, not runtime decimation.
3. One draw call per generated layer mesh, built by the ETL. Since `Q115` the repeated objects —
   signs, lamps, arrows, the barrier family — ship as a **library stood by a `MultiMesh`**, which
   costs the draw call the merged mesh cost (`P3-29`: +1 against +36 for per-scene instancing) and
   multiplies with the shadow passes per extra library mesh; the road, the boxes and the stop lines
   stay merged because nothing in them repeats.
4. Occlusion is largely free — dense HK street canyons occlude naturally.

---

## Build pipeline

```
etl/  →  python -m pipeline --region wan_chai
      →  etl/out/<region>/{city.json, roadgraph.json, roads.glb, …, tiles/*.glb}
      →  tools/sync_generated.sh → game/assets/generated/
      →  Godot export presets → iOS / Android / desktop / web-demo
```

Seventeen stages in one dependency chain — `fetch` through the drawing stages to `export`, the list
`__main__.py` owns — **~19 s end to end** for Wan Chai against a warm source cache. Each stage also
runs on its own against the same arguments, which is how they are developed:

```sh
python -m pipeline.buildings --region wan_chai
python -m pipeline --region wan_chai --from roads   # resume mid-chain
```

`python -m pipeline` invokes each stage through the *same* entry point those commands use, so a full
build and a partial one cannot drift apart. A stage that exits non-zero stops the run rather than
letting the next one read the previous build's output. `fetch` is the only stage that touches the
network.

**`export` also validates.** It re-reads what it just wrote and checks what no single stage checks: a
fare node naming an edge the graph no longer has, a tile whose GLB was never written, a document left
over from another region, geometry outside the declared bounds. Each stage's output is internally
valid in every one of those cases. Everything the manifest asserts is checked against the document it
came from, never against the manifest itself — a stale `city.json` is perfectly self-consistent.
`python -m pipeline.export … --check` runs the checks alone.

The ETL is **not** run by CI. It runs when source data or pipeline logic changes, and its output is a
versioned build artefact.

**Getting a build into the game:** `tools/sync_generated.sh <region>` copies exactly the files
`city.json` names — asked of the ETL (`python -m pipeline.export … --list`), never inferred from a
directory listing. That keeps the stage intermediates out of the bundle, and it removes tiles a
previous build left behind, because nothing else would ever notice them: every check in the project
starts from the manifest, and the manifest has forgotten them.

**`game/export_presets.cfg` is committed, comment-free, and the export dialog rewrites it** in the
same form. Never put keystore passwords, provisioning profiles or signing identities in it — those
come from Godot editor settings or the environment (`.gitignore` says the same). ⚠️
`com.hktaxiq.game` is a `P0-3b` placeholder appearing three times — `application/bundle_identifier`
twice and `package/unique_name` once — and all three must become the real reverse-domain identifier
before any store submission.

**Then check it in-engine**, because the ETL cannot assert engine-side facts about its own output.
`--import` first, since a fresh sync writes GLBs with no import sidecars — then `tools/check.sh`.

### Looking at it

| Scene | For |
|---|---|
| `scenes/dev/city_preview.tscn` | Fly around. Instantiates **every** tile at one tier — no streaming, no LOD switching, so it is *not* a performance measurement |
| `scenes/main.tscn` | Drive. `World` instances `scenes/city_drive.tscn` — the same assets with the taxi on the road surface's collider and the chase camera — and `GUI` holds the HUD |

**The spawn is resolved at runtime and is not written down anywhere.** `drive_harness.gd` asks
`RoadSpawn.at_fare_node` for fare node **`f_004`, "Expo Drive eastbound underneath HKCEC Phase II"** —
a real taxi stand in the Transport Department's data, so the car begins where a Hong Kong taxi would
be waiting. Change `spawn_fare_id` on the scene root to start somewhere else.

The heading is **not** supplied to the query. A zero heading makes `nearest_edge` take the edge's own
vertex order, and `P1-3` reversed the polyline of every backward edge precisely so that order *is*
the legal direction. Passing the car's authored rotation in would let the car decide which way a
two-way street runs, which is backwards.

The car sits in the **nearside lane**, 2.56 m left of the centreline on this edge, and never on the
centreline itself — partly because a car should start in a lane, and partly because the centreline is
the worst place on the network to put a wheel: it is where opposed ribbons overlap and where junction
caps double up, so a raycast can find two coplanar collision triangles a few centimetres apart and
the wheel picks between them. **Y is the one number not published**: lane centre plus ray length plus
`DROP_CLEARANCE_M`. The car is dropped, not set down, and settles onto its suspension — and moving
the spawn moves the harness's fall-detection floor with it.

⚠️ **The trap this replaced, kept because the fallback literal in `city_drive.tscn` still has it.**
`Transform3D`'s 12-float constructor fills `Basis` **rows**, while "forward" is `-basis.z` — and in
GDScript `basis.z` *is* the column. Building a literal as columns therefore transposes the basis, and
**a transpose is not a 180° flip**: transposing a yaw-only basis mirrors the heading about world −Z,
which is 172° wrong for this spawn, 180° for a due east-west street, and **0° — a silent no-op — for
a north-south one.** So the error is invisible on exactly the streets where you would trust an
eyeball check. There is also a check needing no tooling at all, and it is the one that caught this:
**the harbour is north**, so from a car facing east, a left turn heads for the water.

**One thing is knowingly missing:** **the flyovers cannot be driven onto** (`Q13`). Off the
carriageway is ground, and solid (`P3-10`), so mounting a kerb puts the car on the pavement rather
than through it. The dev harness that catches a car falling out of the world still runs — the region
has edges, and level −1 runs under the terrain (`Q21`).

---

## Constraints

1. No runtime network calls. The game is fully offline.
2. No engine-specific formats out of the ETL — glTF and JSON only.
3. Hong Kong facts live in `etl/config/hong_kong.yaml` (tuning, vocabularies) or
   `etl/pipeline/hongkong.py` (the CRS pair, drive-on-the-left, branch sign codes) — one home
   each, never both (`Q100`).
4. Tuning values live in `game/tuning/*.tres`, never as constants in scripts.
