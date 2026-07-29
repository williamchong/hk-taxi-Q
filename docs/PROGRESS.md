# Progress

Living document. **Update this whenever a task changes status, a decision is made, or an open
question is answered.** Newest entries at the top of each log.

Last updated: 2026-07-29

---

## Current status

**Phase 0 complete enough to proceed. Phase 1 is open and is now the critical path.**

The Godot project is scaffolded and exports to macOS, web and Android; the grey-box circuit is
drivable and the handling is accepted; the ETL package exists with the coordinate conversion under
test. `P0-1` and `P0-3b` remain open but neither gates Phase 1.

**`P0-5` passed conditionally, not cleanly** — the user drove it, found the handling acceptable, and
judged that *fun* cannot be assessed from a grey box at all. See the decision log. The consequence
is that the "is this a game?" question is **not** answered yet, and the risk `P0-5` existed to retire
is deferred rather than closed.

### Task board

| ID | Task | Status | Notes |
|---|---|---|---|
| `P0-1` | Identify source data granularity | 🟡 Partial | Roads solved. Buildings still portal-only — needs sheet numbers. |
| `P0-2` | ⚠️ Z-value spike | ✅ **Done** | No Z, but `ELEVATION` encodes level. Region holds. |
| `P0-3` | Godot project scaffold | ✅ **Done** | Godot 4.7.1. Imports clean; macOS/web/Android export verified. |
| `P0-3b` | Mobile device build verification | ⬜ Not started | Split out of `P0-3`. `Q4` resolved; now needs only a signing identity and the two floor handsets. Not on the critical path. |
| `P0-4` | ETL scaffold | ✅ **Done** | `pipeline/` + `hong_kong.yaml`; 22 tests, `ruff` clean. Datum trap found — see log. |
| `P0-5` | Grey-box fun test | ⚠️ **Passed, conditional** | Handling accepted. Fun verdict deferred — see decision log. |
| `P0-5a` | └ Vehicle controller approach | ✅ **Done** | Measured. Custom raycast on `RigidBody3D`; `VehicleBody3D` rejected. |
| `P0-5b` | └ Grey-box Gloucester block | ✅ **Done** | Circuit built from JSON; widen_factor is data |
| `P0-5c` | └ Minimal chase camera | ✅ **Done** | Spring arm, speed FOV, look-back |
| `P0-5d` | └ The drive test | ⚠️ **Passed, conditional** | Driven and verified. No blocking feel problem; no fun verdict possible yet. |
| `P1-*` | ETL vertical slice | 🟢 **Unblocked** | `P0-4` done, `P0-2` cleared, `P0-5` gate released. `P1-1` needs `P0-1`. |
| `P2-*` | Driving the real city | ⬜ Blocked | Gated on `P1-7` |
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
| Q7 | Does game-space Z run negative northward, or should the origin move to the NW corner? | Data contract — tile IDs and every position in `city.json` | `P1-6` | 🔴 Open |
| Q8 | What is the cheapest build that lets the user judge "is this fun?" | **Now the top project risk** — `P0-5` did not answer it | user | 🔴 Open |

### Q7 — the data contract contradicts itself on the sign of Z

Surfaced by `P0-4`. `ARCHITECTURE.md` states the conversion as `game_z = -(northing - origin_northing)`
with the origin at the region's **south-west corner** — which puts the whole region at Z ≤ 0. Two
sections later the same document's `city.json` example shows `bounds_game` running from `[0, -20, 0]`
to `[1650, 220, 900]`, i.e. **positive** Z. Both cannot be true.

`crs.py` implements the stated formula, because it appears in two documents (`ARCHITECTURE.md` and
`DATA_SOURCES.md`) while the positive-Z bounds appear once, in an example whose sibling `origin`
field is explicitly labelled a placeholder. `test_crs.py` pins the resulting sign so the choice
cannot drift silently.

**Recommendation: move the origin to the north-west corner** and leave the formula otherwise
untouched. Z then runs 0…+886 southward, the whole region sits in the positive quadrant, tile
indices become a plain raster with row 0 at the north, and the existing `bounds_game` example
becomes correct. The cost is a one-line change in `GameTransform.from_bounds` plus a docs edit —
but only until `P1-6` writes a real `city.json`, after which it is a `schema_version` bump.
**Cheap now, not later.** Not actioned: it contradicts a documented decision, so it is the user's
call.

### Q8 — `P0-5` did not retire the risk it existed to retire

`PLAN.md` justified `P0-5` as answering "is this a game?" *before* any ETL investment, on the
reasoning that "if the driving isn't fun with boxes, real geometry will not save it." The drive test
established that the driving is **not bad** — no blocking handling problem — but the user's verdict
is that fun is not assessable without either the real Hong Kong scene or the fare loop. The premise
that a grey box could answer the question was wrong.

Two candidate answers, both cheaper than waiting for the Phase 3 gate:

1. **Real geometry first** — proceed through Phase 1 as planned. Answers "does it read as Hong
   Kong, and is driving *this city* interesting?" Multi-week, but every hour of it is on the
   critical path regardless.
2. **A throwaway fare loop on the existing grey box** — four hand-placed markers, a timer, a
   destination arrow. Roughly a day, answers "is the core loop interesting?" independently of
   geometry, and is a rehearsal for `P3-1`. But it is throwaway work, and `GAME_DESIGN.md` ties the
   loop's appeal to recognisable places, which a grey box cannot supply.

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

### 2026-07-29 — `P0-5` gate: **released conditionally**; the fun question moves to Phase 1

User verdict after driving the grey-box circuit: *"verified and seems acceptable, but I don't know
if it is fun or good until we have either the Hong Kong scene or game mechanism."*

**Read as a pass on what `P0-5d` could actually test, and a rejection of its premise.** The
acceptance criterion was "the user drives it and confirms it feels good," and the handling cleared
it — no blocking problem, nothing that must be fixed before real geometry. But `PLAN.md` claimed the
grey box would answer "is this a game?", and it did not. Recorded as `Q8`, and the risk register
updated: `P0-5` is no longer a valid mitigation for "real geometry isn't fun to drive."

**Phase 1 is released.** The gate's purpose was to avoid sinking ETL effort into a game that does
not work; the user's answer is that the ETL output is a *precondition* for knowing. Continuing to
hold Phase 1 would deadlock the project.

**Deliberately not actioned:** the two feel items flagged during `P0-5d` — sustained full lock still
spins the car (`GAME_DESIGN.md:114` wants a drift that is easy to hold), and `brake_force = 900`
gives 3 m/s² of braking against 5.33 m/s² of acceleration, so **the car accelerates faster than it
stops**. Both are real, neither is blocking, and both belong with `P2-3`, which tunes the controller
against real geometry. Revisit them there rather than tuning twice.

### 2026-07-29 — `P0-4` ETL scaffold: config declares its **datum**, not just its CRS

The scaffold landed as planned — `pipeline/` package, `config/cities/hong_kong.yaml`, `crs.py`,
`ruff` and `pytest` — but building the round-trip tests turned up something that would have been an
expensive silent failure.

**HK1980 and WGS84 differ by ~304 m on the ground in Hong Kong.** Measured, not assumed: EPSG:2326's
own natural origin is published as 114°10′42.80″E, 22°18′43.68″N **on the HK1980 datum**, and feeding
those identical digits in as WGS84 lands 304 m away. That is a fifth of the width of the Wan Chai
region, and it is far larger than the ~10 m people expect from a datum shift.

The region bounds in `DATA_SOURCES.md` are quoted as bare lat/lon with **no datum stated**. Read off
any consumer web map they are WGS84; handed to the projection as HK1980 they would have placed the
entire region 304 m from the road data — with no error, no warning, and entirely plausible-looking
output. So `hong_kong.yaml` declares `crs.geodetic` alongside `crs.projected`, `config.py` refuses
to load without it, and `test_crs.py` asserts the two datums disagree by >250 m. That last assertion
is really a canary: if it ever shrinks, PROJ has fallen back to a **ballpark** transformation. It
has not — pyproj 3.7.2 / PROJ 9.5.1 selects the 7-parameter `Hong Kong 1980 to WGS 84 (1)` operation
at 1 m accuracy.

**Verification is against external facts, not the code's own output.** The load-bearing test projects
the published grid origin from EPSG:4611 and expects the published false easting/northing
(836694.05, 819069.80); it reproduces them to sub-millimetre. Corroboration: the config's bounds
project to 1649.0 × 885.9 m against a documented 1.65 km × 0.9 km, and to 66 tiles at 150 m against
a documented ~66.

**Other choices worth knowing:**
- `transformer()` is `@cache`d per CRS pair. Construction queries the PROJ database and costs
  milliseconds; the pipeline pushes millions of vertices through a handful of pairs.
- `always_xy=True` everywhere. EPSG:4326 officially declares lat-then-lon, and a silent axis swap
  is the classic way to relocate a city into the Indian Ocean.
- `GameTransform` is **pyproj-free** and pure arithmetic. The source CRS is already projected and
  metric, so the per-vertex hot path never re-enters PROJ, and the transform serialises into
  `city.json` as three numbers.
- The origin is **floored to whole metres**. Every tile boundary is measured from it, so inheriting
  the sixth decimal place of whatever PROJ release generated it would renumber every tile on a
  library upgrade.
- `deck_height_m()` raises on an unmapped `ELEVATION` rather than defaulting to 0.0 — a defaulted
  tunnel would be dragged to street level and invent a junction with the road above it.
- **Elevation-level keys reject `bool`, not just non-`int`.** Caught in review, reproduced, and now
  regression-tested. PyYAML implements YAML 1.1, where a bare `on`/`off`/`yes`/`no` key resolves to
  a boolean — and because `bool` subclasses `int` in Python, `isinstance(key, int)` waves it
  straight through. `False == 0` as a dict key, so a stray `off:` would silently redefine **ground
  level**. Verified: a config with a boolean key loaded without error and returned 42.0 m for
  level 1. One residual case is unreachable from here — writing both `1:` and `on:` in the same
  mapping collapses inside PyYAML before the loader sees either.
- Bounds are projected with pyproj's `transform_bounds` and edge densification, not by projecting
  four corners. A geodetic rectangle is not a rectangle once projected. Irrelevant at 1.5 km,
  wrong at city scale.
- Deps are only `pyproj` and `pyyaml`. GDAL/OGR and geopandas are heavy and platform-awkward and
  stay out until `P1-1` actually imports them.

**Surfaced, not fixed:** the data contract contradicts itself on the sign of game-space Z. See `Q7`.

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
| Real geometry isn't fun to drive | **High** | ⚠️ **Mitigation weakened.** `P0-5` was meant to retire this before any ETL investment; the user's verdict is that a grey box cannot answer it (`Q8`). The test did clear the *handling*, so the remaining risk is the city, not the car. Road widening and hand-added ramps are still the designed remedy, and `widen_factor` is already data. Next real check is the Phase 1 gate. |
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

### 2026-07-29 — `P0-4` ETL scaffold

`etl/` now exists: `pipeline/` package, `config/cities/hong_kong.yaml`, `crs.py`, `config.py`,
`pyproject.toml` with `ruff` and `pytest` configured, and `tests/`. **22 tests pass, `ruff check`
and `ruff format --check` clean.** Verified on Python 3.13.5 with pyproj 3.7.2 / PROJ 9.5.1.

The interesting finding is the ~304 m HK1980/WGS84 datum shift and the config change it forced —
full detail in the decision log. Two things came out of the same work:

- **`Q7` opened:** `ARCHITECTURE.md` states a conversion that puts game-space Z at ≤ 0 across the
  region, then shows a `bounds_game` example with positive Z. The formula is implemented and pinned
  by a test; the contradiction needs the user's call before `P1-6` writes a real `city.json`.
- **`hong_kong.yaml` carries the verified road source URLs** from `DATA_SOURCES.md` so `P1-1` does
  not rediscover them. Building sources are deliberately absent — those datasets expose no download
  endpoint at all (`Q3`).

Deliberately **not** built: `fetch.py`, `buildings.py`, `roads.py`, `tiles.py`, `export.py`. Those
are Phase 1 tasks with their own acceptance criteria, and stub modules would only be deleted.

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
