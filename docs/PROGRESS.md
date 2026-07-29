# Progress

Living document. **Update this whenever a task changes status, a decision is made, or an open
question is answered.** Newest entries at the top of each log.

Last updated: 2026-07-29

---

## Current status

**Phase 0 — Spikes and scaffolding. `P0-2` and `P0-3` done. `P0-5` is the critical path.**

The Godot project is scaffolded, imports clean on 4.7.1, and exports to macOS, web and Android.
`P0-5` (grey-box fun test) is now unblocked and is the next thing that matters — it is the gate
that decides whether this is a game before any ETL investment.

### Task board

| ID | Task | Status | Notes |
|---|---|---|---|
| `P0-1` | Identify source data granularity | 🟡 Partial | Roads solved. Buildings still portal-only — needs sheet numbers. |
| `P0-2` | ⚠️ Z-value spike | ✅ **Done** | No Z, but `ELEVATION` encodes level. Region holds. |
| `P0-3` | Godot project scaffold | ✅ **Done** | Godot 4.7.1. Imports clean; macOS/web/Android export verified. |
| `P0-3b` | Mobile device build verification | ⬜ Not started | Split out of `P0-3`. `Q4` resolved; now needs only a signing identity and the two floor handsets. Not on the critical path. |
| `P0-4` | ETL scaffold | ⬜ Not started | |
| `P0-5` | Grey-box fun test | 🟡 In progress | **The critical path.** Subjective gate — needs the user |
| `P0-5a` | └ Vehicle controller approach | ✅ **Done** | Measured. Custom raycast on `RigidBody3D`; `VehicleBody3D` rejected. |
| `P0-5b` | └ Grey-box Gloucester block | ✅ **Done** | Circuit built from JSON; widen_factor is data |
| `P0-5c` | └ Minimal chase camera | ✅ **Done** | Spring arm, speed FOV, look-back |
| `P0-5d` | └ The drive test | ⬜ **Blocked on user** | **Needs a display. `godot --path game`** |
| `P1-*` | ETL vertical slice | ⬜ Blocked | Gated on `P0-5` (`P0-2` cleared) |
| `P2-*` | Driving the real city | ⬜ Blocked | |
| `P3-*` | Playable slice | ⬜ Blocked | |

Legend: ⬜ not started · 🟡 in progress · ✅ done · ❌ blocked

---

## Open questions

| # | Question | Impact | Owner | Status |
|---|---|---|---|---|
| Q1 | Do Road Network v2 centrelines carry Z values? | **Critical** — was the region-choice risk | `P0-2` | ✅ **Resolved 2026-07-29** |
| Q2 | Which LandsD 1:1000 sheet numbers cover the region? | Blocks automated fetching of building data | `P0-1` | 🔴 Open |
| Q3 | Can building data be downloaded programmatically at all? | **Now the top risk.** Road data has direct static URLs; building data exposes only interactive portal pages | `P0-1` | 🔴 Open |
| Q4 | Confirm the device floor | Sets the whole perf budget and gates `P0-3b` | user | ✅ **Resolved 2026-07-29** |
| Q5 | Actual file sizes of the region's building data | Affects fetch time and disk planning | `P0-1` | 🟡 Partial — `CENTERLINE.gml` is 486 MB territory-wide |
| Q6 | Does the region need Central for the circuit to feel complete? | Scope | after `P3-9` | 🟡 Deferred |

### Q1 — resolved in full

**No true Z coordinates, but grade separation is encoded as an integer `ELEVATION` attribute.**
Verified against live data: `CENTERLINE.gfs` declares 2D LineString, every `gml:posList` carries
`srsDimension="2"`, and `ELEVATION` takes values 0 (86.5%), 1 (2.0%), and 2 (11.5%) across samples
spanning the full 486 MB file.

**The Wan Chai region choice holds. No fallback to Tsim Sha Tsui.** Map `ELEVATION` to authored
deck heights in city config; only allow junctions between edges at matching levels. Full detail in
`docs/DATA_SOURCES.md`.

**Bonus:** bilingual street names (`STREET_ENAME` / `STREET_CNAME`) ship in the source — one less
thing to hand-author. `-99` and `–９９` are null sentinels.

### Q4 — resolved

**iOS: A13 (iPhone SE 2nd gen / iPhone 11). Android: Adreno 618, Vulkan 1.1, 4 GB RAM.**
Reference Android handsets: Pixel 4a (SD730G), Redmi Note 9 Pro (SD720G), Galaxy A52 (SD720G).

The two floors are separate decisions and only one sets the budget — see the decision log entry
below.

---

## Decision log

### 2026-07-29 — `P0-5a` Vehicle controller: **custom raycast on `RigidBody3D`**, not `VehicleBody3D`

Measured, not assumed. A throwaway headless spike built a `VehicleBody3D` with four
`VehicleWheel3D` on a flat plane under Godot 4.7.1 + Jolt and drove it through settle → accelerate →
steer → drift phases.

**`VehicleBody3D` is not broken under Jolt.** It instantiates, simulates, accelerates, steers and
brakes. The wheel query API works: `is_in_contact()` reported 4/4 while cornering, with
`get_skidinfo()` at 0.894 and `get_rpm()` at 269.5. Anyone repeating this spike should not expect a
crash — the problem is subtler.

**The problem is that the tuning schema is inexpressible.** `ClassDB` introspection shows
`VehicleBody3D` exposes exactly three tunables — `engine_force`, `brake`, `steering` — with the rest
on `VehicleWheel3D`. Mapping the 18 `HandlingProfile` fields against that surface:

| Fit | Count | Fields |
|---|---|---|
| Direct | 4 | `engine_force`, `brake_force`, `centre_of_mass_offset_y`, `gravity_scale` |
| Partial / fightable | 4 | `steer_angle_max_deg`, `grip_lateral`, `grip_longitudinal`, `drift_grip_scale` |
| **Absent** | **10** | both speed caps, three steering-curve fields, two drift fields, all three collision/recovery fields |

**The decisive finding: `wheel_friction_slip` is isotropic.** One friction number covers every
direction, so `grip_lateral` and `grip_longitudinal` collapse into each other, and a drift cannot
break lateral grip without destroying traction and braking with it. Measured, holding throttle:

| Drift variant | Speed lost over 2 s | Implied scrub/s (target **0.080**) | Peak slip angle (threshold **14°**) |
|---|---|---|---|
| Friction × 0.35, all four wheels | 57% | 0.285 | 162.7° |
| Friction × 0.35, rear axle only | 30% | 0.151 | 162.6° |

Both violate `GAME_DESIGN.md` on two counts at once: `drift_speed_scrub_per_s` is "deliberately
small — drifting must not feel like a penalty" (missed by 1.9–3.6×), and grip must be "high,
forgiving, no spin-outs" (162° is a full spin, not a slide).

**Could it be tuned out? Partly — and that is the argument against it.** Yaw damping, counter-steer
assist and per-axle friction curves would suppress the spin. But that is an arcade correction layer
built on top of a physical model actively resisting it, leaving `VehicleBody3D` contributing only
suspension raycasts — perhaps 100 lines of the eventual controller. Every future tuning change would
be a negotiation with the engine rather than a dial. `GAME_DESIGN.md:120` expects vehicle feel to be
iterated on more than anything else in the project, which makes that friction compound.

**Consequences:**
- `handling_profile.gd` gains a `Suspension` group — the original schema had none, having assumed
  `VehicleBody3D` would own them. Values seeded in `handling.tres`.
- Spring rate is specified as **natural frequency in Hz, not a raw N/m constant**, so it stays
  correct when vehicle mass changes or a heavier vehicle joins the roster. It is *not* gravity-
  independent, though: static sag is `g_eff / (2πf)²`, so `gravity_scale = 1.6` deepens sag by the
  same 1.6× and eats the bump travel that absorbs kerbs and jump landings. The seed is therefore
  **2.8 Hz** — 2.2 Hz scaled by `√1.6`. Anyone retuning `gravity_scale` must rescale this with it.
- Forward note for `P2-3`: the class docstring promises an unassigned profile "fails loudly", but
  nothing enforces that yet. `wheel_radius_m = 0.0` divides by zero and `suspension_frequency_hz =
  0.0` is a dead spring, so the controller should assert both non-zero on assign. It should also
  cache the derived `k = mω²` and `c = 2ζ√(km)` rather than recomputing transcendentals per wheel
  per tick on the Adreno 618 floor.
- New `anti_roll` field: the spike rolled the car over even with `centre_of_mass_offset_y` applied,
  so roll resistance needs its own dial rather than being a side effect of centre-of-mass placement.
- Wheel **geometry** (wheelbase, track, mount points) deliberately stays out of `HandlingProfile` —
  that is per-vehicle model data; the resource describes feel, which is shared across the roster.
- `P2-3` is now "finish and tune the controller", not "adopt `VehicleBody3D`".

Spike files were deleted after the numbers were recorded here.

### 2026-07-29 — Device floor: **A13 / Adreno 618**, named as two separate floors

Resolves `Q4`, on the user's call. Reverses the earlier assumption of iPhone XR (A12) /
Snapdragon 730-class.

- **iOS floor: A13** — iPhone SE 2nd gen (2020) or iPhone 11 (2019).
- **Android floor: Adreno 618 tier** — Vulkan 1.1, 4 GB RAM. Spans Snapdragon 710/712/720G/730/730G.

**These are two decisions, not one, and the old single-device phrasing hid that.** The iOS floor is
a *support-matrix* question — A12 is off the current iOS train, so an XR would mean testing against
hardware that can no longer take OS updates. The Android floor is a *performance* question, and it
is the only one that constrains the budget: A13 is roughly 3–4× the GPU throughput of the Adreno 618
tier, so anything that holds 60fps on the Android floor is free on iOS.

**The Mobile renderer requires Vulkan**, so the real floor is "Vulkan 1.1 with a maintained driver"
before it is any particular chip. `project.godot` locks `rendering_method="mobile"`; cheap hardware
with broken or absent Vulkan drivers is out regardless of the name on the floor.

**Chosen over a more conservative floor because Hong Kong skews high-end** — iPhone share is far
above global average and the Android side skews Samsung and flagship-adjacent brands rather than
budget hardware. A global-market floor would cost art fidelity for users this TAM does not have.

**This makes the existing perf budget coherent rather than arbitrary.** <150 draw calls, <300k
triangles and <128 MB texture are sane Adreno-618 numbers — needlessly tight for a 2022 floor,
unachievable on a 2017 one.

**Follow-through:** the floor defines **tier 0** of the perf tiers that `P3-3` scales traffic
density against. Per hard rule 4 that lives in config, not constants — to be authored in `P2-6`.
Hardware to acquire for `P0-3b`: one A13 iPhone and one Adreno 618 Android, both viable secondhand.

### 2026-07-29 — Engine version: Godot 4.6 → **4.7.1**
Reverses the locked "Godot 4.6" decision, on the user's call. Homebrew's cask ships 4.7.1, which is
current stable; 4.6.3 would have needed a manual pinned download for no gain this early. Nothing in
the project depends on 4.6 specifically — no code existed when the switch was made.

**The GDScript-not-C# decision is unaffected.** Re-verified against the official 4.7 docs: desktop
C# is fully supported, Android and iOS remain **experimental**, and web export remains
**unsupported entirely**. The reasoning stands unchanged.

`CLAUDE.md` and `docs/ARCHITECTURE.md` updated to match.

### 2026-07-29 — `P0-3` acceptance criteria split
The written criterion, "builds and runs on the device floor", bundled a scaffold together with
Android SDK setup, Xcode, an Apple signing identity and physical 2019-era hardware. Split per the
working agreement in `PLAN.md` rather than quietly redefined:

- **`P0-3`** — project imports clean, cube scene at 60fps with an FPS counter, export presets
  committed as configuration, desktop and web verified to export.
- **`P0-3b`** — signed on-device builds for iOS and Android, and the real bundle identifier.

`P0-5` depends only on `P0-3`, so the critical path is not affected.

### 2026-07-29 — `P0-2` resolved without writing code
Answered Q1 by inspecting the live dataset directly (GFS schema + ranged reads across the 486 MB
GML). No Z ordinates, but `ELEVATION` encodes grade separation as an ordinal level. Region choice
holds. Also surfaced: bilingual street names ship in the source, `-99` is the null sentinel, and
the file must be streamed and clipped rather than loaded whole.

**Top data risk has moved from roads to buildings.** Roads are fully scriptable via static URLs;
building data is portal-only with no direct download endpoint. Not slice-blocking — the region is
a handful of 1:1000 sheets and can be fetched by hand — but it must be solved before a second city.


Decisions are **settled**. Do not re-litigate without explicit instruction from the user — but do
flag it here if new evidence contradicts one.

### 2026-07-29 — Engine language: GDScript, not C#
Verified Godot C# platform support: desktop full, **Android and iOS experimental**, **web
unsupported entirely**. Mobile is a primary target and the free web demo is the planned marketing
funnel — C# compromises both. The complex code lives in the Python ETL anyway, so C#'s tooling
advantage earns little. Performance escape hatch is **GDExtension** (C++/Rust), not C#.

### 2026-07-29 — Target platforms: mobile + desktop/Steam
User decision. Adds a gamepad/keyboard input layer, resolution-independent UI, a desktop LOD tier,
and a Steam build path. ~15–20% engineering overhead across input and UI, accepted for the broader
revenue options.

### 2026-07-29 — Scope: vertical slice first
Plan covers Phases 0–3 in executable detail. Phases 4–6 are outline only and will be refined after
the Phase 3 gate.

### 2026-07-29 — Engine: Godot 4.6
Chosen after the target shifted from a free web release to a commercial store product. Reversed an
earlier web-first (three.js + Rapier) recommendation. Decisive factors: native mobile performance
versus Android WebView GPU throttling, and a single codebase covering mobile, desktop, and a web
demo. Store-service integration turned out to be a weak argument, since a one-time unlock IAP is
small on any stack.

### 2026-07-29 — Monetisation: free download + one-time unlock (deferred)
Not F2P (2–5% conversion needs volume this TAM can't supply, and retention mechanics would corrode
a 3-minute arcade loop). Not paid-upfront (paid games are <5% of App Store revenue, and this
product's appeal — "it feels like Hong Kong" — cannot be conveyed in a screenshot; a free slice
*is* the marketing). **Build implication:** design Wan Chai to be standalone-playable as the free
tier. Final call deferred to launch.

### 2026-07-29 — Region: Wan Chai → Causeway Bay
Chosen over Tsim Sha Tsui and Central. Reasons: a natural circuit exists in the real road layout
(Gloucester → Canal Road Flyover → Hennessy), map edges are diegetic (harbour north, escarpment
south), and it has real grade separation without Central's multi-level data risk. TST is the
fallback if `Q1` resolves badly.

### 2026-07-29 — Building source: non-textured / LOD1, NOT photogrammetry
The tile-based photogrammetry mesh was rejected: a prior public attempt found ground gaps, level
differences, and vehicles baked into the geometry, and concluded it suited flight rather than
driving simulation. Decimating photogrammetry produces blobs, not low-poly style. The non-textured
and 3D-BIT00 Level 1 products are already extruded flat-shaded volumes — the target art style is
the data's native form.

### 2026-07-29 — Art direction: accurate city, toy vehicles
Stylise the actors, not the stage. Recognition is the product, so building proportions stay
accurate; charm and readability come from Choro-Q vehicle proportions.

---

## Planned vehicle roster (user direction, 2026-07-29)

Real models, not generic cars. Recorded because the **drive layout differs across them**, which is
an architecture constraint rather than an art note.

| Vehicle | Drivetrain | Notes |
|---|---|---|
| Old Toyota Crown (Comfort) | LPG, **rear-wheel drive** | The iconic HK red taxi |
| New Toyota Crown | Hybrid, **front-wheel drive** | |
| Toyota Hiace | CVT | Van proportions — tall, high centre of mass |

**Already supported without code changes:** `WheelMount.drives` is authored per wheel in each
vehicle scene, so RWD and FWD are scene data. Each vehicle gets its own `HandlingProfile`, and
`centre_of_mass_offset_y` plus `anti_roll` already cover the Hiace's height.

**This is why drift bias is derived from chassis geometry, not from `drives`.** `VehicleController`
computes `WheelMount.is_front` from the wheel's position along the chassis. Had it keyed off
`drives` or `steers`, the front-wheel-drive Crown would have had its drift bias inverted — the
front would break away instead of the rear.

**Not yet modelled:** transmission character. `engine_force` is a flat constant with no gears or
torque curve, so an LPG Crown, a hybrid and a CVT would accelerate identically. Hybrid instant
torque versus LPG's laggier delivery would need a torque curve in `HandlingProfile`. Open, not
urgent — flag it before the roster work in Phase 4.

---

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Road data lacks Z values | **High** | `P0-2` first. Fallbacks documented in `DATA_SOURCES.md`. Worst case: switch region to TST. |
| Real geometry isn't fun to drive | **High** | `P0-5` grey-box test before any ETL investment. Road widening and hand-added ramps are the designed remedy. |
| Doesn't read as HK to locals | **High** | `P3-9` authenticity test with ≥3 real drivers; run again every phase after. |
| Perf misses 60fps on device floor | Medium | Budget defined up front; untextured merged tiles are the main lever; `P2-6` is a dedicated pass. |
| Source data quirks (dual carriageways, doubled junctions) | Medium | Known and documented; budget extra time on `P1-3`. |
| GDScript learning curve | Low | Small codebase; complexity lives in Python. |
| Landmark depiction IP | Low | Untextured massing; legal sight-check before launch (Phase 6). |
| TAM too small to be commercial | Medium | City-agnostic ETL is the scaling answer — city packs, not one city. |

---

## Metrics to track from Phase 2

Record measured values here, not estimates.

| Metric | Target (mobile) | Latest | Date |
|---|---|---|---|
| FPS on device floor | 60 | — | — |
| Draw calls | < 150 | — | — |
| Visible triangles | < 300k | — | — |
| Texture memory | < 128 MB | — | — |
| Bundle size | < 200 MB | — | — |
| ETL full-run time | — | — | — |

---

## Session log

### 2026-07-29 — `P0-5b` / `P0-5c` Grey-box circuit, vehicle controller and chase camera

`VehicleController` implemented per the `P0-5a` decision: raycast suspension on `RigidBody3D`,
spring and damper sized from natural frequency, tyre forces capped **independently** for lateral and
longitudinal grip. That separation is the whole reason for the custom controller, and it verified:

| Same corner, held 4 s | Speed scrubbed /s | Peak slip angle |
|---|---|---|
| Gripping (no drift) | 0.297 | 16.4° |
| **Drift held** | **0.270** | 12.6° |

Drifting is *cheaper* than gripping, because breaking lateral grip removes the cornering force that
was scrubbing speed. Under `VehicleBody3D` the same manoeuvre cost 30–57% extra and spun to 162°.
The measured 0.27 is full-lock cornering, not the drift mechanic — a straight-line drift figure
comparable to `drift_speed_scrub_per_s = 0.08` needs a clean skid pad, which `P0-5d` can judge by
feel instead.

Headless verification on the built circuit: suspension settles at **50.6 mm sag** against 50.7 mm
predicted, body rests at 0.649 m, 4/4 wheels grounded, accelerates smoothly and dead straight to
49.9 km/h, corners upright without flipping, and the camera tracks at 2.2 m.

**Three bugs found and fixed by measuring rather than reading:**
- **Anti-roll signs were inverted** — force pushed *down* on the already-compressed side, amplifying
  roll instead of resisting it. The car flipped on the first hard corner. This is why `P0-5a`'s
  spike flip was not purely a centre-of-mass problem.
- **Coasting drag divided by `delta`**, making it framerate-dependent and roughly 35× too strong
  (~70% of velocity shed per second). `apply_force` already integrates over the tick.
- **A `Node3D`-typed `@export` does not resolve from a hand-authored `.tscn`** — it silently read
  null and the camera never moved. `ChaseCamera` now takes a `NodePath` and resolves it explicitly.
  Worth remembering for every scene authored outside the editor.

**Review pass found a fourth bug the drive tests could not have caught: steering was inverted.**
`InputRouter.steer` is `+1` for right, but a *positive* rotation about `+Y` turns the `-Z` forward
vector toward `-X` — left. Press D, car goes left. The headless tests missed it because they only
ever steered one direction and never checked which. Verified fixed by yaw sign: held right lock now
gives monotonically decreasing yaw, i.e. clockwise from above. Also fixed in the same pass: wheel
raycasts accepted wall faces as ground (free traction and a launch ramp off any building), six
buildings sat inside the carriageway at the junctions the circuit has to turn through, road slabs
were exactly coplanar with the ground plane and z-fought across their whole surface, and auto-right
teleported the car after that tick's forces had already been queued for its overturned pose.

**Open question for `P0-5d`:** slip angle is *lower* with drift held (12.6°) than without (16.4°),
because `drift_grip_scale` currently applies to all four wheels equally — that ploughs (understeer)
rather than rotating the car (oversteer). An arcade drift usually wants the rear to break away
first, which would need a per-axle bias the schema does not yet have. **Deliberately not added
before the user has driven it**, since which way it should feel is exactly what `P0-5d` decides.

`P0-5b` road widths live in `game/assets/authored/greybox_wanchai.json` as `real_width_m` ×
`widen_factor`, so the arcade divergence stays visible and re-drivable in seconds. `P0-5c` is
explicitly throwaway — `P2-5` owns the real camera.


### 2026-07-29 — Planning
Feasibility evaluated, region selected, engine and language decided, monetisation direction set.
Wrote `CLAUDE.md`, `README.md`, and the five docs in `docs/`. No code yet.

**Immediate next steps:** `git init`; then run `P0-2` (Z-value spike) and `P0-5` (grey-box fun
test) in parallel — one kills the data assumption, the other kills the design assumption.

### 2026-07-29 — `P0-3` Godot project scaffold
`game/` scaffolded on Godot 4.7.1 and machine-verified headlessly: clean import, all GDScript
parses, Mobile renderer and Jolt confirmed active at runtime, all six input actions bound to both
keyboard and gamepad.

Seams for `P0-5` laid deliberately: `InputRouter` autoload sampling in `_physics_process` (so no
gameplay script ever reads raw input, and the vehicle never reads a stale sample), `HandlingProfile`
+ `tuning/handling.tres` where the `.tres` is the **only** home for the numbers, and an FPS /
frame-time overlay autoload that gates itself out of release builds unless run with `--fps`.

**Export results:** macOS (57 MB) and Web (37 MB wasm) verified. Android also exports to a 25 MB
APK using the prebuilt template — no Gradle or Android SDK required, which is better than
expected. iOS fails only on a missing App Store Team ID, which is the correct failure: that
credential must never be committed.

**Discovered:** `rendering/textures/vram_compression/import_etc2_astc` must be enabled or Godot
refuses to export **any** arm64 target — including Apple Silicon macOS, not just phones. Needed for
the mobile tier regardless; the desktop export just surfaced it early.

**Not verified, and needs the user:** the cube scene rendering at 60fps in an actual window
(`tools/export.sh` builds it; running it needs a display), and anything on physical hardware
(`P0-3b`).

**Placeholder to replace:** bundle identifier `com.hktaxiq.game` in `game/export_presets.cfg`.
