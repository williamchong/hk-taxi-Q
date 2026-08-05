# Progress

Living document. **Update this whenever a task changes status, a decision is made, or an open
question is answered.** Newest entries at the top of each log.

Last updated: 2026-08-05 (`P3-10` ships the ground, and it collides — `Q18`'s cheap half is on
screen and awaiting a verdict, and the drive opened `Q24`)

---

## Current status

**Phase 0 and Phase 1 are complete. Phase 2 is two hardware-blocked tasks from its gate.**

The ETL turns six government map sheets and one road geodatabase into a drivable Wan Chai in **3.0 s
from an empty `out/`**: 65 vertex-coloured tiles at two LOD tiers, 797 road edges over 615 nodes
with 217 turn restrictions, one 35k-triangle road surface with trimesh collision, and 29 fare nodes.
Godot streams it, the car drives it, and it exports to a 26.3 MB web PCK.

**Shipped in Phase 2, all five reviewed and passed:** `CityStreamer` (`P2-1`), `RoadGraph` (`P2-2`),
the queried start line (`P2-3`), the chase camera and building collision (`P2-5`), and the off-grade
carriageway on its real structure (`P2-7`). **Left:** `P2-4` (`InputRouter` across three input paths)
and `P2-6` (the perf pass) — both blocked on `P0-3b`, which needs a signing identity and the two
floor handsets. **Nothing on the critical path is blocked on software.**

**Phase 3 was refocused on 2026-08-02, and the next work is `P3-11`.** User's call: finish the Hong
Kong driving *experience* before any taxi gameplay element exists, so test players judge the scene on
its own. Builds now run **`B2` → `B1` → `B3` → `B4`**, `B2` gains a player taxi model (`P3-11`), and
`P3-9a` then puts that build in front of ≥3 HK drivers over a web link. Order, deps and acceptance
are in `PLAN.md`; why it was reordered and what it costs are in the decision log below.

**The premise is measured rather than assumed.** `Q8` closed on 2026-07-31 when the user drove the
real city: an HK-like map is a fun enough gimmick on its own. That retires the project's founding
risk and replaces it with a narrower one — *gimmick* is the user's own word, and a gimmick carries a
first session. "Novelty does not survive the first session" is now the live entry in the register,
and it is `P3-*`'s to answer.

**Two things are knowingly missing from the world, and one just arrived.** The **ground shipped** on
2026-08-05 (`P3-10`) — flat-coloured, untextured, merged into the tile primitive, and **solid**, so
leaving the carriageway now puts the car on the pavement instead of through it. Still missing: the
**elevated network is closed to driving** — `nearest_edge` refuses all 60 off-grade edges (`Q13`,
reopened deliberately in Phase 4) — and **nothing in the authenticity table is built**: no traffic,
no trams, no neon (`P3-3`, `P3-4`, `P3-8`).

### Task board

| ID | Task | Status | Notes |
|---|---|---|---|
| `P0-1` | Source data granularity | ✅ Done | 6 sheets, glTF per sheet ~44 MB. Buildings are scriptable; closed `Q2`, `Q3`, `Q5`. |
| `P0-2` | ⚠️ Z-value spike | ✅ Done | No Z, but `ELEVATION` encodes the level. Region holds. Closed `Q1`. |
| `P0-3` | Godot project scaffold | ✅ Done | Godot 4.7.1. macOS / web / Android export verified. |
| `P0-3b` | Mobile device build verification | ⬜ Not started | Needs a signing identity and the two floor handsets. Blocks `P2-4`'s and `P2-6`'s reviews. |
| `P0-4` | ETL scaffold | ✅ Done | `pipeline/` + `hong_kong.yaml`. Found the ~304 m datum trap. |
| `P0-5` | Grey-box fun test | ⚠️ Passed, conditional | Handling accepted; fun verdict deferred to `Q8`, which closed 2026-07-31. |
| `P0-5a` | └ Vehicle controller approach | ✅ Done | Custom raycast on `RigidBody3D`. `VehicleBody3D` measured and rejected. |
| `P0-5b/c/d` | └ Circuit, camera, drive test | ✅ Done | Circuit from JSON, spring-arm camera, driven. |
| `P1-1` | Source fetching | ✅ Done | Sheets derived from the published index, not listed. Idempotent. |
| `P1-2` | Building meshes | ✅ Done | 65 tiles; 989k → 434k → 222k triangles. Verified in-engine. |
| `P1-2t` | └ Terrain evaluation | ⚠️ Superseded | Judged unaffordable at 267 MB — but 224 MB of that was the JPEG. Replaced by `P3-10`, which ships no texture. |
| `P1-3` | Road graph | ✅ Done | 797 edges, 615 nodes, 217 turns, 96.3% connected. Closed `Q9`, `Q11`, `Q12`. |
| `P1-4` | Road surface mesh | ✅ Done | One mesh, one draw call, kerbs, trimesh collision. All 393 single-level junctions covered. Opened `Q13`. Two driver-reported defects fixed 2026-08-04: kerbs buried in a neighbour's carriageway, and the hull pinching the road at a bend. |
| `P1-5` | Fare nodes | ✅ Done | 29 nodes (14 stands, 6 cross-harbour; 15 PUDO) from 793 territory-wide points. Opened `Q14`, `Q15`. |
| `P1-6` | Export and manifest | ✅ Done | `city.json` + one-command pipeline; byte-reproducible. Opened `Q16`. |
| `P1-7` | Godot import | ✅ Done | **Phase 1 gate passed.** Georeferenced to 1 cm, checked in-engine. |
| `P2-1` | `CityStreamer` | ✅ Done — review passed | Threaded load/unload by published `aabb`. Draw calls 70 → 53; the review dropped the exact-weld tier, closing `Q16`. |
| `P2-2` | `RoadGraph` + debug overlay | ✅ Done — review passed | One parse per scene; p99 **45 µs** against a 1 ms budget. Refuses all 60 off-grade edges (`Q13`). Found the carriageway-width contract gap. |
| `P2-3` | Vehicle on real geometry | ✅ Done — review passed | `RoadSpawn` resolves the start line through `RoadGraph`; the hand-written transform is deleted. Verdict: *"car seems ok"*. |
| `P2-4` | `InputRouter` | ⬜ Not started | Touch, gamepad and keyboard → one action set. Its review needs `P0-3b`'s handset. |
| `P2-5` | Chase camera | ✅ Done — review passed | Unblocked by shipping building collision. No shape-cast needed. Opened `Q19`, `Q20`. |
| `P2-7` | Off-grade carriageway on its structure | ✅ Done — review passed | Deck heights sampled from `INFRASTRUCTURE`. \|error\| p90 **4.13 m → 0.095 m** against a 0.50 m criterion, graded against the shipped tiles by a tool sharing no code with the pipeline. Closed `Q20` and `Q23`, largely closed `Q13`, opened `Q21` and `Q22`. Nothing became drivable |
| `P2-6` | Performance pass to budget | ⬜ Not started | **Phase 2 gate.** Runs last because it measures the geometry that ships. Needs `P0-3b`. |
| `P3-11` / `P3-10` / `P3-7` / `P3-6` | Build `B2` — "it reads as HK" — **runs 1st** | 🟡 In progress | Taxi first (it is in every later screenshot), then ground (`Q18`), then the window shader, then the hero buildings. |
| `P3-11` | └ Player taxi model | 🟡 **Awaiting review** | Generated by `tools/make_vehicle.py`; **1,184 triangles** in scene across three `.glb`s (596 body, 4 × 144 tyres, 12 decal). Chassis taken from the scene, not chosen. Review shots in `build/driver/p311*`. |
| `P3-10` | └ Ground surface | 🟡 **Awaiting review** | Shipped 2026-08-05. Terrain is a tiled class: **+87,649 triangles** at LOD0, no texture, **no extra draw call**, **+4.56 MB of PCK**, and it **collides**. `ground_sink_m: 0.20` sized by `tools/ground_clearance.py`. Reads as ground on the flat core; **buries the carriageway on hill streets** — `Q24`. Shots in `build/driver/p310*`. |
| `P3-9a` | Recognition round 0 — the city, before the game | ⬜ Not started | ≥3 HK drivers on the `B2` web build. No HUD, nothing to do. Asks *do they know where they are*, and *did they keep driving anyway*. |
| `P3-1a` / `P3-5a` | Build `B1` — "one fare" — **runs 2nd** | ⬜ Not started | Fare state machine + deliberately ugly HUD. |
| `P3-3` / `P3-4` / `P3-8` / `P3-2a` | Build `B3` — "the streets are alive" — **runs 3rd** | ⬜ Not started | Traffic, trams, bus lanes, and near-miss scoring moved up from `B4`. |
| `P3-2b` / `P3-1b` / `P3-5b` | Build `B4` — "it's a game" — **runs 4th** | ⬜ Not started | Style chain, cross-harbour fares, full HUD. |
| `P3-9` | Authenticity test round 1 | ⬜ Not started | **Phase 3 gate.** ≥3 HK drivers on a handset, arrow disabled. Different drivers from `P3-9a` — that cohort has learnt the map. |
| `P4-*` | The elevated network | ⬜ Not started | Post-slice, but broken down: the data is measured and shipping collision half-opened the network by accident. Reverses `P2-2`'s refusal; closes `Q15`. |

Legend: ⬜ not started · 🟡 in progress · ✅ done · ⚠️ conditional · ❌ blocked

---

## Open questions

| # | Question | Impact | Owner | Status |
|---|---|---|---|---|
| `Q6` | Does the region need Central for the circuit to feel complete? | Scope | after `P3-9` | 🟡 Deferred |
| `Q13` | Nothing ramped between elevation levels; all 36 nodes joining two levels stepped by a whole deck height | 23.3% of carriageway area unreachable | `P2-2` → Phase 4 | 🟢 **Largely answered 2026-08-02.** All 36 are ramps — 17 junctions, 13 attribute flips, 5 tunnel portals, 1 stub; **no plan-coincident crossings.** After `P2-7`'s sampling the median step is **0.04 m** and 26 of 36 are inside 0.5 m. What remains is the 5 portals and the stub: a tunnel is a void, and their descent happens outside the region. Driving the network is `P4-1` |
| `Q14` | Taxi stands carry operating-time restrictions in `Status_EN` that `P1-5` discards | A part-time cross-harbour stand is modelled as full-time. `fares.json` has no field for it | `P3-1` | 🟡 Open — deferred deliberately. The source is fetched, so adding it is a schema bump plus a parser |
| `Q15` | Fare nodes snap by **plan distance only**, because the published points are 2D | A stand under a flyover cannot prefer the street below over the deck above. No Wan Chai node is affected — every winner is level 0, with a ≥4.28 m margin | `P4-2` | 🟡 Open — not reachable with this source |
| `Q18` | Does flat-coloured ground read as ground, or does it need land-cover colour classified from the source aerial JPEG? And does sinking terrain ~0.2 m under the road deck clear the carriageway on cross-slopes? | Decides whether `P3-10` stops after its cheap half or grows an image-decode stage and a **Pillow** dependency. Get the z-fighting half wrong and the ground fights every road in the region | `P3-10` | 🟢 **Second half answered 2026-08-05, first half awaiting the user's eye.** The 0.2 m guess measured to 0.2 m — **no z-fighting anywhere**, and the sink is the shallowest value that passes its gate. Whether flat *reads* is on screen in `build/driver/p310*` and is a verdict, not a measurement. What the sink does **not** fix is `Q24` |
| `Q24` | **The road is a plane and the ground is not**, so on 3.3% of carriageway area the ground stands in the road — up to **2.98 m**, which buries CAROLINE HILL ROAD outright | Cosmetic until 2026-08-05 and not cosmetic since: the ground collides, so this is solid geometry in legal carriageway, on top of `Q19`'s 5.17%. `P3-3`'s traffic will route into it | `P3-10` → decision | 🔴 **Open, and it is a `roads.py` question rather than a ground one.** Two mechanisms, both measured: `simplify` keeps 2.0% of source vertices so the road runs as a chord under curving ground (0.35% of centreline points proud within 1 m of a vertex, **5.78%** at 15–40 m), and the ribbon is flat across a width the 1.6× widening made too wide (2.27% at the centreline, **5.39%** at the outer rim). **`P2-7` already solved the first for off-grade edges** by densifying with `resample`; level-0 edges get it only where they were lifted onto a ramp. The fix moves at-grade drivable geometry, which is the user's call — as it was in `P2-7` |
| `Q19` | **5.17% of drawn carriageway has solid geometry standing in it at bumper height.** At grade: `BUILDING` 1.72%, `INFRASTRUCTURE` 1.60%. A further 1.87% is on off-grade ribbon nobody can reach | The car is stopped by invisible walls on legal carriageway, and `P3-3`'s traffic will route into them. Cosmetic until collision shipped on 2026-08-01 | `P3-3` | 🔴 Open. The `BUILDING` half is the 1.6× widening eating the frontage — a playability trade, not a bug. The `INFRASTRUCTURE` half shrinks with `Q20`. **Wants a verify tool that fails the build when the carriageway is occupied** |
| `Q21` | **Should level −1 carriageway be drawn at all?** 15 edges, 5,010 m, **11.6% of carriageway area**, ribboned under the terrain where nothing can see it and nobody can drive it — and solid since collision shipped | Triangles, collider surface and bundle bytes for geometry with no viewer. Against: `P3-3` and Phase 4 want the *edges* to exist, and `roadgraph.json` would keep all 15 either way | Phase 4 | 🟡 Open. `P2-7` could not improve their height — a tunnel is a void — and **11 of their 30 ends are clipped at the region boundary**, so the Cross-Harbour portals have ~42 m of run for an 8 m descent |
| `Q22` | **10.2% of off-grade carriageway still hangs past its structure**, after narrowing took it from 20.1% | Cosmetic while nothing off-grade is drivable. It stops being cosmetic in Phase 4: a wheel leaving the deck finds air, not a parapet | Phase 4 | 🟡 Open. No width rule reaches the rest — a single-lane ramp is drawn at the two-lane default, a source centreline is not always centred on its deck, and `P2-1` decimates `INFRASTRUCTURE` on a 0.5 m cell. `tools/overhang.py` is the committed instrument; it reads 10.0% against the 10.2% recorded by hand |

**Resolved:** `Q1` (no Z, but `ELEVATION` encodes the level) · `Q2`/`Q3`/`Q5` (building data is fully
scriptable; 6 sheets, ~44 MB each) · `Q4` (device floor A13 / Adreno 618) · `Q7` (origin at the
region's NW corner) · `Q8` (the city itself is the fun) · `Q9` (read the 17 MB geodatabase, not the
539 MB of GML) · `Q10` (local origin **plus** a recorded `city_offset`) · `Q11` (sample the terrain
height field) · `Q12` (the source's one-way directions match the street) · `Q16` (LOD0 does not
ship; PCK 51.6 → 21.1 MB) · `Q17` (CI runs `tools/check.sh`) · `Q20` (sample the deck; \|error\| p90
4.13 → 0.095 m) · `Q23` (width per station, with a taper). Each is written up in the decision log.

### `Q18` — deliberately asked in the order that might avoid answering it

`P3-10` ships flat-coloured decimated terrain **first** and looks at it. The classification pass —
sample the 45 MPix source JPEG per triangle, snap to a land-cover palette, put the class in
`mesh.collapse`'s cluster key so boundaries stay crisp — is real work with a **Pillow** dependency
behind it, and the flat version is the screenshot that says whether it is needed. If flat reads
fine, the question closes without the code ever being written. *Art of Rally* ships flat-shaded
untextured terrain as its finished look; that is evidence rather than proof, since it is open
countryside and Wan Chai is dense. What it buys is an order of investigation: **if the first pass
reads dead, tune the palette before reaching for the classifier.**

The second half is not a matter of taste. `roads.py` places the level-0 ribbon at `terrain + 0.0`,
so ground and carriageway are **coplanar by construction** and will z-fight across the whole
network. The 0.15 m kerb riser and 0.5 m lip `P1-4` already draws are what a sunken terrain tucks
under, and ~0.2 m is a guess until it is driven on a cross-sloped street.

---

## Decision log

### 2026-08-05 — `P3-10`: the ground ships, it collides, and it found a defect in the road

**Terrain became one more entry in `buildings.classes`.** That is the whole design: being a class
gets it the tile's single material for free, so it costs **no draw call**, and it cannot end up
somewhere the buildings are not. `_ground` strips the texture and sinks it on the way in.

| | before | after |
|---|---|---|
| LOD0 triangles | 434,149 | **521,798** (+87,649) |
| LOD1 triangles | 222,375 | **253,070** |
| Tiles | 65 | **66** — ground reaches a corner no building did |
| `bounds_game` | 1668 × 942 m | **1728 × 977 m** |
| Draw calls per tile | 1 | **1** |
| Worst resident triangles | 236,882 | **280,807** |
| **PCK** | **27.73 MB** | **32.30 MB** (+4.56) |

⚠️ **The PCK grew nearly twice what `ART_DESIGN.md` predicted, and the collider is the difference.**
The estimate was 1.5–2.5 MB and counted geometry. Measured from a PCK, one variable changed, as this
file's own rule requires — and the split between geometry and `ConcavePolygonShape3D` was *not*
separately measured, so it is not quoted.

**The ground collides, and that was a decision rather than an inheritance.** `ART_DESIGN.md` said
the first pass was "visual only, with no collider" while two other lines promised it merged into the
tile primitive for "+0 draw calls". **Those were never compatible**: `_write_tile` names the merged
tier-0 mesh `<tile_id>-col`, so anything merged into it is solid. User's call: merged and solid.
Ground you can see and fall through is worse than no ground for a free-roam recognition test, and
the driver run confirms the car now mounts the kerb and keeps driving where it used to fall 25 m and
respawn. **The standing consequence is in `ARCHITECTURE.md`, not here:** any future class added to
`classes` inherits tier-0 collision whether or not it asked.

**`ground_sink_m: 0.20` — the guess and the measurement agreed, which is not the same as not
measuring.** `roads.py` lays the level-0 ribbon at `terrain + 0.0`, so the two surfaces are coplanar
by construction; `tools/ground_clearance.py` sized the drop the way `deck.clearance_m` was sized:

| sink | of carriageway area proud | of sampled points proud |
|---|---|---|
| 0.00 | 47.5% | 49.9% |
| 0.15 | 5.2% | 0.97% |
| **0.20** | **3.3%** | **0.36%** |
| 0.35 | 1.2% | 0.12% |

0.20 is the shallowest value passing both gates, and deeper costs a visible gap under a 0.15 m
riser. **No z-fighting was found anywhere in the region**, which is `Q18`'s second half closed.

#### The finding: shipping ground did not create a defect, it revealed one

⚠️ **3.3% of carriageway area has ground standing in it, up to 2.98 m — and none of it is the
ground's fault.** The drive is unambiguous: on **CAROLINE HILL ROAD** the carriageway is simply
gone, buried, with the asphalt emerging as a fragment. The same on YAT SIN STREET, JARDINE'S
CRESCENT, WAN CHAI ROAD. On the flat core — Hennessy, Gloucester, Harbour — the ground reads
correctly and tucks under the kerb.

**The road is a plane and the ground is not**, in both directions, and both were measured rather
than argued:

- **Along its length.** `simplify` keeps **2.0%** of the source vertices (175,610 → 3,553), so the
  road runs as a straight chord over ground that curves. **0.35%** of centreline points are proud
  within a metre of a retained vertex against **5.78%** at 15–40 m from one; 0.58% on segments under
  20 m against 3.66% on segments of 50–100 m.
- **Across its width.** The ribbon is extruded flat from one centreline height, so a cross-sloped
  street rises into it at the kerb: **2.27%** proud at the centreline against **5.39%** at the outer
  rim — and the outer rim is where `Q19`'s 1.6× widening put carriageway on top of the frontage.

⚠️ **Three explanations were measured and rejected before this one**, each of which would have sent
the fix somewhere useless:

1. **Tile decimation.** The obvious suspect, and `P2-7`'s precedent — 0.5 m cells lifted the shipped
   deck +0.339 m at worst. Measured at the 4 m ground cell: median **+0.000**, p99 **+0.155**, max
   +0.680, and only **0.44%** of centreline vertices lifted past the sink. It is inside the sink,
   not the cause.
2. **The sink being too shallow.** Refuted by the table above: at the points the road's height was
   actually sampled from, 0.20 m already reads 0.36%. A sink deep enough to clear 2.98 m would put
   the ground below every kerb in the region.
3. **The tunnel portals.** The worst *edges* included two CROSS HARBOUR TUNNEL approaches descending
   to y −3.6, which looks like the whole story until the area is counted: the tail is spread across
   ordinary hill streets, not concentrated at the portals.

⚠️ **The first measurement was taken at polyline vertices and came back clean**, which is exactly
where a chord error is zero by construction. It read median +0.000 and would have closed the
question. What exposed it was asking the same thing *between* vertices — the answer changed by a
factor of sixteen. **A probe placed where the geometry is defined cannot see a defect that lives
between definitions.**

**`P2-7` already solved this half of it, for other edges.** Its densification note — *"the case for
10 m resampling is the 4.84 m max, all of it on `e118` FLEMING ROAD where a 71.5 m vertex gap spans
structure climbing 4.25 → 5.05 m — precisely the defect the user drove into"* — is the same defect,
and `resample` is the same fix. Level-0 edges get it only where they were lifted onto a ramp.
**Deliberately not done here**: it moves at-grade drivable geometry, which is the call `P2-7`
escalated rather than take, and `P3-10`'s scope is the ground. `Q24` holds it.

#### The tool, and the trap it was built around

`tools/ground_clearance.py` joins `deck_error.py` and `overhang.py`: reads only the shipped bundle,
finds ground by **vertex colour** rather than by sheet sub-directory, and takes the road from
`roads.glb` rather than from the graph.

⚠️ **It gates the sink on a different population from the one it reports first**, because the two
measure different defects and blending them makes the sink unfalsifiable. The gate is the share of
**points the road's height was sampled from** — the centreline at a retained vertex, where the sink
and the decimation are the only things between the surfaces. The headline share over all cells
carries `Q24` as well and is a regression bar, not a standard. A single number would have read 3.3%,
looked like a failing sink, and sent the next person to deepen it.

⚠️ **`deck_error.py` was a real regression risk and is not one.** It identifies structure by testing
a jitter *ray* through `#9d9a93`, so adding a second grey class to the same tiles is precisely the
input that could over-match. Measured: **16,554 upward faces before and after**, byte-identical, and
\|error\| p90 0.094 against the recorded 0.095. `overhang.py` still reads 10.0%. Both were run
because the rule says to, and one of them could have failed.

**A latent bug fixed in passing:** `structure_faces` read the global `colour_jitter` where per-class
overrides now exist. The two agree for Hong Kong, so nothing was wrong — but `_wears` is exact about
the interval it tests, and a class with its own jitter would have silently changed what counts as
structure.

**No `schema_version` bumped.** Nothing was added, removed or renamed and no attribute changed
meaning: a consumer keeping its old interpretation of a tile is not wrong, it simply draws more.

### 2026-08-04 — Two road defects reported from the driver's seat, and both were `P1-4` treating each edge alone

The user reported a **white line down the middle of a road, with collision, that threw the car**, and
**junctions narrower than the roads meeting them, with straight roads shrinking unexpectedly**. They
are one root cause: `surface.py` extrudes every graph edge into its own ribbon with its own kerbs and
never asks what the neighbours did.

**The white line is a kerb.** There are no lane markings yet — `ART_DESIGN.md` defers those to a
shader. It is `kerb_colour` `#9a968d` against `#3c3a37` asphalt, 0.5 m wide and 0.15 m tall. It lies
mid-road because a dual carriageway is two edges, each kerbed on both sides, and `hong_kong.yaml`
chose `widen_default: 1.6` *precisely so* those pairs overlap "into a single continuous surface". The
tarmac merges; the kerbs come along. **Measured at 33.0 km of 98.6 km of kerb line — 33%** — worst on
GLOUCESTER, VICTORIA PARK, HENNESSY and LOCKHART.

⚠️ **Not cosmetic, and the reason is two facts that were each recorded correctly and never put
together.** The mesh ships as `road_surface-col`, so Godot builds one trimesh collider over
everything including the kerb risers; and `handling.tres` allows `suspension_travel_m = 0.18`. A
0.15 m step is **83% of the car's total bump travel**, which is why a lane-three kerb launches it.
`drive_harness.gd` calls the kerbs "mountable by design" and they are — that reasoning just never
anticipated meeting one in the middle of a road.

**The junction pinch is the convex hull.** `_cap_ring` trimmed each arm back by a full half-width —
10.2 m of road replaced by a cap at every node on a standard street — and filled the gap with the
hull of the arm mouths. At a bend the hull's straight chord cuts the outside of the turn off and the
road narrows to `cos(half the turn)` of its width. BULLOCK LANE into CROSS LANE, 62 degrees, left a
**7.1 m waist between two 10.2 m arms**; THOMSON ROAD into O'BRIEN ROAD lost 3.2 m on a turn of only
11.4 degrees, which is the "straight road shrinks" report exactly. 8 of the 49 two-arm nodes were
narrower at the node than their own thinner arm.

**This was already in this file and had been read as cosmetic.** The 2026-08-01 shadow entry records
"the dark wedges at junctions … are **not shadows and not the missing terrain**. They are gaps in the
road mesh", filed as "a `P1-4` coverage question, worth taking before `P3-9`". It reached the driver
first.

| | before | after |
|---|---|---|
| Two-arm nodes narrower than their own arms | 8 of 49 | **1 of 49** |
| Kerb line lying inside another carriageway | 33.0 km | **0** |
| Movements mitred through their cap | — | 677 |
| Triangles | 35,039 | **25,028** (−29%) |
| `roads.glb` | 1.8 MB | **1.3 MB** |
| `build_region` | 0.30 s | **0.36 s** (2.49 s as first written — see below) |

⚠️ **No bundle figure here on purpose.** The obvious one to quote is `export.py`'s "MB shipped", and
it is a **sum of source files** — the number this file's own Metrics rule forbids, and the one that
cost `Q16` two wrong answers. The PCK was measured instead and is recorded in Metrics; the road
surface is one asset of 134 in it, and `P3-11` landed a taxi since the last reading, so no part of
that delta is attributable to this work.

**The mitre apexes go into the same hull as the mouths**, rather than building a second kind of cap.
A hull can only grow, and a straight through movement puts its apex on the boundary the hull already
had — so a crossroads is unchanged and there is still one cap with one construction. What qualifies
as "through" is the whole question and it is **not** a tuning value: two arms at a node is one street
bending, so the corner is carriageway and up to 90 degrees is mitred; three or more and a sharp
corner is the pavement between two streets, so the limit drops to 45. Filling that corner would pave
the footpath, which is what `hull` was chosen to avoid in the first place.

The one node still pinched is a **172-degree hairpin**, and no mitre should reach it.

**Rejected: merging opposed pairs into one ribbon.** It is the tempting read of the kerb bug, and it
would reopen a decision this module's docstring closed with measurements — plus it needs polygon
clipping and would change what `roadsurface.json` indexes. Only the *kerb* asks about its neighbours;
the carriageway is untouched, so no collider gains a hole and `carriageway[].half_width_m` still
means what it meant. **No schema bump**: a consumer keeping its old interpretation stays right.

⚠️ **The overlap test is on the outer lip, and per segment rather than per station.** A kerb whose
far edge is still inside a neighbour is swallowed; one the neighbour merely reaches into is a real
boundary between two surfaces and keeps its kerb. And a station lands exactly on a neighbour's
boundary at every arm of every plain crossroads — a crossing-number test calls a boundary point
inside, and one such touch would have taken the entire kerb of a two-station edge. `testville` caught
that within a minute of the first run; the region would have hidden it in the aggregate.

⚠️ **The first cut of the overlap test made the stage 8.3× slower and nobody would have noticed.**
It ran, the output was right, every check passed — and `build_region` went from 0.30 s to **2.49 s**,
against a module docstring that sells the graph input as "what lets this stage run in a second". A
review pass caught it: `_within` was **86% of the whole stage**, from a Python loop over polygon
vertices that the file's own style forbids (`boundary` earns its scalar walk with a measurement; this
had none), and from 476,000 `np.errstate` context managers — **15% of the stage on their own** —
guarding a division whose result was masked away. Vectorising the test, deduplicating candidates
found through more than one grid cell (29% of them), and rejecting by bounding box first (65% of
them) brought it to **0.36 s**. Correctness is unchanged: the polygon test agrees with the old one on
39,048 samples with **zero** disagreements.

The **3 triangles** that moved are the mitre apex now coming from `mitres` — the same construction
the function had been carrying a private copy of, `_MITRE_LIMIT` included. The two agree to
**1.0e-13**, which is enough to drop three hull points that were colinear at that scale. Sub-picometre
drift, and worth it to stop the mitre policy living in two places.

**Still open, deliberately.** The cap carries **no kerb and no lane coordinate** — `fan` writes zero
UVs. Both were true before and neither is what was reported. `ART_DESIGN.md` already has the second
one written up as the junction defect the markings shader will expose; nothing here changes it.

### 2026-08-03 — `P3-11` review: **reads as 紅的, does not read as a Crown Comfort**

**Verdict, from the user.** The colour split (red body, pale roof) carries the most basic signature
of a Hong Kong urban taxi, and the model works **as a placeholder** — a viewer sees "香港紅的" at a
glance. It does **not** read as a Toyota Crown Comfort, and specifically not as the **4-seat**
variant. Answering `PLAN.md`'s question *"does it read as a toy in an accurate city, rather than as a
box?"*: **a toy, yes; the right toy, not yet.**

The findings split into two kinds of work, and the split is the useful part.

**Texture, not geometry — and this is where the recognition actually lives:**
- ⚠️ **The green semicircular badge.** The user's word is *必定* — a 4-seat taxi always carries it,
  and it is **the** marker that identifies the variant. Nothing in the project knew it existed.
  **Corrected from the reference photo: it reads 「TAXI / 4 / SEATS」 in English, not 「4座位」**, on
  a white-edged green half-ellipse, and it sits on the **bumper** — front and rear, not the boot.
  That correction mattered technically as well as factually: English is a 7-glyph bitmap font, where
  Chinese would have meant hand-encoding 24×24 bitmaps per character.
- **"TAXI" lettering** on the roof sign's long sides.
- **Registration plates, and they are two different colours.** Hong Kong follows the UK: **white at
  the front, yellow at the rear**, black characters. Shipping both white would be a detail a local
  eye catches instantly.

**Geometry:**
- The whole body is too hard-edged. A real Crown Comfort is a square three-box saloon, but its
  front, roof and rear *transitions are radiused*, and its bonnet and boot are proportionally longer.
- The roof reads as a flat pale slab laid on top of the red, rather than silver paint that covers the
  roof **and continues down the A/B/C pillars**. The glass needs real inset depth against the body.
- The roof sign is a plain cuboid; the real one is a specific solid — semi-elliptical, or a
  rectangle with a rake.
- Tail lamps want the signature upright cluster; the plate wants a recess.
- Wheels read as dark blobs with no rim.

⚠️ **The mirrors, door handles, shut lines, pillars and silver hubs are already modelled** — the user
listed them as missing. They are 16–150 mm features seen from ~8 m in a 1080p frame in flyover
shadow, so they are sub-pixel and contrast-free. **Detail that cannot be seen at review distance is
not detail, it is triangles.** The fix is to make them read — larger, higher contrast, or moved into
a texture — not to add them again. Worth remembering before spending the rest of the budget the same
way.

**This earns the texture half that `Q18`'s pattern deliberately deferred.** The cheap version shipped
and got looked at, and the answer came back that the highest-value remaining items — 「4座位」 and
「TAXI」 — are *text and decals*, unreachable in flat triangles at any triangle count. The blocker
stands: `pipeline/mesh.py`'s `merge` refuses textured meshes, so it needs per-part UVs into an atlas.

### 2026-08-03 — `P3-11b`: the review's notes, answered

**Built in response to the verdict above.** 1,184 triangles in scene — 596 body, 4 × 144 tyres,
12 decal — against `ART_DESIGN.md`'s 2,000 ceiling.

⚠️ **The loop was broken for most of a session, and every conclusion drawn in it was wrong.**
`drive.sh` builds `game/.godot/` on its first run and thereafter renders **whatever is already
imported**. Rewrite a `.glb` and every screenshot afterwards is of the *old* mesh, silently, with
`DRIVER OK` and an exit code of zero. Three diagnoses in a row were made against hours-stale images:
geometry was removed, the render did not change, and the removed geometry was cleared of blame for
something still on screen. **The tell was a probe that came back pixel-identical** — a change that
produces literally no difference is far likelier to mean "the change never arrived" than "the change
had no effect". Fixed in the skill's gotchas: run `godot --headless --path game --import` before
believing any screenshot. The stick artefacts had in fact been gone for four edits.

**Wheel width, third value and the two failures worth keeping.** `half_width_m` went 0.86 → 0.76 →
**0.90**. At 0.86 the tyres were sealed inside the bodywork and the car rendered with no wheels. At
0.76 they were visible but stood *outside* the flank on a perched lip — which the user read
immediately as *"some kind of vintage car"*, because standing fenders are a pre-war arrangement, not
a 1990s saloon. Only flush bodywork with the wheel in a hole cut through it is neither, and that is
what `_flank` now builds: solid stretches between the openings, an arc of columns over each tyre, a
rim turning inward and an inner wall so the well has a back to it.

**Rounded, by chamfer rather than by smoothing.** `_ring` grew a corner cut, so every vertical edge
is three short facets instead of one 90° turn, and `_loft` became generic over N-gon rings to carry
it. This was the correction to a caution recorded earlier in this log — that bevels would fight the
flat-shaded city. **They do not.** The user's own reference art is rounded *and* flat, and the
distinction that matters is chamfer versus smooth shading: faces stay flat, edges stay crisp, there
are simply more of them. `corner_cut_m = 0` still yields the cheap square car `B3`'s traffic wants.

**The tail lamp is three lenses, not one.** Amber indicator over white reverse over red tail and
brake, in that order. An earlier pass had a single cream lens — a *white tail lamp*, which is simply
wrong — adopted because a red lens on red bodywork vanishes. The real fix was the dark bezel, and
then the correct colour on top of it. ⚠️ **This took the palette to six**, where `ART_DESIGN.md` says
3–5: three stacked lenses cannot be expressed in two colours. Flagged rather than quietly taken.

⚠️ **The glTF importer silently reinstated `VehicleWheel3D`, the class `P0-5a` rejected** — through
nothing but the mesh being named `taxi_wheel`. **The mechanism and the suffix list live in
`ARCHITECTURE.md`**, under their own heading, because they are a standing property of the importer
rather than an event. What belongs here is what it cost: the wheels stopped drawing with a clean
import, a passing `check.sh` and a `DRIVER OK`, and the disappearance was blamed on body width twice
before anyone inspected the instantiated *tree* rather than the scene *file*. **Everything upstream
of instantiation was consistent and wrong together**, which is precisely why reading the source
could not find it.

**`VehicleBody3D` re-asked, and re-refused — 2026-08-03.** The user asked directly whether the
built-in vehicle would give us anything, which is the explicit instruction hard rule 1 requires to
reopen a locked decision. It genuinely would: per-wheel angular velocity for wheelspin and lockup,
`get_skidinfo()` for smoke and tyre marks, and ~340 lines of `vehicle_controller.gd` deleted. It is
still refused, and the reason is a capability gap rather than a preference — `VehicleWheel3D` exposes
**one** `friction_slip`, and Godot's implementation derives lateral and longitudinal impulses from
it, so it cannot break lateral grip while keeping traction. `handling.tres` carries four drift dials
with no counterpart there, and `GAME_DESIGN.md` builds the style chain on the mechanic they tune.
"Wheels only" is not available either: `VehicleWheel3D` simulates solely under a `VehicleBody3D`.
**The two features worth having are cheap to build here instead** — `_apply_tyre_forces` already
computes the slip both need — and are scheduled into `B4` beside the effects that consume them.

⚠️ **The review round found four defects the build could not, and one had shipped.** Recorded
because each was invisible to every check that passes:

- **The roof-sign TAXI decal was buried inside the sign** — both quads at `x = 0`, coincident with
  each other, 13 cm inside opaque geometry. The lettering had never rendered once. Nothing catches a
  decal *strictly inside* the body, and the cause was that the sign tapered in width, so no flat quad
  could lie on its side. It rakes across its width now and the lettering faces fore and aft, which is
  where the real sign carries it **and** the only face the chase camera ever sees.
- **The flank stood 0.24 m proud of the chamfer** at each lower corner — a flat red fin cancelling
  the `corner_cut_m` rounding it poked through, because `_flank` ran the full body length while the
  rings it patches into are chamfered. The bumpers' side faces were also *exactly* coplanar with the
  flank plane, giving four z-fighting patches.
- **`corner_cut_m = 0` opened a hole through the boot.** The flank edge indices were pinned to `(2,
  6)`, correct only for the eight-corner ring; at zero cut a ring has four corners and edge 2 is the
  *rear face*. Since zero is the setting offered to `B3`'s traffic, this was armed for later.
- **`_text` had no bounds check**, and negative numpy slice indices wrap: a plate one character too
  long wrote 162 ink pixels *inside the 4 SEATS badge*, silently.

**The lesson is the same one this task keeps teaching.** Every one of these rendered, imported and
passed `check.sh`. What found them was reading the *built mesh* — its vertex positions, its coplanar
faces, its triangle count at a different dial setting — rather than the source that produced it.

**Decals ship as a third mesh, and the `merge` blocker dissolved.** The earlier note here said
textures needed per-part UVs across all 87 body parts, because `pipeline/mesh.py`'s `merge` refuses
textured meshes. That was solving the wrong problem: the *body* never needed texturing. Six quads
carrying a 256² sheet do, and they never touch `merge` — `write_glb` simply takes a third entry.
`tools/vehicle_decals.py` draws the sheet with `zlib` and `struct` alone, so **Pillow is still not a
dependency**, and bakes each decal's surroundings into its own patch so no alpha channel is needed
(the writer sets no blend mode). Cost: a third material, and 12 triangles.

### 2026-08-03 — `P3-11`: the taxi is generated, and the chassis generates it

**Built and reviewed — see the verdict above.** `tools/make_vehicle.py` → `taxi_body.glb` (484 tris) and
`taxi_wheel.glb` (72), which the scene instances as **484 + 4 x 72 = 772 triangles**, 31 KB and 7 KB
on disk. Two meshes, so two materials, and five flat colours — inside `ART_DESIGN.md`'s 1–2 and 3–5.

**The chassis is an input, and that is the whole design.** `Chassis` mirrors the `WheelMount`
markers and `handling.tres` rather than proposing geometry of its own, so the mesh is built *around*
hardpoints `P0-5` tuned against. The desync this avoids is the nastiest kind — the physics never
reads a mesh, so a model built to its own wheelbase looks right, drives to the old tuning, and shows
nothing wrong in a drive. `test_make_vehicle.py` parses the shipped `.tscn` and `.tres` and fails if
the two ever part company. **The scene is the authority; the generator follows.**

⚠️ **The guard shipped with a hole in it, found by review rather than by use.** The wheel meshes were
parented at an authored `-0.35` offset — a fourth copy of `suspension_rest_length_m`, in four places
— and the guard filtered on the `WheelMount` script id, so it never looked at those nodes. Retuning
the spring would have moved the raycasts and left the meshes behind, which is *precisely* the failure
the whole design exists to prevent. `wheel_visual.gd` now reads the rest length from the profile and
the scene carries no offset at all; a test asserts no wheel visual re-authors one. **A guard is only
as good as the copies it knows about**, and the one it missed was the copy the renderer actually
used.

⚠️ **Two bugs that no test would have caught, both found by looking at the render.**
- **The wheel was wound inside-out.** Every tread normal pointed at the axle, which backface culling
  draws as a wheel-shaped hole. It passed the triangle count, the file size and `check.sh`.
- **The wheels were sealed inside the bodywork.** They reach x 0.90 and the arch lip reached 0.91,
  so the first render was a car with no wheels at all — and the *numbers* all looked healthy. Fixed
  by narrowing the body to 0.76 half-width so the wheels stand proud, which is the toy read anyway.
  A real Crown Comfort hides its wheels in wells cut into a wider body; wells cost a segmented flank
  and buy nothing at this scale.

Recorded because `PLAN.md` already says a green driver run is not a rendered game, and this is the
second time that has been literally true — the first was `P2-7`, whose three review findings were
each *"found by a drive and by no internal number."*

**A third defect, found the same way and fixed the same way:** the cap triangles were faked as quads
with two coincident corners, so their normal came out of a zero-length edge. `_polygon` now takes
3+ corners and **refuses a face with no area** rather than writing one.

**Triangle budget: `ART_DESIGN.md`'s 800–2,000 stands, and the model came up to meet it.** The first
pass was 384 — comfortably under, and cheaper for `B3`'s roster. User's call was to spend the
triangles rather than lower the spec, so the arches became swept bands, the wheels went 12 → 18
segments, and the flanks gained pillars, door shuts, handles, sills and grille slats: 772. The
detail knobs are `Proportions` fields, **so `B3` can still instance a cheap variant** by passing
fewer segments — which is the answer to the objection that a heavier player car makes traffic
expensive.

**Textures deliberately not done.** The writer already supports them — `MeshData` carries `uvs` and
`texture`, and `write_glb` emits `TEXCOORD_0` and a `baseColorTexture` — and the bundle has 174 MB
spare against a 26.3 MB PCK, so cost is not the objection. What stops it is that
`pipeline/mesh.py`'s `merge` **refuses textured meshes outright** ("that needs a UV atlas"), and the
body is **87 merged parts**. Doing it properly means per-part UVs packed into an atlas. Held back on
`Q18`'s pattern: ship the cheap half, look at it, and only then decide whether the expensive half is
earned. The prize if it is: 的士 on the roof sign, which is the single most Hong Kong thing the car
could carry and is unreachable in flat triangles.

⚠️ **The visual body is not the collider, and the collider did not move.** `P0-5a` rejected a
trimesh player collider and `P0-5` tuned against the 1.8 x 0.7 x 4.0 box, so `P3-11` left it alone.
The mesh is larger on every axis — 1.90 x 1.34 x 4.12. That is the safe direction — the car never
reads as clipping before the box has actually touched something — but it does mean the visible roof
can pass under geometry the collider would have stopped. Worth a look when `P2-6` measures.

### 2026-08-02 — Phase 3 refocused: **the city gets finished, and tested, before any taxi gameplay**

**User's call.** Build the complete Hong Kong driving experience — and a taxi worth looking at —
before a fare, a HUD or a score exists, then put it in front of test players. Builds run
**`B2` → `B1` → `B3` → `B4`**. Scope was considered and deliberately held to `B2`: traffic and trams
stay in `B3`, so the streets tested will be empty ones. **`PLAN.md` holds the new order, the deps and
the acceptance criteria**; what belongs here is what the reorder decided elsewhere, what it uncovered,
and what it costs.

**The build letters were not renumbered, and that was the deliberate part.** `B1`…`B4` name content;
running order is stated separately wherever the two disagree. This is `P2-7`'s convention — *"the one
place where ID order and running order disagree"* — extended rather than invented. Renumbering would
have been tidier for a reader starting today and would have silently falsified a dozen existing
entries, including this log's own "`P3-10`, build `B2`" and the risk register's "already authored for
`B3`". **A plan that edits its own history to look consistent stops being usable as a record.**

**The reorder exposed a task that never existed.** `ART_DESIGN.md` specifies a vehicle roster, toy
proportions and an 800–2,000 triangle budget, and `GAME_DESIGN.md` builds a genre on *"accurate city,
toy vehicles"* — but no Phase 3 task delivered the player's own car. It is still `taxi.tscn`'s two
`BoxMesh` primitives, **24 triangles**, from the `P0-5` grey box. Nobody noticed because the docs
describe the car so thoroughly that it reads as decided, and **a decided thing looks like a done
thing.**

⚠️ **This is `P2-5`'s gap a second time, and `PLAN.md` predicted it.** `P2-5` was blocked on building
collision that `P2-1` had correctly declined to own, and the note written then ends *"worth a glance
at the other acceptance criteria for the same shape."* Nobody took the glance. The rule that would
have caught both: **a capability named only in a design doc has no owner.** Dependency graphs link
tasks to tasks, and neither the collision nor the taxi was ever a task to depend on.

⚠️ **What the reorder costs.** `B1` was first because *"is completing a fare worth doing twice?"* is
cheap to answer and expensive to get wrong; it is now answered on a city already built, so if the
fare loop turns out to want something different of the world, `B2`'s art is already spent. Against
that: `Q8` closed on *"the city itself is the fun"* with **one** person's drive behind it, and every
downstream build rests on it. The user judged the unverified premise the larger risk. **`P3-9a`'s
second question is where that judgement gets checked** — a city with no fares, traffic or score is
the harshest form of "does novelty survive the first session", and **how long each driver keeps going
before stopping is the number to write down.**

### 2026-08-02 — Licensing: **GPLv3 out, MIT in, and the generated data is nobody's to relicense**

User's call: **GPL-3.0-or-later** for code. **`LICENSING.md` is the standing policy** — the split, the
quoted terms and the review items live there, not here. What belongs in the log is why the choice
constrained two other things, and what re-reading the terms corrected.

**The licence choice decided the contribution policy.** GPLv3 cannot ship through the App Store, so
store builds need a separate proprietary grant — which works only while one party owns the whole
copyright. A single GPL-only patch would close the iOS route permanently, as it did for VLC. Hence
`CONTRIBUTING.md` taking contributions **inbound MIT**: it permits sublicensing, which is the exact
property that keeps dual licensing available, at far less friction than a signed CLA. No exposure
today, and **no retrofit** once a contributor declines — so the file lands before the repo is public.

**Reading the terms verbatim corrected `DATA_SOURCES.md` in two places.** The grant is permissive —
six acts, commercial use explicit, **no usage limit, quota or volume cap of any kind**, so player
count consumes no government allowance (the game makes no runtime calls anyway). But the attribution
requirement is **stronger than the credits draft had it**: it demands acknowledging *ownership of the
intellectual property rights*, not merely naming a source, and **both portals** must be named. The
draft is corrected and hard rule 6 now says so.

⚠️ **One false alarm, recorded so it is not re-raised.** Neither portal's grant contains "adapt",
"modify" or "derivative", which looked alarming for a pipeline that does nothing but derive geometry.
It is expected: **"adaptation" is a term of art** attaching to literary, dramatic and musical works,
and for artistic works the restricted act is *copying* — which expressly covers 2D↔3D transformation
and is granted here as **reproduce**. The alarm came from grepping for a word rather than from the
structure of the right, and the user's objection that an open-data portal forbidding derivation would
be absurd was better grounded than the keyword search. Landmark depiction, not adaptation, is the top
item for legal review.

### 2026-08-02 — `P2-7` closed: the off-grade carriageway lies on its structure

> Collapsed from ten dated entries (steps 0–8a, the two review findings, and `Q23`) once the review
> drive passed. The per-step narrative is in the git history; kept here is every measurement and
> every trap that would otherwise be re-derived.

**Review verdict: the user drove it and judged `Q23` fixed**, answering `PLAN.md`'s question — *"does
the elevated road now sit where the structure says it does?"*

⚠️ **Read narrowly, as `P2-3`'s and `Q8`'s verdicts were.** It says the carriageway reads as sitting
on its deck and that the widening stops where the bridge starts. It says nothing about `Q22` or
`Q21`, and **nothing became drivable** — `verify_road_graph` still reports 737 drivable edges of 797,
so `nearest_edge` refuses all 60 off-grade edges exactly as `P2-2` accepted. Opening the network is
`P4-1`.

| Graded against the shipped tiles by `tools/deck_error.py` | before | after |
|---|---|---|
| **\|error\| p90** | **4.131 m** | **0.095 m** *(accepts 0.50)* |
| deepest into the structure | 4.67 m | **0.48 m** *(accepts 0.50)* |
| within ±0.10 m | 1.5% | **92.7%** |
| step at the 36 mixed-level nodes, median | 6.00 m | **0.19 m** |
| level-0 carriageway widened past its support | 896 m | **382 m** |
| off-grade carriageway hanging in air | 20.1% | **10.2%** (`Q22`) |
| drivable edges / surface triangles | 737 / 34,920 | 737 / 35,039 |

⚠️ **0.48 m against a 0.50 m gate is a thin margin, named as a risk rather than quoted as a pass.**
One station of 3,286 — nothing else is past 0.24 m — 0.05 m from **node 275**, the `CANAL ROAD
FLYOVER` touchdown, where `_node_heights` takes the at-grade side at 4.43 m while the ramp's tile
geometry reads 4.71 m. That is the `Q13` residual already on record; narrowing did not create it, it
changed which drawn surface covers that station and so exposed it.

#### The classification, which was the task's real finding

| Kind | Count | Residual step once the deck is sampled |
|---|---|---|
| **Ramp junction** — structure already reaches grade at the node | **17** | median 0.33 m, max 0.93 m |
| **Ramp mid-point** — the source's `ELEVATION` flips partway up | **13** | median 3.09 m, range 2.14–4.02 m |
| **Tunnel portal** — a void, so no structure and never will be | **5** | unchanged, 8.00 m |
| **No usable structure** — `e425`'s 25 m stub at the region corner | **1** | unchanged |

⚠️ **There are zero plan-coincident crossings**, which was `PLAN.md`'s second hypothesis. The first
pass duly labelled 13 nodes that way; what exposed the error was the clearance — **2.14–4.02 m is too
low for a street to pass under.** Checked properly, 12 of the 13 are degree 2 with a level-0 edge
ending and a level-1 edge starting, 11 share a road name across the node, and the structure runs
continuously through. That is **one road, split where the publisher's attribute changes, partway up
the ramp** — which is why those 13 look like a 6 m cliff: *both sides are wrong, by about half a deck
height each, in opposite directions.* The deck-above-terrain margins are **bimodal with a gap between
+0.93 and +2.14 m**, so the split is a property of the data rather than of where a threshold was put.

**So sampling only off-grade edges would relocate the step, not close it** — a 2.1–4.0 m cliff would
remain **mid-ramp**, where it is more visible. **User's call: sample level-0 edges too**, since that
moves at-grade drivable geometry in a task whose scope note says nothing becomes drivable, and it was
not the ETL's decision to make. **Which level-0 rule was measured, not argued:** a height cap touches
173 of 737 edges with the ramp and flyover-deck populations separating at only 4.95 vs 5.33 m, while
a **walk** — edges meeting a mixed node, from that node until the structure meets the ground —
touches **16 edge ends** with no threshold to tune. The walk answers "is this the road's own ramp?"
from **topology**, which is the third place in this task where the naive answer was "pick by height"
and the measured answer was "pick by what it connects to".

**The portals are *clipped*, which is a better reason than "a tunnel is a void".** All five have an
edge cut at the region boundary, and **11 of the 30 level −1 edge ends sit on it**. For the
Cross-Harbour Tunnel that is decisive: **8 m of descent over a 42 m stub is a 19% grade**, and the
descent happens outside the region, so no height model can put a run there. It resolves itself only
if the region grows east — `Q6`'s territory.

#### Four sampler ideas were wrong before they were measured

1. **There is no parapet to subtract.** Transverse profiles across 8 flyovers show the deck centre is
   a flat plateau with the raised lips **+0.11 to +0.92 m, off-centre at ±3 to ±6 m** — a centreline
   never touches one. `Q13`'s "+1.22 m, about railing height" was the genuine gap between the invented
   height and the deck. One config knob deleted before it was written.
2. **Seeding from the existing height and taking the nearest hit is *worse* than taking the
   highest.** The multi-hit spread is 1.7–2.2 m — slab thickness — so the sampler hits the top *and
   the underside of the same slab*, and today's seed sits below the deck 66% of the time. What works
   is **slab clustering plus continuity**, anchored on stations with only one slab: segments over 12%
   go 6 → 2, worst grade **163.1% → 13.7%**.
3. **The terrain gate cannot be a minimum clearance.** Level-1 ramps genuinely touch down: of 645
   covered stations, 33 sit within a metre above terrain and 8 sit *below* it — a continuous 0–15 m
   spectrum with no gap to cut in. What separates is the other side, decisively: `e425` samples
   **8.3 m below** terrain against a next-worst of **0.54 m**. Hence `max_below_terrain_m: 1.0`.
4. **The fallback was the bug, and it hid behind a correct-looking result.** First run: median step
   6.00 → 0.04 m, but **14** nodes still stepped where step 1 predicted 6, nine at the full 6.00 m.
   `INFRASTRUCTURE` **stops being modelled where a ramp reaches grade**, so the structure query
   returns nothing at those nodes — and falling back to `terrain + 6.0` rebuilt the exact cliff the
   task exists to remove, at the most visible place in the region. Measured inside the hole, the
   structure sits −0.6 to +1.1 m of the terrain: the ramp has arrived, what is missing is a volume
   nobody modelled. An uncovered station now takes the deck **either side of it**, interpolated, and
   only an edge with no usable sample *anywhere* falls back. That closed 4 of the 9 outright and took
   the worst of the rest to 1.63 m.

⚠️ **Three of those were the plan's own answer, measured and replaced. The fourth appeared in no
plan** — it was found only because the node-step number came back worse than predicted and the gap
was chased instead of rounded off. A per-station fallback to the flat offset is the obvious
implementation and it is silently wrong in exactly the places that matter most.

**Densification is justified by the maximum, not the p90.** Sampling at today's vertices already
clears ±0.5 m at p90 (0.30 m); the case for 10 m resampling is the **4.84 m** max, all of it on `e118`
`FLEMING ROAD` where a 71.5 m vertex gap spans structure climbing 4.25 → 5.05 m — precisely the
defect the user drove into. ⚠️ `resample` **adds** stations without moving any existing vertex:
restating the line at evenly spaced stations is the obvious implementation and it silently cuts every
corner `simplify` just decided to keep.

#### Two claims from the `Q13` spike were wrong

⚠️ **The slab separation is far tighter than recorded.** The earlier note cited "1.7–2.2 m within a
deck against 9.2–16.4 m between stacked ones" — two *different* metrics. Measured over 645 stations:
within one deck **0.00–2.57 m**, between stacked structures **3.36–8.49 m**. So `slab_gap_m = 3.0`
sits in a **0.79 m** margin, not a 7 m one, and a second city must measure it.

⚠️ **"Single-slab stations are the majority on every edge" is false** — ≥73.1% on 44 of 45 elevated
edges, but `ISLAND EASTERN CORRIDOR` crosses the region on two stations and is stacked on both, so it
has no anchor at all.

Two latent defects fixed although Wan Chai triggers neither: the slab walk grew from the *first*
anchor only, so a run walled off behind an uncovered station fell back to the highest hit — the
flyover, precisely what the query exists to reject; every anchor now seeds both directions. And NaN
hits are dropped in `slab_tops`, since `np.sort` puts NaN last and no comparison against one is true,
so one NaN would have survived as the top of the highest slab.

#### Structural changes the fix forced

**`build_region` became two passes.** Whether a level-0 edge sits on a ramp depends on whether its
node is *also* reached by another level, which no edge can know until every edge has been clipped and
placed. `_Nodes` already keyed on plan position, but carried a height recorded **on first sight** —
whichever edge the source happened to list first won. Invisible while every edge at a level shared
one flat offset; not invisible once two ends are sampled independently. `_node_heights` states the
rule: **the level nearest grade, and the highest edge end on it.**

**`deck.clearance_m: 0.20`, a layer rather than a fudge.** The step-8 drive reported *"a little bumpy
where the white and grey mix together"* — a defect `P2-7` **introduced**, and no number in the task
could have caught it: before, the ribbon floated a median 1.31 m clear, so the two surfaces never
met; landing it *on* the deck made them coincident, and coincident surfaces interleave. The cause is
not the sampling — against the source sheets the ribbon is exact (median −0.000 m) — but `P2-1`
decimates `INFRASTRUCTURE` on a 0.5 m cell, and that collapse lifts the *shipped* deck a median
**+0.041 m**, max **0.339 m**. A real road is a wearing course laid *on* a structural deck, so a
clearance is the right shape; its size is set by the decimation, not by paving practice — 0.15 m
leaves 1.31% poking through at LOD0, **0.20 m leaves 0.37%**, 0.25 m leaves 0.06%. It applies only
where the deck decides the height, and `deck_error.py` **subtracts** it so the metric still measures
error rather than counting a deliberate layer as one. Cost: the median node step went 0.04 → 0.19 m.

**`at_grade_m: 0.30`, bounded by consequence rather than by a gap.** The 143 non-zero lift values run
continuously from 0.004 m up, so it is a tolerance, not a discriminator: bounded above by the 0.5 m
acceptance (the value *is* the residual step it leaves), below by the 0.1–0.2 m sampling wobble.
Across 0.1–0.3 the run length moves by at most one station on 13 of 16 ends.

⚠️ **Four config spellings loaded in a state they could not act on**, each now refused with a test,
because the symptom of any of them is *output identical to a city that never asked for deck
sampling* — a config error shaped to survive review: `deck:` with nothing under it; `.nan`, which
passes both `<= 0.0` and `< 0.0` then makes every downstream comparison false without raising;
`.inf`, which makes the lift never stop; and a fifth unknown key beside the four. Two combinations
are refused for parsing but never running — `roads.deck` without `ground: terrain`, and without
`buildings.structure_class`.

#### Width: the level rule, then the station rule

**`widen_by_elevation_level: {1: 1.0}`** — the first review finding: *"the elevated part of road
should not widen because the bridges are not widen and has guardrails"*. **The level rule wins
outright over the speed rule**, and that is the design decision: the speed table is a *preference*
about how much room a fast road wants, a level rule is a *statement about what the carriageway is
sitting on*. The Wan Chai Interchange matches both — signed at 70 and up on structure — so a
speed-first reading would still draw it 1.3× and hang it over the parapet. Both arguments the
widening rests on are at-grade arguments: a gap between opposed carriageways shows the void where
terrain would be (on a flyover it shows the **deck**, which the tiles ship), and real street widths
are unforgiving at arcade speeds (a viaduct is parapet-to-parapet in the real city).

**Then `Q23`: width is a property of the *station*, not of the edge** — the re-drive's finding, *"it
should stop widen where it meets any bridge structure"*. `elevation_level` is an attribute of a whole
edge, and a road does not become a bridge at an edge boundary: `P2-7` itself lifted **16 level-0 edge
ends** onto their ramps, so those stations sat on a deck while their edge was still labelled level 0
and kept the full 1.6× — **1,070 m of level-0 centreline across 28 edges, every metre widened.**

**The graph had to gain a field, because nothing downstream could recover it.** `surface.py` reads
`roadgraph.json` and nothing else, and the published `y` cannot identify structure: with
`ground: terrain` a level-0 road climbing the Mid-Levels escarpment reaches 49 m while at grade,
against a level-0 median of 4.22 m. Only `roads.py` knows which stations it lifted — and
`_lifted_heights` was already computing that mask as `raised > 0` and discarding it.

- **The level table still wins over the station, and that ordering is load-bearing.** Letting the
  station win would re-widen an off-grade edge wherever structure was never found —
  `ISLAND EASTERN CORRIDOR`'s stub reports every station as off structure *precisely because* nothing
  is under it. Checking the level first leaves levels 1 and −1 exactly as measured.
- **A taper, not a step, on the user's call.** A hard switch jogs the carriageway edge and its kerb
  sideways by ~1.9 m between two stations, reading as a modelling error rather than as a bridge.
  `structure_taper_m: 15.0` spends the blend on the *approach*. Zero stays reachable.
- **The width travels as a fourth column of `_Edge.points`, not a parallel array.** `dedupe` drops
  stations and `trim` interpolates new ones, so a side array must be threaded through both by hand;
  as a column it simply travels, because `_at` interpolates every column it is handed.
- **`_assign_trims` had to change with it**, and that was the sleeper risk: the junction radius was
  `max(half_width_m)` over the arms at a node and is now the widest *end*. Those stopped being the
  same thing here, and the end is right — a cap has to reach each arm's mouth, and a mouth is as wide
  as that arm is *there*.

⚠️ **The residual does not go to zero, and it should not — this is the finding.** `roads.py` decides
"on structure" *topologically* (an end is on a ramp because it connects to the edge that is);
`overhang.py` decides it *geometrically* (an upward face within 1 m). The geometric set is larger and
includes things that are not bridges. The populations separate cleanly: stations this narrowed sit a
median **1.55 m** above the ground (max 4.03 — ramps), the ones left wide a median **0.15 m** (max
0.92 — abutments and retaining walls). **A street on an abutment is a street.** So 1,070 m was always
a geometric upper bound and 546 m — what the graph flags — is the honest count.

#### Schema, and the bump rule it established

`roadgraph.json` → **2** for the sampled `y`, then → **3** for the per-vertex `on_structure`;
`roadsurface.json` → 3 and `city.json` → 4 because `carriageway[].half_width_m` went from a number to
an array. `roads.glb` did **not** bump: its geometry moved and no attribute changed meaning —
`TEXCOORD_0.x` is still a lane coordinate, which is exactly what lets it survive a width that varies
along an edge.

**The rule this established, now in `ARCHITECTURE.md`: bump where a consumer would be *wrong* to keep
its old interpretation, not wherever bytes change.** Schema 2 is the pure case — nothing was added,
removed or renamed; `polyline.y` simply began meaning something different, which a consumer cannot
tell by inspection and a diff cannot show. `Q23`'s is the rarer shape-change case, louder but still
earning a bump for the quiet half: a reader taking `[0]` is right on 769 of 797 edges and 0.96 m out
on the other 28.

Verified the gate is live: hand-editing the shipped asset back to `schema_version: 1` makes
`verify_road_graph` fail by name. It also gained a per-station width check, because `_check_lanes`
samples edge midpoints and could never reach these 16 edges — and it **refuses to pass vacuously**,
reporting a build with no mixed edge at all, because "the case never came up" and "the case works"
are the same green.

#### The two grading tools were wrong seven times between them

⚠️ **This is the finding most worth keeping.** An acceptance tool is the last thing anyone checks, and
every one of these produced a *plausible table*.

`tools/deck_error.py` grades the carriageway against the structure in the **shipped tile GLBs**,
sharing nothing with the code it grades: geometry from the decimated tiles rather than the source
sheets, deck faces by **winding** rather than slab clustering, structure by **vertex colour** rather
than sheet sub-directory, and its own point-in-triangle query. Four ways wrong:

| Wrong | Read | Why |
|---|---|---|
| Matched the structure colour exactly | 428 of 434,149 triangles | `colour_for` **jitters every class**. A class is a *ray* through its base colour, not a value |
| Kept both face windings | 1.07 m p90 | A deck's underside is as horizontal as its top, so a carriageway sunk into a deck scored against the face 1.5 m below |
| Sampled the road mesh's own vertices | 1.31 m p90, 8.4 m on `CANAL ROAD FLYOVER` | `roads.glb` carries vertices **only at the carriageway edges**, which overhang the deck *by design*. The tool was measuring overhang |
| Left unmeasurable stations out of the denominator | 0.09 m p90, "acceptance met", **exit 0** | Raise 35% of the elevated carriageway 30 m in the graph and leave the mesh alone: the broken third stopped being measured and every ratio improved |

The third looked exactly like a real defect — one named flyover, a consistent 8 m, the deck
separation of a double-decker. Chasing it found the geometry right and the *question* wrong.
**Overhang is `Q19`'s question; height is `Q20`'s, and conflating them manufactures a failure.** The
fourth was the dangerous one: a total break was already loud (no samples → exit), a *partial* one was
silent. Coverage is now measured against what the centrelines asked for, fails below 90%, and an
elevated edge matching no drawn road fails outright. The real bundle reads **96.9% measured**.

`tools/overhang.py` was wrong three ways, all the same shape — **a probe that measures itself.** (1)
Asking "on structure?" of *any* cell across the ribbon made the measurement depend on the drawn
width, so narrowing would shrink the very number that says whether narrowing worked; it samples the
centreline now. (2) `stations` yields a polyline's last vertex as well as its interior steps, so run
per segment it double-counted **735 of 4,127** level-1 stations, overstating drawn area by 22%. (3) A
cell with no road drawn at it counted as hanging in air in one tally and "not measured" in another.
All three were found by review rather than by the numbers, and it now reproduces the recorded 10.2%
off-grade overhang at **10.0%**.

**Both are committed and neither is wired into `tools/check.sh`** — they need a built region under
`etl/out`, which `check.sh` does not require and should not start requiring. The reason to commit
them: a measurement that cannot be re-run is an anecdote.

⚠️ **Two scoping notes on the claim.** It is bounded to **LOD0**, the tier that collides — against
LOD1 the same bundle reads a deepest intrusion of 0.54 m and fails, because that tier decimates
`INFRASTRUCTURE` on a 1.0 m cell; a drawing artefact seen from over 250 m away, and the tool says so
to anyone who passes `--lod 1`. And the **"no ribbon more than 0.1 m below the deck" half of the
criterion was superseded by measurement**: `P2-1`'s decimation alone widens \|error\| p90 from
0.030 m (source sheets) to 0.095 m (shipped tiles), so a 0.1 m gate sits under the noise floor of the
surface being measured. The gate became the **deepest single intrusion** at the same 0.5 m.

⚠️ **The ETL's own error column is not an acceptance measurement** and must not be quoted as one. It
resamples the written polyline and asks the *same* `HeightField` that produced it, so it can only
show the write-out is faithful to the sampler. Its value is that its `before` column reproduces the
recorded 4.19 m baseline at 4.14 m — it validates the harness, not the fix.

#### What is left

`Q22` (10.2% of off-grade ribbon overhangs its structure — no width rule reaches the rest), `Q21`
(whether level −1 should be drawn at all), and the five tunnel portals plus `e425`'s stub, which no
height source will ever repair. All three belong to Phase 4.

### 2026-08-01 — One owner for the debug chrome, one key, and **off by default**

`DebugHud` is a new autoload owning every dev readout. Three scripts were each deciding
independently what to draw — the frame counter, the road-graph overlay's text block at a hardcoded
`(16, 96)`, and its chevrons — and a fourth would have been a fourth offset picked by eye. `F3`
cycles `off → minimal → full`; `--debug-view=` sets where a run starts.

**The default is off, in every build**, which is a change. First, every screenshot anyone judged Wan
Chai from had a five-line text block over it. Second, measured on the standard driver run at 2.0 s:
19 draw calls off, 27 at minimal, **38 at full** — debug text was costing half as many draw calls as
the entire city, because text with an outline does not batch the way a flat-shaded mesh does.

`drive.sh` defaults to `minimal` instead, which is the one place the reasoning inverts: a scripted
run is somebody debugging, and a screenshot that cannot say where it was taken cannot be acted on.
The position block reports engine metres **and** the EPSG:2326 grid reference via
`CityManifest.to_grid`, so a suspicious frame is checkable against the ETL's own source data.

Three smaller calls, each with a trap behind it. **The toggle is a raw key, not an action** —
`[input]` is the *shipped* map, so `drive.sh --hold=` cannot press it and the flag is the only route
a scripted run has. **`--debug-view` had to be taught to `driver.gd`**, which fails on unknown
arguments, and the autoload reads *both* arg lists because Godot splits at `--`. **Headless parks
the HUD whatever the flag says.** And `VehicleController` now joins a `vehicle` group: two overlays
were each walking the whole tree to find the car, and the HUD repeated its search for as long as it
came back empty — in a preview scene, for ever.

Font sizes are constants rather than a `.tres`, which is a deliberate reading of hard rule 4:
tuning values are *gameplay* values, balanced by someone who should not need a code change. Nothing
about dev chrome is balanced.

### 2026-08-01 — Genre direction: three references, three different questions

| Reference | Contributes | Landed in |
|---|---|---|
| **Crazy Taxi** | The loop — fare combo, session timer, arrow, three-minute sessions | Already the design |
| **Midtown Madness 2** | The world — real shortcuts over invented ramps, tone, drivable roster | `GAME_DESIGN.md` divergence table; the risk register |
| **Forza Horizon** | The reward layer — the losable style chain, scoreable traffic | `GAME_DESIGN.md` scoring; `PLAN.md` `B3`/`B4` |
| **Sleeping Dogs** | The nearest commercial precedent for a recognisable HK. The common reading is that **signage density carried it, not street accuracy** — untested here | `P3-9`, and the neon note |
| **Burnout 3** | Traffic as reward rather than obstacle — near miss, oncoming lane, risk-fed boost | `P3-2a` |
| **Art of Rally** | Flat-shaded untextured terrain as a **finished** look, not a placeholder | `Q18`, `P3-10` |

**Neither open-world structure survives a 1.5 km² region, and the reason is size rather than taste.**
Midtown Madness consumes map area as content; Forza Horizon uses the open world as its menu, which
needs traversal to be a pleasure rather than a formality. A checkpoint race across this region is
60–90 seconds. The fare loop does the opposite — it re-randomises the route through the same
1.5 km² every session, which makes a small map an **asset**.

**The finding is a plan-ordering bug, and it is a shape this project has seen before.** `B3`'s
review asks *"harder in a good way, or just annoying?"*, and `P3-2`'s near-miss scoring sat in `B4`.
Dense traffic converts from obstacle to opportunity only when threading it **pays**, so `B3` would
have been reviewed in the single state where traffic has no upside, and a "just annoying" verdict
would have been an artifact of the ordering. Near-miss detection splits out as **`P3-2a`** and moves
into `B3`. Same failure shape as `P2-5`'s missing building collision: *a unit whose acceptance
depends on a capability scheduled after it.*

**Refused, and named here so they are not revisited:** wheelspins and randomised rewards (already an
anti-goal); live-service and always-online structure (hard rule 2); licensed-car collection as a
progression spine (the art direction is 800–2,000-triangle toys); and Crazy Taxi's absurd-geometry
philosophy — ramps scattered wherever the driving goes quiet — which `P3-9` would charge for in full.

### 2026-08-01 — `P2-5` closed, and the exception it found is `Q20`: **the flyovers are drawn twice**

The camera verdict: *"camera work mostly with one exception where a road suddenly appears mid air
and block everything"*. **That is not the camera, and `P2-5` passes.** Measured at the car's own
position, road geometry within 60 m is either y 2–4 (the street) or y 8–10 (the deck above), and
**nothing sits in the 0.3–3.0 m band the car occupies**.

`Q13` decided the elevated network is out of the slice, and that decision was about **driving**.
Nobody made the matching decision about **drawing**, so `surface.py` still ribbons every off-grade
edge — 15 tunnel and 45 elevated edges, **23.3% of drawn carriageway** — with no ramps, so a deck
starts and stops in mid-air. **And the deck is already there:** sampling along every level-1
centreline, `INFRASTRUCTURE` tile geometry sits a median 0.51 m away vertically. The 3D
Visualisation Map models the flyover as a solid and `class_lod_cell_sizes_m` holds it at a 0.5 m
cell precisely so it survives decimation — and then `surface.py` draws a second carriageway on top.

**The height is invented, not measured.** Against the structure the ribbon is supposed to lie on:
median error **−1.51 m**, p10–p90 **−4.06 … +2.45 m**, **below** the structure in **72%** of samples,
off by over 1 m in 78%. So the ribbon is mostly buried inside the flyover it should be lying on.

⚠️ **What changed is the reason it was safe to defer.** `Q13` reads "topologically connected and
**geometrically unreachable**", and that was true while the only solid thing in the world was
`roads.glb`. Since collision shipped, the `INFRASTRUCTURE` structure is a collider — so the physical
ramps are drivable, and a player arrives on a deck whose carriageway is a metre and a half away.
**Nobody decided to open the elevated network; a change made for the camera opened it.**

It also corrects `Q19`, which this session got wrong. Re-split by deck height: `INFRASTRUCTURE` off
grade 1.73% (unreachable), `BUILDING` at grade 1.72%, `INFRASTRUCTURE` at grade 1.60%, `BUILDING`
off grade 0.14%. `Q19` was first written as "`INFRASTRUCTURE` 3.32%, the larger half" — **over half
of that sits on ribbon nobody can drive on.** A number is only as good as the question it answers,
and "blocked carriageway" without "carriageway the player can reach" was the wrong question.

### 2026-08-01 — `P2-5` drive: collision passes, and it **promoted a cosmetic overlap into a blocker**

*"collision seems ok, note that some building actually went onto part of road"*. Read narrowly, as
`P2-3`'s was: it answers the collision question, not `PLAN.md`'s camera question. No camera
complaint was raised, which is not the same as a pass.

Geometry rasterised to a 1 m plan grid, a cell counting only when solid geometry sits **0.3–2.0 m
above the deck** — bumper to roofline, so a podium 6 m up overhanging the street is Hong Kong
working as intended: **25,466 of 492,320 cells, 5.17%.** A first bad measurement put this at 13.71%
by marking each triangle's bounding box; sampling the actual surfaces cut it to a third.

⚠️ **These are two defects wearing one symptom, and they do not share a fix.** The `INFRASTRUCTURE`
half belongs to `Q13`/`Q20`. The **`BUILDING` half this project chose**: `widen_default` is 1.6× and
`GAME_DESIGN.md` fixes the range at 1.3–1.8×, so widening eats the pavement first and then the
ground-floor frontage. The config already knew — `widen_by_min_speed_limit_kph` holds expressways to
1.3 with the comment *"widening them the same amount pushes the deck through the buildings beside
it"*: the same effect, found once, fixed locally, and never checked across the network.

**Nothing here is new geometry; only the consequence is new.** Collision is what turned 25,466 m² of
overlap into invisible wall on roads the graph says are legal — and `P3-3`'s traffic will route into
it, because `RoadGraph` has no idea any of it is there. Both halves want the same missing tool: **a
check that fails the build when the carriageway is occupied.**

### 2026-08-01 — Buildings get collision from a **mesh name**, and the task that owned it had already closed

`P2-5`'s acceptance criterion is *"no clipping through buildings"* — unreachable, because a
`SpringArm3D` collides with nothing until the buildings do. `PLAN.md` gave that decision to `P2-1`,
which decided correctly that **a building collider is an ETL product, not a runtime one**, then
closed. The decision was right and it left nobody holding the work, so the region shipped as a
hologram. Neither the streamer review nor the `P2-3` drive would have caught it, because neither
asked.

**The answer was already in the repo.** `P1-4` gives the carriageway its collider by naming the mesh
`road_surface-col`; Godot's glTF importer reads the suffix and builds a `StaticBody3D` with a
`ConcavePolygonShape3D` at **import** time. `buildings.py` now names its finest tier
`<tile_id>-col`, and that is the entire game-side change. No shape is built at runtime, and the
collider cannot drift from the mesh because it *is* the mesh.

**Only the finest tier, and that is policy rather than economy.** A tier is chosen by distance, so
the coarse one is resident only beyond the 250 m band where nothing can touch a building.
`verify_tiles.gd` asserts both directions — present on tier 0, absent on every other — because a
suffix that spread would be invisible in every screenshot and show up only as bundle bytes.

**Cost: 21.10 → 26.27 MB PCK, +5.17 MB**, measured from two exports with one variable changed. Worth
stating what it is *not*: tier 0's 434,149 triangles as raw un-indexed faces would be 14.91 MB. The
pack compresses them to a third. `Q16`'s rule — measure the PCK, never sum the source — earned its
keep in both directions in one session.

⚠️ **`P2-6` must re-measure hitching.** Instantiating a tile now also registers a trimesh with Jolt
on the main thread, and `max_instantiations_per_frame` is 2. `P2-1`'s "no hitching" was accepted
before that cost existed. It is invisible at 120 fps on an M4 Pro and is exactly what the device
floor finds.

**Two bugs found on the way, and the second was the dangerous one.** `RoadGraph.shared()` returned
`null` from a guard written to stop it: the fallback used an inline `{}`, which is **untyped**, so
the null branch — the only branch the guard exists for — raised and aborted. Then `verify_spawn.gd`
called `.is_empty()` on that null, the script error left `_init` before any `quit()`, and the
SceneTree ran forever; `tools/check.sh` hung with it, twice for over ten minutes. **A check that
hangs is worse than a check that fails**, because a timeout names nothing. Fixing the first turned
the hang into a **silently wrong pass** — the spawn assertion reported `ok` at 1.60 m off the
centreline instead of 2.56 m, computed from absent data. `verify_spawn.gd` now refuses on
`has_carriageway_widths()`, which is stronger than a manifest null-check: a `city.json` that loads
cleanly but publishes an **empty** table passes the null-check and fails this one.

### 2026-08-01 — `P2-3`: the start line is **queried, not written down**

`RoadSpawn.at_fare_node` resolves fare node `f_004` through `RoadGraph`, and `basis_facing` builds
the rotation from a direction with `Basis.looking_at`. Almost all of `P2-3` is a deletion:
`city_drive.tscn` carried a twelve-float `Transform3D` literal and `ARCHITECTURE.md` carried forty
lines explaining how not to transpose it.

**The query reproduces the literal to 4 dp**, and the overlay reads `0.00 m` from the nearside lane
centre with heading agreement `+1.00`. The hand-derivation was right; it just should not have had to
be done.

**The heading is deliberately not passed to the query.** A zero heading makes `nearest_edge` take
the edge's own vertex order, and `P1-3` reversed the polyline of every backward edge precisely so
that order *is* the legal direction. Passing the car's rotation in would let the car decide which way
a two-way street runs, which is the wrong way round: the street decides.

⚠️ **The assertion alone is not enough, because a transpose is not a 180° flip.** It mirrors the
heading about world −Z: 171.9° wrong on Expo Drive, 180° on a due east-west street, and **0° — a
silent no-op — on a north-south one.** So `verify_spawn.gd` builds the transposed basis and requires
it to *fail*, with a 10° floor on the discriminating angle. Proven non-vacuous by transposing
`basis_facing`'s return and by pointing it at a fare id that does not exist.

**Two findings that changed the shape.** `ray_length_m` lives on `HandlingProfile`, not on
`VehicleController`: the controller reads the `InputRouter` autoload, **autoloads are not registered
under `--script`**, so any headless tool touching it fails to compile — and `verify_spawn.gd` then
*printed `ok` and exited 0* while erroring, caught only because `tools/check.sh` greps stderr as well
as reading the exit code. And the authored transform stays in the scene as a fallback that says so,
because `assets/generated/` is gitignored and a fresh clone has neither graph nor fare nodes.

**Review caught two more in code that had passed every check.** The nearside-lane assertion measured
against the wrong street — it took the centreline from a fresh unconstrained `nearest_edge`, which
can land on a *neighbouring* edge, and compared it against `forward` from the spawn's edge. And a
keep-alive comment stated the opposite of the truth. Three smaller: an unused `clearance_m` that made
the drop-height check valid only because nobody passed it; a malformed `pos` degrading to
`Vector3.ZERO`, which in a region-local frame is a real place and would resolve to a plausible wrong
street; and `spawn_fare_id` duplicated into the scene file, so changing the default would silently
do nothing to the scene that boots.

**The `P2-3` verdict was *"car seems ok"*** — a pass on the question asked and nothing more. It says
the placement change did not damage handling `P0-5` had already accepted. It says nothing about feel
in the hand, which is review point 2 and still needs `P0-3b`.

### 2026-08-01 — Ground and building colour: **the vertex stream carries both**

An evaluation, not an implementation. Two questions the user put together — colour the ground from
the huge source texture, and colour buildings without a size or perf cost — turn out to be one
question: **what channel carries colour.** The project already answered it. Colour rides `COLOR_0` on
an untextured mesh that merges to one primitive per tile, and that single choice is what produces 53
draw calls and a 21.1 MB PCK.

**The terrain budget that terrain failed no longer exists.** `P1-2t` measured 267 MB against a
bundle then holding 51.6 MB of tiles. **224 of the 267 MB was the JPEG. Geometry was never the
problem**, and the resampling that would have fixed the texture was simply never written.

**Rejected — ship the texture, resampled.** 2 px/m is ~5.9 MB as ASTC, affordable in isolation. It
fails on two other counts: a textured surface cannot merge with the vertex-coloured building
primitive, so it costs **+1 draw call per resident tile**; and an orthophoto has the *real* roads
baked in at their real width while the generated ribbon sits coplanar and **1.6× wider**, so
photographic asphalt and lane markings would show from under a wider synthetic road, along with
parked cars and baked shadows.

**Chosen — the texture is read at build time and thrown away.** Sample the JPEG per source triangle,
classify to a small land-cover palette, write the result into `COLOR_0`, ship no texture. ~88k
triangles region-wide (≈1,355 per tile), 1.5–2.5 MB of geometry, **zero** texture memory, **no extra
draw call**. And the UV-smearing objection to decimating terrain evaporates — there are no UVs left
to smear. The implementation idiom already exists: `mesh.collapse` puts *facing* in the cluster key,
so putting the **land-cover class** in the same key lands cluster boundaries on the park, pavement
and water edges instead of blending across them.

**Ordered first — geometry only, one flat colour.** No image decode, no new dependency, and it
produces the screenshot that says whether flat ground reads dead. That ordering is `P3-10` and `Q18`.

**Buildings do not have a colour problem; they have a surface-detail problem**, and the fix was
already designed as `P3-7`. Two routes rejected: a low-res texture or atlas (any texture needs UVs,
and **UVs do not survive vertex clustering** — paying to break the LOD system), and per-building
colour sampled from the individualised set (5.86 GB for one region, 93–96% of it texture, and
oblique aerial capture is dominated by shadow and haze so the median converges on grey-beige,
flattening exactly the old-below/new-above contrast the height bands exist to express). What ships
instead is the channels already in the bundle carrying nothing: `TEXCOORD_0.xy` = height above the
building's own base and a per-building seed, ~2 bytes/vertex quantised.

⚠️ **Use `TEXCOORD_0`, not `COLOR_0.a`.** `generated_scene_import.gd` sets
`vertex_color_use_as_albedo` project-wide. An opaque material ignores albedo alpha only until
somebody enables transparency on a tile, after which the city renders see-through with no error.

### 2026-08-01 — **Two** shadow cascades, not four: 35% off the frame's primitives

`golden_hour.tscn` never set `directional_shadow_mode`, so it took Godot's default of **four** PSSM
cascades at 600 m — past both the chase camera's 400 m far plane and the streamer's 400 m unload.

| Config | t=1 | t=3 | t=6 | vs default |
|---|---|---|---|---|
| 4 cascades @ 600 m (was) | 244,888 | 215,071 | 263,077 | — |
| **2 cascades @ 400 m (shipped)** | **159,739** | **132,845** | **155,032** | **−35%** |
| 1 cascade @ any distance | 110,644 | 93,206 | 112,142 | −55% |

⚠️ **One cascade is what the spec asked for, was shipped first, and had to be withdrawn.** It has a
distinct artefact at every distance: at 150 m shadows fade out mid-street while the camera draws to
400 m; at 250 m the HKCEC shadow comes out **banded**; at 400 m it **disappears**, the caster falling
outside the ortho volume's near plane. The first two are one artefact, not two —
`directional_shadow_fade_start` is a *fraction* of `max_distance`, so shortening the distance to
sharpen the near field silently drags the fade band in with it. I checked the two artefacts I
expected on a **near-field crop** and never looked down a long street; the user did.

400 m rather than 600 because it is exactly the camera's far plane and the streamer's unload, so
shadow reach and draw distance end together. Distance is free either way — 150, 250, 400 and 600
measure **bit-identically** for a given cascade count.

⚠️ **"35% off the frame" is a primitive count, not a frame time.** Every configuration pinned to
8.3 ms on this machine, so the GPU saving is **unmeasured**, and shadow-map fill is unchanged since
the atlas is one texture at any cascade count. Justified as headroom for the unbuilt mobile tier and
as spec conformance, not as a measured speed-up. Cascade count also costs draw calls in the opposite
direction: 4 → 32, 2 → 35, 1 → 39, off → 26.

**No `LightingProfile` resource, deliberately.** A `.tscn` *is* data — `city_drive.tscn` already
carries `far = 400.0` the same way. A profile plus an apply script would move values out of a scene
the editor renders correctly and into a script that writes them in `_ready()`: two sources of truth
whose disagreement would be invisible in the editor.

⚠️ **"Vehicle blob shadow only" deserves re-examination before anyone builds the mobile tier.** Shots
with shadows *off* looked markedly worse than the line implies — flat and blown out, the canyon
losing its depth entirely. A real mobile tier needs the ambient and tonemap re-tuned around a blob
shadow, not the shadow switched off. `P2-6` inherits that.

**Unrelated finding, recorded while looking at the shots.** The dark wedges at junctions — the thing
that prompted the shadow question — are **not shadows and not the missing terrain**. They are gaps in
the road mesh: `surface.py` trims each edge end back from a node and fills the middle with a cap
fanned from its centroid, so where roads meet at an angle the cap's straight chord cuts inside the
corner. They read as shadows because the sky's ground gradient shows through. A `P1-4` coverage
question, worth taking before `P3-9`.

> ✅ **Closed 2026-08-04**, after the user hit the same thing from the driver's seat and reported the
> road shrinking at junctions. The diagnosis above was right and the "worth taking" was too soft.
> See the 2026-08-04 entry.

### 2026-08-01 — `P2-1` review passed, and it closes `Q16`: **LOD0 does not ship**

The user drove a build with no exact-weld tier — not a distance-band trick, an actual two-tier build
— and the verdict was *"they look ok"* on the buildings and *"not much pop"* on the transitions.

| | 3 tiers | 2 tiers | |
|---|---|---|---|
| Files shipped | 199 | 134 | −65 |
| Source bytes | 105.5 MB | 30.8 MB | −74.7 MB |
| **PCK** | **51.6 MB** | **21.1 MB** | **−30.5 MB (59%)** |
| Worst-case visible triangles | 249,210 | **150,374** | **−40%** |
| Worst-case resident triangles | 424,648 | 236,882 | −44% |
| Draw calls | 53 | 53 | — |

**Both budgets improve, and the second is the surprise.** Dropping a tier was supposed to be a bundle
decision; it also took 40% off the frame cost, because the tier removed was the one drawn nearest the
camera where the least is culled. For the business case: roughly **4–5 regions in a 200 MB download
instead of 2**.

**`Q16`'s own lesson applied to itself, again.** The source saving is 74.7 MB and the PCK saving is
30.5 MB. `PROGRESS.md` had estimated "the bundle drops to 28 MB"; measured, **21.1 MB** — better than
the guess this time, and still 33% out.

**The bands were retuned with it.** Two tiers want one edge, not two: left at `[100, 250]` the
coarsest band clamps and everything past 100 m draws at 4.0 m cells. `streaming.tres` now carries a
single 250 m edge with a 400 m unload. The user's verdict was given on the *coarser* version, which
makes it a stronger yes than it needed to be.

⚠️ **Dropping the finest tier broke the `aabb` contract, and `verify_city.gd` caught it — 34 tiles.**
`tiles[].aabb` was measured from the **uncollapsed source**, right only while tier 0 was an exact
weld. Once the finest shipped tier was decimated the published box described geometry no build
contained: one tile declared a height **19 m** past its own LOD0, a mast too thin to survive a 1.5 m
cell. **And publishing tier 0's box is also wrong**, measured on `t_01_02`: its 4.0 m tier stands
**12.03 m taller** than its 1.5 m tier, because `collapse` buckets on `floor(position / cell_m)` and
averages, so a *coarser* grid can leave an extreme vertex alone in its cell where a finer grid
averaged it inward. **Decimation does not only shrink a box.** The ETL now publishes the union of
the shipped tiers, and `verify_city.gd` asserts every tier is contained and the union tight to 1 cm.

**What is not closed.** LOD0 can come back for one platform: 200 MB is the *iOS cellular* threshold
and desktop has no hard limit, so a desktop-only exact-weld tier is an export-filter question rather
than a settled no. One entry in `lod_cell_sizes_m` and a 3 s rebuild.

### 2026-08-01 — LOD is **per mesh class**: a deck is not a building

`P2-1`'s LOD1 shots showed the flyovers and footbridges coming apart while the buildings beside them
were near-indistinguishable. The cause is geometric and exact: **`collapse` clusters vertices by
cell, so any structure thinner than the cell has its top surface merged into its bottom one.**

| Solid | raw | 0.5 m | 1.0 m | 1.5 m | 4.0 m |
|---|---|---|---|---|---|
| Deck, 30 m across and **0.8 m thick** | 12 | 12 | **2** | **2** | **2** |
| Tower, 20 × 20 × 60 m | 12 | 12 | 12 | 12 | 12 |

The tier was never too coarse for buildings — it was always too coarse for infrastructure, and
merging the two into one mesh before collapsing meant one cell size had to serve both.
`class_lod_cell_sizes_m` holds Hong Kong's `INFRASTRUCTURE` at `[0.0, 0.5, 1.0]` against the
building default `[0.0, 1.5, 4.0]`. **Ordering is the whole fix:** bucket by class, collapse each at
its own cell, *then* merge — which keeps the tile one mesh and one draw call. Cost: worst-case
visible triangles **240,598 → 249,210**, +3.6% against a 300k budget. Chosen over an outright
exemption (+20% at LOD1, +57% at LOD2) because a deck only has to beat its own thickness.

⚠️ **One correction.** `P2-1` recorded that tall towers survive LOD1 well because they are big boxes.
Measured, the opposite: towers ≥100 m keep **36%** of their triangles at LOD1 against **44%** for
everything else. They are hit *harder*. They read as fine in the canyon shot because they were
distant, where a tower is mostly silhouette.

**The landmark half of the question was declined for a better reason than "not implemented".** There
is no landmark key in the source — the sheets carry `BUILDING` and `INFRASTRUCTURE` and nothing else.
More usefully, `ART_DESIGN.md` already specifies the ~5 hero buildings as hand-authored models placed
via `landmarks.json`; they never pass through `buildings.py`, so their massing is *replaced* rather
than decimated and the question is moot for exactly the buildings that motivated it.

### 2026-08-01 — `P2-1`: the city streams, and **visible triangles come inside budget for the first time**

Measured in-engine at five places, the same five before and after — because quoting one spot's
"before" against another's "after" is how every bundle figure in this project drifted.

| Place | Draw calls | Visible triangles (main pass) |
|---|---|---|
| (172, 27) — the HKCEC spawn | 63 → **32** | 163,384 → **60,758** |
| (1114, 506) — worst residency | 52 → **46** | **398,574 → 240,598** |
| (700, 400) | 70 → **53** | 375,574 → **167,914** |
| (400, 300) | 70 → **48** | 211,236 → **106,180** |
| (1400, 700) | 29 → 29 | 134,971 → **119,570** |

Draw calls peak at 53 against 150. Worst-case *visible* triangles went **398,574 → 240,598** against
300k: the baseline was over, the streamed city is under. The method is corroborated — the baseline at
the spawn measured 1,164,133 primitives against the 1.16 M recorded independently for the same setup.

**The design is split in two, and that is what makes the third criterion structural.** `TileStreaming`
lives in `scripts/core/`, is pure, and takes an `AABB` and returns an int — there is no code path from
it to a file, so a distant tile cannot be rejected *after* being loaded rather than before.

**Resident triangles are reported, never gated, and the measurement says that was right.** The
sweep's worst case is 405,210 resident against a 300k budget. But the budget is 300k *visible*, and
the streamer culls to a **disc** while the renderer frustum-culls to a **cone**: at that same point,
402k resident draws as 240k visible. Gating on it would have tightened the bands by ~40% to satisfy
an arithmetic mismatch.

**A review pass found four defects, and two were in the check rather than the thing checked.** The
draw-call gate read the resident-tile count *at the worst-triangle sample* rather than its own
maximum — 31 tiles there against **37 at (1114, 381)**, so the only failing assertion was gating on
a number that was not the worst case. The residency sweep culled on `unload_distance_m`, but a
resident tile keeps its band for another `hysteresis_m`, so the real disc is 415 m. A failed tile
load leaked and then repeated forever, because `load_threaded_get` is the only call that releases a
`ResourceLoader` task. And a superseded tier was instantiated rather than discarded, spending one of
the two per-frame slots exactly when they are scarcest.

⚠️ **Proving the check could fail was itself a false green.** Breaking `plan_distance_to` to measure
to the AABB *centre* reported exit 0 and no failures — the edit orphaned a local, `unused_variable`
is promoted to error, the script never parsed, and `quit(1)` never ran. **Never read raw `godot`
output and call it a pass**; `tools/check.sh` is the only thing that can fail.

### 2026-08-01 — `P2-2`'s last criterion, measured: **p99 45 µs against a 1 ms budget**

Closed inside `verify_road_graph.gd`, so it is a check that runs on every `tools/check.sh` rather
than a number someone wrote down once.

| Population | n | p50 | p99 | max |
|---|---|---|---|---|
| Whole region — 10 m lattice | 15,865 | 14 µs | **45 µs** | 191–229 µs |
| On the road — every drivable edge midpoint | 737 | 4–5 µs | 9–10 µs | 44–101 µs |

**Probing the whole region rather than the road is the whole design.** A query on a centreline is won
in the first ring; a query in the middle of a block expands rings until the 60 m bound stops it. So
the **misses are the expensive population** — 1,758 of 15,865, 11%, which is more than the top 1% and
therefore exactly what p99 lands in. A road-only probe would have reported 9 µs and understated the
worst case by five times.

**The gate is p99, not max, and that was measured rather than judged.** Across runs the maximum
ranged 44–229 µs while p99 moved by a single microsecond. The maximum is a fact about what else the
machine was doing; p99 over thousands of probes is a fact about the code.

⚠️ **And the test found the limit of this check.** Disabling `nearest_edge`'s ring early-exit moved
on-road p50 from 5 µs to 56 µs and p99 from 10 µs to 117 µs — an 11× regression that **stayed under
budget**. This is an acceptance criterion, not a regression alarm, which is why the distribution is
printed on success as well as on failure. One incidental finding for `P2-6`: with the early-exit
disabled, on-road queries became *slower* than region-wide ones, because a cell on a road holds many
segments while a cell inside a block holds none.

### 2026-07-31 — `P2-2`: the drawn carriageway width is a **contract gap**, and the overlay is what found it

`RoadGraph` lands the queries the previews were faking: one parse per scene held through a
`WeakRef`, nearest-edge over a 25 m plan grid, lane centres, and typed accessors.

⚠️ **The "one parse" claim was false when first written.** Both previews took `RoadGraph.shared()`
into a **local**. `RoadGraph` is `RefCounted` and the cache is weak, so the only strong reference
died when `_ready` returned and the next sibling re-parsed. A weak cache only works if consumers hold
a member.

**`Q13` is enforced rather than described.** Only level-0 segments enter the index, while
`polyline_of` still serves all 797 because `P3-3`'s traffic will need them. `verify_road_graph.gd`
probes **every vertex of every off-grade edge** — 505 of them, the exact places a flyover centreline
is nearest in plan to a car underneath it. Proven non-vacuous by indexing off-grade segments on
purpose: 482 of 505 probes resolved to a flyover.

**Then the overlay disagreed with the docs**, reporting the lane centre 1.60 m off the centreline
where `ARCHITECTURE.md` put the spawn at 2.56 m. **The cause was a hole in the data contract, not a
bug in the arithmetic.** `roadgraph.json` publishes `width_m` as the *authored* street, while `P1-4`
draws the ribbon at `width_m × widen_for(...)`. The widening lives on the surface style and
`config.py` keeps it there on purpose — *"the graph is a description of the city, this is how wide
and how kerbed to draw it"* — so the game had no route to the width of the tarmac it was driving on,
and a lane centre from the graph sat a quarter of the widening short.

Three ways out, two rejected. **Publish the widening rules** — rejected: GDScript would reimplement
`widen_for` and its "fastest matching rule" semantics, two implementations of one rule across a
versioned interface. **Read lane geometry from the surface UVs** — rejected *for this*, and worth
keeping for `P3-8`: `TEXCOORD_0` answers "which lane am I in?", a lookup, where `P2-2` needs "where
is the lane centre?", the inverse; it is also `(0, 0)` on junction caps. **Mirror the factor in a
`.tres`** — rejected, satisfies the tuning-as-data rule literally while creating the drift this repo
keeps paying for. **What shipped: publish the derived result, not the rule.** `surface.py` records
the half-width it already computes; `export.py` carries it into `city.json` without recomputing.

**Three more defects came out of review, and the overlay found a fourth from the driver's seat.** 74
of 797 edges publish `{"en": null}`, and `str(null)` in Godot is the literal `"<null>"`, so the
`is_empty()` guard meant to substitute "(unnamed)" never fired for 9% of the network.
`has_carriageway_widths()` documented "every" and implemented "any". `_fill` re-walked the polyline
to re-derive a segment `nearest_edge` had already won, and could pick a *different* segment on a tie.
And the green marker stays on the outermost lane whatever lane the car is in — which is correct:
`lane_centre` is the **placement target**, not a tracker, and **there is no runtime lane concept to
track**, since `lanes` is authored config that nothing routes by. The overlay now says what it is.

### 2026-07-31 — `Q13` narrowed: the ramps **are** in the source

`Q13` was written as though the height model had no better input — "the source carries no Z at all".
That is true of *Road Network v2*. It is not true of the map sheets. **`INFRASTRUCTURE` is a third
mesh class holding the elevated road structures**, in `hong_kong.yaml` since `P1-2` and already
rendered — the flyovers are on screen today. `DATA_SOURCES.md` mentioned the class only as a *tiling
hazard*, never as a height source, which is why nobody had looked.

**So there are two representations of the same flyover and they disagree.** A spike sampled the
structures with `terrain.HeightField` — same class, same query shape, pointed at `INFRASTRUCTURE`
instead of `TERRAIN(TB)`: **45/45 edges covered, 95.3% of vertices, median grade 3.01%**, against
`P1-4`'s blend at 3.9% median with 10 of 39 edge ends over 12%.

**A correction while measuring.** `Q13` claimed "a third of the region's road area cannot be driven
onto". Measured: **60 of 797 edges (7.5%), 19.6% by length, 23.3% by carriageway area.**

> ❌ The conclusion drawn here — that the residual step is *topological* because 20 of 28 level-1
> edges start already elevated — was **superseded 2026-08-01 by `P2-7`'s classification.** The
> observation is right and the inference is wrong: the climb *is* in the graph, split across a
> level-0 edge and a level-1 edge, because the source flips `ELEVATION` partway up the ramp. Both
> halves need sampling; nothing needs inventing.

### 2026-07-31 — CI runs `tools/check.sh`, and **cannot** check the generated assets — closes `Q17`

Two jobs on every push and PR: `ruff` + `pytest` on Python 3.11 and 3.13, and `tools/check.sh`
against a pinned Godot. **CI runs the script, not its steps** — repeating `--import` and the warnings
sweep as YAML would have been the obvious shape and wrong for the reason the script exists.

**Three of the six checks cannot run there.** `game/assets/generated/` is gitignored build output, so
`VERIFY_GENERATED=0` skips the verify tools and the script **prints that it skipped them** — silence
is the `dea1f36` failure mode this script exists to break. Giving CI a city means running the ETL
there, 320 MB from a government server per push. Declined.

⚠️ **The skip's own guard was a false green.** `if ((VERIFY_GENERATED))` is the obvious bash and is a
trapdoor under `set -u`: `VERIFY_GENERATED=true` looks up a variable named `true`, dies with
`unbound variable` **and exits 0**; `=1x` reports "value too great for base", falls into the skip
branch, and prints `All checks passed`. A typo in the one knob that turns checks off would have
turned them all off, silently, green. Now compared as a string with only an exact `0` skipping.

**The `godot` job does not install the ETL.** `pip install -e "etl/[dev]"` drags in pyogrio's bundled
GDAL, numpy and pyproj — ~70 MB of geodata stack to format GDScript. It reads the `gdtoolkit` pin out
of `etl/pyproject.toml` with `tomllib` instead. That also forced dropping the pip cache from that
job: `setup-python` keys its cache with **no job component**, so the two jobs shared a key while
installing different things and whichever finished last would poison the other.

### 2026-07-31 — GDScript checks: the engine's own warnings, and **the checks never had exit codes**

Adopted `gdformat`, declined `gdlint` (17 problems, 16 of them one cosmetic rule across four preview
scripts), and turned on Godot's own warnings instead. Configuration in `ARCHITECTURE.md`.

**The find was that `game/project.godot` had no `[debug]` section at all**, so warnings had sat at
defaults since `P0-3` — `untyped_declaration` among them, off. Static typing is a hard `CLAUDE.md`
convention that `gdlint` has no rule for and, being a grammar-level tool with no type resolution,
could never have one.

⚠️ **Two things were wrong with the first version, and both are the same mistake.** The gate broke
two of the three verify tools, **and the breakage reported success** — `shadowed_variable_base_class`
fires on `root` in two `SceneTree` tools and on `basis`/`transform` in `greybox_builder.gd`, those
scripts then failed to *parse*, `_init` never ran, `quit(1)` was never reached, and the SceneTree
exited `0`. Eight violations shipped green under the claim "all twenty passed, zero code changes".
And it was verified with `godot … && echo PASS`, which could not have failed.

**So `tools/check.sh` exists**, and is the only thing in the repo that can fail: it greps Godot's
output for compile failures and supplies the exit code the engine will not. Tested against five
planted defects. **The sweep is separate from `--import` because `--import` does not do the job** —
an untyped variable planted in `greybox_builder.gd` went unreported, since the import step compiles
autoloads and what they reach. And the sweep must run with `game/` as the project directory: run from
the repo root, `res://` does not resolve and every script analyses clean.

**A tool was written and thrown away.** `verify_scripts.gd` walked `res://` and `load()`ed every
script; autoload identifiers do not resolve under `--script`, so it needed a deferral list, which
needed a transitive closure over `preload`, and then a `class_name` reference needed class-name
resolution too. The `--check-only` sweep gets the same coverage for four lines of shell.

### 2026-07-31 — `P1-7`: the manifest is the **only** route to the tiles

**The directory listing had to go, and it was not a style preference.** `generated_tiles.gd` found
tiles with `DirAccess.get_files_at("res://…")`. In the editor `res://` is a folder and that works; in
an exported build it is a PCK archive Godot's virtual filesystem will not enumerate, so the call
returns an empty array and the game renders an empty city **without a single error**. It would have
looked like a content problem in the first device build. Deleted rather than deprecated.

**The gate's word is "georeferenced", so something had to be able to disagree.** `tools/verify_city.gd`
measures each imported mesh against the `aabb` `export.py` recorded: **all 65 tiles agree to within
1 cm.** The tolerance is generous against what causes drift (float64 into float32 costs ~0.1 mm at
1.7 km) and tight against what it looks for (an axis flip or dropped offset moves a corner by
metres). Proven non-vacuous by nudging one tile 0.5 m east, renaming a document and shrinking
`bounds_game`: 15 findings, exit 1, nothing spurious. Two real bugs surfaced on its first run — it
grew *both* boxes before an `encloses` test, which cancels out and leaves no tolerance at all; and it
read `global_transform`, which returns identity outside the tree, and a `--script` run has no tree.

**What it cannot check is z-fighting.** `--headless` loads the dummy rasteriser, so there is no frame.
A **windowed** run can: render, nudge the camera 2 cm, diff. A fighting surface flips wholesale under
a sub-pixel move where anti-aliased edges only shift. **653 of 921,600 pixels — 0.071%** on Hennessy
Road, the diff sparse dotted lines along silhouettes and kerbs. Evidence, not proof: one camera at
one place, so flying around is still the acceptance.

**The sync is manifest-driven, not a directory copy.** `tools/sync_generated.sh` asks the ETL what
`city.json` names and copies that, which keeps the stage intermediates out of the bundle. It also
deletes tiles a previous build left behind — nothing else would notice them, because every check
starts from the manifest and the manifest has forgotten them.

**A camera-framing bug surfaced while taking the gate screenshot.** The preview scenes opened at the
origin looking at the horizon: `_ready` runs children-first, `Tiles` is the first child and `Camera3D`
the last, so `built` was emitted before the camera connected — reaching nobody, with no error.
Quietly false since `P1-4`. Emitting deferred fixes it and survives a node reorder.

### 2026-07-31 — `P1-6`: the manifest **names** the other documents, and the export stage **checks** them

**`city.json` references rather than inlines.** The alternative was tempting for exactly one reason —
the previews parse `roadgraph.json` twice in the same scene — and it was the wrong reason. Each
consumer wants a different document at a different moment, and each is separately versioned, so
merging would make a change to fare nodes bump the schema on the document carrying the tiles.

**`bounds_game` is the union of the content, not the region rectangle.** The region is 1650 × 887 m
and its geometry spans **1668 × 942 m**, because a building is assigned to a tile whole and may
overhang, and the ribbon is drawn outward from centrelines that run to the boundary. A camera framed
on the rectangle, or a spatial partition sized to it, would silently clip real buildings.

**The stage validates what it wrote, and that is the actual deliverable.** Four classes of error
exist that **no individual stage can see, because each document is internally valid in all of them**:
a fare node naming an edge the graph no longer has; a tile whose GLB was never written; a document
left over from another region; geometry outside the declared bounds. Each is a real sequence rather
than a hypothetical. Verified by breaking three at once: three findings, exit 1, nothing else.

**Reproducibility was measured, not assumed.** Rebuilt from an empty `out/`, **every one of the 199
files was byte-identical**, the sole difference being the `generated_utc` stamp. That makes "did this
change anything?" answerable by `diff` for every future ETL change.

The orchestrator calls each stage's own `main` with the arguments the documented per-stage command
would pass. Composing them any other way would create a second code path that could drift from the
one people actually run.

### 2026-07-31 — `P1-5`: fare nodes keep the **kerbside** position

**`pos` is the source position, not the snapped one.** 11 of 29 nodes lie outside even the widened
carriageway, because the published points are on the pavement and `P1-4` draws from centrelines. The
tempting fix — move each node onto the road — throws away the only thing the source surveyed. The
kerbside is where the passenger stands; where the taxi stops is derivable from `nearest_edge` and
`edge_t`, and the reverse is not. Only the height comes off the road.

**`edge_t`, `pickup` and `dropoff` were added to the contract.** `nearest_edge` alone names a road
that can be 200 m long. `pickup`/`dropoff` exist because a quarter of the published points are
**drop-off only** (66 of 275 territory-wide), and flattening that would let a player hail a fare
where no taxi may stop for one. Both free here and expensive later, since `P1-6` freezes the shape.

**The category table lives in config, and its *order* is validated.** `Status_EN` is free text with
sixteen spellings, so matching is first-hit-wins over substrings — which makes rule order
load-bearing in a way that fails silently: `DF` before `PU/DF` files every pick-up point as drop-off
only and still produces a complete, plausible `fares.json`. `load_city` now refuses a table where an
earlier rule always shadows a later one, and an *unmatched* category raises rather than defaulting.

**A bug found on the way, in `P1-3`'s code.** `clean_text` normalised to NFKC, a *compatibility*
fold that rewrites the full-width brackets Chinese sets its parentheticals in as ASCII. Harmless for
road names, wrong for 98 fare-node names that go on a bilingual HUD. Now NFC, with NFKC used only for
the null-sentinel comparison. `roadgraph.json` verified byte-identical across the change.

### 2026-07-31 — `Q8` closed: **the city itself is the fun**

The user drove `scenes/dev/city_drive.tscn` and returned the verdict that driving an HK-like map is a
fun enough gimmick already.

**This is the question the project has carried since `P0-5`.** That test cleared the handling and
explicitly could not clear the premise. The whole ETL slice was built on an unvalidated bet — that
accurate Hong Kong massing is itself the product — and it is answered now, the right way round, by
driving the real thing rather than by arguing about it. `ART_DESIGN.md`'s "accurate city, toy
vehicles" is a measured position rather than an assumption.

**What it does not license, and the word matters.** *Gimmick* is the user's own, and it is accurate
rather than dismissive — a gimmick carries a first session and says nothing about the tenth. The risk
is retired and **replaced** rather than deleted. The failure mode to avoid is reading this verdict as
covering `P3-*` or `P3-9`.

One process note: the verdict cost one dev scene assembled from parts that already existed. `Q8`
asked for "the cheapest build that lets the user judge", and the answer turned out to be *no new
build at all*, only wiring.

### 2026-07-30 — `P1-4`: the road surface is **one mesh**, capped per level, never merged

**One mesh for the region, not tiles.** The whole road network is 28,423 triangles — a fortieth of
the massing — and it is on screen whenever the player is. Tiling it would buy nothing but seams and
65 draw calls in place of one.

**Junctions are filled by the convex hull of the arms' corners.** The property that makes this right
is convexity: the hull's boundary passes through every arm's two end corners, so the mouth between
them is inside the cap by construction — no gap is possible — and it stops at the kerb line rather
than spilling into the corner between two streets, which is pavement. **393 of 393 single-level
junctions covered** under a 60-point sample.

**Capped per elevation level, which is the opposite of how `P1-3` keys nodes — and right for the
opposite reason.** A node exists so a flyover and the ramp under it stay one network. A junction cap
is a piece of tarmac, and there is none between a street and the tunnel roof 8 m below. This is where
`Q13` was found.

**Opposed carriageways are drawn twice and left overlapping**, and the decision turned out not to
exist. The premise — that two ribbons leave a gap down the middle of Lockhart Road — was never
checked against the widths. It is false: five of the six pairs already overlap at their authored
width, and the sixth overlaps by 3.42 m at 1.6×. So nothing in `surface.py` knows what a dual
carriageway is.

**Self-intersection was the one thing that needed real geometry work.** A corner tighter than the
road is wide has no inner offset curve — the naive one crosses itself, which renders as an inverted
sliver and is invisible to a one-sided collider. A slip road off Hung Hing Road loops at a **5 m
radius** while the widened carriageway is 10.2 m across.

| Repair | Folds left | Cost |
|---|---|---|
| Simplify harder before offsetting | 8 of 89 | 43% of the region's segments, visible on curves |
| Cap the width to the local turning radius | 1 | **Pinches the carriageway to zero** at 24 places |
| **Hold the inner boundary still where it would reverse** | **0** | 93 collapsed quads of 5,188, dropped at build |

The third is also what the offset of a too-tight corner actually *is*: the inside stops while the
outside sweeps past. It touches neither the centreline nor the width.

### 2026-07-30 — `P1-3`: the road graph, and three things the source forced

`python -m pipeline.roads` turns the 17 MB geodatabase into **797 edges over 615 nodes with 217 turn
restrictions in 0.80 s**: 175,610 → 3,553 vertices, 592 of 615 nodes in one component (96.3%), 679
one-way and 117 two-way, 736 at grade / 45 elevated / 15 tunnel, 723 edges named bilingually straight
from the source.

**The 23 nodes outside the main component are correct, not a defect.** Four of the six minor
components are the Central–Wan Chai Bypass tunnel, which passes under the region with no ramp inside
it; the other two are two-node stubs on the boundary.

**`ELEVATION` must not key nodes.** This reverses an implementation note that had survived since
`P0-2` — "two edges may only form a junction if their `ELEVATION` values match." It sounds obviously
right and it breaks the network: all 36 endpoints where two levels meet are **ramp touchdowns**, and
applying the rule takes the region from 6 connected components to **24**, dropping the largest from
583 nodes to 389 and cutting a 163-node elevated island adrift — most of the Wan Chai Interchange
and the Canal Road Flyover, the reason the region was chosen. **The hazard the rule was aimed at does
not exist here**, because nodes form only where centrelines share an *endpoint*, and a flyover
crossing over a street shares no vertex with it. The rule is right about crossings and wrong about
junctions.

**Roads are clipped to the region, where buildings are not.** A building is assigned to a tile whole
because splitting a mesh leaves an open shell; **a polyline cut in two is two polylines**, with
nothing to seam. It is also not optional: the geodatabase filters on bounding box, so the
Central–Wan Chai Bypass is selected and then runs **570 m out into the harbour**. Measured before
clipping, **14.2% of the region's road length was outside the region**.

**Lane counts are authored, not published.** `ARCHITECTURE.md`'s provenance table implied `lanes`
came from Road Network v2. Verified against every field of every layer: **there is no lane attribute
anywhere.** What the source does carry is a signed speed limit on the 10% of edges that differ from
the urban default, which is a decent proxy for expressway versus street.

**Endpoints coincide exactly** — 601 distinct at full float precision, nearest *distinct* pair
**2.26 m** apart — so node snapping needs no tolerance. It does need to be no finer than a
millimetre: two clusters differ in their last bits, and at a tenth of a millimetre they split, which
silently disconnected Johnston Road at Fenwick Street. Caught by a turn that would not resolve.

**The geometry is over-densified past belief** — one 51.7 m centreline carries **54,330 vertices**
(median segment 0.4 mm), and five features hold three quarters of the region's vertices.
Douglas–Peucker is a correctness measure for `P1-4`, not a size optimisation. Written iteratively
rather than recursively, because nearly-collinear input is exactly what produces both the vertex
count and the stack overflow.

**`EDGE1END` is a hint, not the truth.** It names the end of the first edge a turn passes through,
and in 4 of 217 it names an end 4–39 m away while the *opposite* end coincides exactly. Taking the
shared node resolves all 217.

**What is deliberately not in the output:** the turn layer's `EXC_VEH_TYPE` / `INC_VEH_TYPE`,
`PART_TIME_REST` and `EFF_ALL_DAYS`. One restriction in the region excludes taxis — a turn a real red
taxi may make and the graph says it may not. `roadgraph.json` has no field for it, and adding one is
a schema change on both sides, so it is recorded in `DATA_SOURCES.md` for `P3-3` and `P3-8`.

**Review pass, same day: 1.26 s → 0.80 s and 962 MB → 523 MB peak, output byte-identical.** The three
wins: `np.allclose` on 2-vectors called 41,406× in `clip` (−0.32 s, and a latent bug — its default
`rtol=1e-5` widened an intended 1 nm join test to ~15 mm at the far edge of the region); terrain
reading 224 MB of JPEG the height field never looks at (−300 MB); and the height field indexing all
six sheets when 54% of the terrain lies outside Wan Chai (−80 ms). Four hypotheses were **measured
and rejected**, which is the more useful half: vectorising `HeightField.sample` gives no gain (3,553
query points land in 2,023 distinct cells), a counting sort is no faster than `argsort`, and two
suspected hot spots cost 10 ms between them. Three correctness fixes came out of the same pass —
`parse_speed_limit` searched rather than matched, so `"Route 4, 70 km/h"` would have read as
**4 km/h**; `clip`'s fast path skipped the minimum-length rule the slow path applied; and an empty
geometry raised `IndexError` with nothing to say which feature caused it.

**Recorded, not fixed:** `roads.py` reaches into `buildings.py` for `Placement` and `read_sheet`, and
reads its terrain class out of the *buildings* config section, which crosses the format/policy
layering rule. The right shape — a shared sheet-reading module — is easier to see once more stages
have said what they need from the same sheets.

### 2026-07-30 — `Q12` closed: the published road directions **match the street**

User verdict after flying the road-graph preview: **Jaffe Road runs east**, as `roadgraph.json` says.
That clears `P1-3`'s last acceptance criterion.

**The useful part is what this licenses downstream.** Direction reaches the graph through
`TRAVEL_DIRECTION` and the digitised vertex order, and there was no independent way to know whether
that chain — or the publisher's own survey — matched the road. It does. So `P3-3` can route traffic
on the source's directions rather than treating them as a first draft to be hand-corrected street by
street, which is a materially different amount of work for Causeway Bay and every city after.

Not a blanket warranty: one street was checked, and the source's *geometry* is separately known to be
quirky. **Lockhart Road is two-way carried as opposed one-way carriageways** — three such pairs,
2.73 / 3.07 / 3.41 m apart, narrow enough to look like a doubled centreline until you measure it.
Six opposed pairs region-wide, 1.96–3.85 m apart, and that is a **floor**: it counts only pairs
sharing *both* endpoints.

### 2026-07-30 — Region placement: local origin **plus** a recorded `city_offset` (`Q10`)

Regions keep their own local frames; `city.json` gains a `city_offset` translating a region-local
position into a city-wide frame. **A single city-wide origin was rejected on measurement**: Hong Kong
spans 62.9 × 45.4 km, which would put Wan Chai ~38 km out, where float32 spacing is **3.91 mm** —
about 8% of the vehicle's measured 50.6 mm suspension sag, on a `Transform3D` Godot stores as
float32. That is the classic large-world jitter problem, self-inflicted.

**The load-bearing constraint is that a city's declared `bounds` never change.** Every region's
offset is measured from them, so they are declared in config rather than derived from the regions
that exist — a derived frame would move each time a region was added and silently relocate everything
already published. Enforced three ways: a do-not-change warning in the city file, a loader check that
every region lies inside the bounds, and a test asserting the city frame is unchanged by adding a
region. Mutation-tested.

### 2026-07-30 — `Q7`: the game-space origin is the region's **north-west** corner

`ARCHITECTURE.md` stated the conversion with the origin at the **south-west** corner — putting the
region at Z ≤ 0 — then two sections later showed a `bounds_game` example with **positive** Z.

**The two halves were never equally free.** The sign of Z is forced by handedness: Godot is
right-handed and Y-up, so rotating `+X` by 90° counter-clockwise about `+Y` lands on `−Z`. If east is
`+X`, north **must** be `−Z` or the city comes out mirrored. Only *where zero sits* was ever a
choice, and it is a pure translation.

**North-west chosen** because the forced Z sign means anchoring at the northern edge is the only way
to keep the region in the positive quadrant. Tile indices now run `(0,0)`…`(10,5)` instead of
`(0,0)`…`(10,−5)` — natural numbers, row 0 at the north, as in a raster. The rejected south-west
origin is the GIS bbox convention and is defensible; it loses on negative tile indices being a
papercut paid every time anyone writes a filename or a debug print. Origin northing is now **ceiled**
where easting is floored, rounding outward.

⚠️ **Non-negativity is a property of the region, not of the source data.** `fetch.py` downloads every
sheet that *intersects* the region, so geometry on disk runs past all four edges and anything north
or west still indexes negative. **Clipping before indexing is part of the data contract, not an
optimisation.**

Two errors of mine, caught in review. I wrote that float32 holds millimetre precision to ~65 km; it
is **~16 km** (2¹⁴), and that number was the sole quantitative input to `Q10` — being 4× optimistic
made a city-wide origin look comfortably safe. Then, correcting it, I quoted spacings sampled at
powers of two while labelling them decimal kilometres.

### 2026-07-30 — `P1-2`: vertex clustering, whole-mesh tiling with one exception, and the terrain verdict

`python -m pipeline.buildings` turns the six cached sheets into **65 tiles × 3 LOD tiers in ~3 s**
(2,274 source meshes read, 881 clipped away, 1,393 placed): **989,212 → 400,139 → 183,773** triangles
at 0.0 / 1.5 / 4.0 m cells. All tiles pass `verify_tiles.gd` in Godot headless.

**The geometry is verifiably really Wan Chai**, which matters because a coordinate bug here produces
a plausible-looking city in the wrong place — the failure this pipeline is most exposed to. Taking
the tallest building and converting its centre back to WGS84: **374.5 m at 22.28011 N, 114.17358 E**
against Central Plaza's published 374 m at 22.28028 N, 114.17361 E — a **19 m** offset, inside its
own 78 m footprint. Right building, right height, right place, through node matrix → HK1980 → region
origin → tile.

**Vertex clustering, not quadric decimation.** The source is extruded footprints, so clustering keeps
silhouettes blocky and axis-aligned — which *is* the art direction, where quadric decimation would
smooth the corners and fight it. It is also robust on triangle soup, which this is. And its
aggressiveness is one number in metres, so the tiers stay tuning data.

**The cluster key includes the facing, not just the cell.** Merging on position alone averages a wall
normal into the roof normal above it and rounds off the faceting the whole style rests on. ⚠️
"Lossless" is precise about **positions**: it was first implemented as a cluster mean, which is not
the same thing — summing k equal doubles and dividing by k need not reproduce them. Taking a
representative fixed that.

**Meshes are assigned to tiles whole, except those too big for a tile.** Splitting a building at a
boundary leaves an open shell and makes half of it pop. But the source contains elevated road
structures **up to 1,984 m long in a single mesh**, and whole-mesh assignment handles those two ways,
both wrong: one whose centre falls outside the region **vanishes entirely** — taking a viaduct that
crosses the whole map with it — and one whose centre falls inside gives a 150 m tile a 2 km bounding
box. Oversized meshes are partitioned by triangle instead.

**Godot needed a fix the ETL could not make.** Godot 4.7's glTF importer reads `COLOR_0` but leaves
`vertex_color_use_as_albedo` **off**, so every tile imports as a white block — with or without a
material in the file, because in glTF `COLOR_0` always multiplies base colour. Corrected by a
post-import script wired as a project-wide importer *default*; per-file would not survive a fresh
clone, since generated assets are gitignored. Separately: the `"normalized": true` flag on the colour
accessor is load-bearing — drop it and Godot reads every colour as 1.0 and the whole city renders
white, silently. Both fail silently and look identical.

**No glTF library.** `pipeline/gltf.py` reads and writes the format directly in ~380 lines. The read
side would have used a few percent of trimesh or pygltflib, and the write side has to lay out
accessors and buffer views by hand under either.

❌ **Terrain: measured, and not affordable as it ships.** Clipped to the region it is still **404,669
triangles**, and its six GLBs total **267 MB** — 224 MB of JPEG and 43 MB of geometry. Over on
triangles, texture memory and bundle size at once, by roughly 2× each. *(Reassessed 2026-08-01: the
geometry was never the problem. See the ground-colour entry.)* **Two things keep it in the pipeline
regardless:** it is the **height field** `Q11` needs, and judging "does photographic ground read wrong
next to flat-shaded massing?" still needs eyes on it.

### 2026-07-30 — `Q11`: sample the terrain height field under every vertex

Opened by `P1-2`, closed by `P1-3` the same day. `elevation_levels` was always an *offset* per
grade-separation level; what was missing was what it is an offset **from**. The answer is the ground,
and the ground is in the sheets we already download.

| | Before (from the datum) | After (from sampled ground) |
|---|---|---|
| Level 0 road height, median | 0.00 m | **4.21 m** |
| Level 1 (flyover), median | 6.00 m | 10.08 m |
| Level −1 (tunnel), median | −8.00 m | −3.53 m |
| Vertices with no terrain under them | — | **0** |

**The cross-check is the point.** `P1-2` measured the region's building bases at a median **4.29 m**
by a completely separate path — glTF node matrices out of the sheets. Roads land **8 cm below the
doorways**, which is what a kerb is. Nothing was tuned to make those agree.

Chosen over two alternatives: sampling the nearest buildings' bases is available without the terrain
but noisy (podium bases sit above the pavement, maximum 75.92 m), and one authored offset per region
is cheapest and wrong the moment the road climbs toward Kennedy Road, since the region spans 55 m of
relief. `roads.ground: terrain | datum` in city config, because a city whose sources carry no height
field must still be able to build.

### 2026-07-30 — `P1-1`: the fetcher derives its own sheet list

`fetch.py` handles two source shapes — fixed-URL (roads) and index-derived (buildings) — because that
is what the publishers offer, and the second shape is what keeps hard rule 3 intact. The pipeline
knows "some feature property holds a download URL"; that it is called `Format_glTF` is config.

**The six sheets are derived, and they match.** Intersecting the region bounds with the 3,456-feature
index selects exactly the six `P0-1` recorded by hand. Nothing in config names them. That agreement
is the real result: the bounds, the datum and the index all line up.

Decisions worth knowing: **caching is fetch-once, not fetch-if-changed** (`CLAUDE.md` fixes the
snapshot, so re-running must not quietly adopt upstream's new month of road data); **`REVISIONDATE`
is per sheet**, so a re-snapshot only re-downloads what moved — measured, a forced re-snapshot costs
**3.2 MB instead of 265 MB**; **downloads are atomic**; **the API key is never written down**, since
URLs are read from the fetched index at run time and everything recorded passes through `redact()`;
**bounds are reprojected before comparison, never compared across datums**, pinned by a test using a
sheet that only the HK1980 misreading selects; **edge contact counts as overlap**, since sheets tile
edge to edge; and **selecting zero tiles is an error.**

**Review found four defects the end-to-end run could not have surfaced**, all reproduced before
fixing and the two most serious mutation-checked:

1. **A short HTTP response was committed as complete, then cached forever.** `read(amt)` returns
   `b''` on a premature close rather than raising, so a server dropping mid-transfer produced a
   truncated file that `os.replace` committed and the manifest recorded *at its short size*, making
   the truncation a permanent cache hit. Reproduced against a real socket: 5,000 bytes accepted
   against a declared 1,000,000. The atomic-rename machinery only ever protected against interruption
   of *our* write.
2. **A failure partway through discarded the whole manifest**, so one dropped connection on the sixth
   sheet cost the record of the five that landed — ~283 MB re-pulled after one transient error.
3. **`--force` re-downloaded everything, contradicting its own documentation.** The docs described
   the better tool, so the code changed to match.
4. **A poisoned index would have cached as "zero buildings" silently** — a portal answering an outage
   with HTTP 200 and a JSON error body parsed fine, selected zero sheets, and exited 0.

### 2026-07-30 — `P0-1`: building data is **fully scriptable**; the top data risk is retired

Reverses the `P0-2` finding that "the top data risk has moved from roads to buildings." That
conclusion came from reading the CKAN resource list — which genuinely does only point at interactive
portals — and stopping there, instead of opening the portal's own Downloads panel.

**The CSDI portal serves a sheet index, not the models.** It offers the non-textured dataset as
ordinary GIS vector formats, which looked wrong for 3D buildings and is what prompted a closer look.
The payload is a territory-wide index of **3,456 sheet polygons**, each carrying direct download URLs
and a per-sheet `REVISIONDATE` that is the natural cache key. **One public key covers all 3,456
sheets** — not per-user, not per-session — and it must not be committed anywhere.

Verified by downloading `11-SW-10C` (44.3 MB). Three findings that shaped `P1-2`: coordinates are
**already in Godot's convention** (`(easting, elevation, -northing)`), vertices are **unwelded at
exactly 3.0 per triangle** so flat shading is baked in, and **"non-textured" describes the buildings,
not the terrain** — terrain ships with a JPEG.

**New risk registered:** 612 triangles per building is far more than an LOD1 extrusion needs.
`DATA_SOURCES.md` previously claimed "no decimation needed"; corrected. LOD tiers became load-bearing
rather than optional.

### 2026-07-30 — Region bounds confirmed **WGS84**, by measurement

`P0-4` flagged that the region bounds were authored with no datum stated, and that HK1980 vs WGS84 is
a **~304 m** question in Hong Kong. That is load-bearing rather than pedantic: the two readings select
**different sheets** — WGS84 gives a contiguous `11-SW` block, HK1980 swaps two of six. A third of the
region rode on an unstated assumption. Settled by comparing sheet `11-SW-10C`'s real building
positions against both readings: the WGS84 projection matches to within metres and the HK1980 one is
out by ~250 m, and the terrain node sits at the WGS84-projected sheet centre exactly.

### 2026-07-29 — `P0-5` gate: released conditionally; the fun question moves to Phase 1

User verdict: *"verified and seems acceptable, but I don't know if it is fun or good until we have
either the Hong Kong scene or game mechanism."*

**Read as a pass on what `P0-5d` could actually test, and a rejection of its premise.** The handling
cleared its criterion — no blocking problem. But `PLAN.md` claimed the grey box would answer "is this
a game?", and it did not. Recorded as `Q8`. **Phase 1 is released**, because the gate's purpose was
to avoid sinking ETL effort into a game that does not work, and the user's answer is that the ETL
output is a *precondition* for knowing.

**Deliberately not actioned:** sustained full lock still spins the car, and `brake_force = 900` gives
3 m/s² of braking against 5.33 m/s² of acceleration, so **the car accelerates faster than it stops**.
Both real, neither blocking, both belonging with `P2-3`.

**Three bugs found in `P0-5b`/`P0-5c` by measuring rather than reading**, plus a fourth from review —
and none of them is a defect any linter catches:

- **Anti-roll signs were inverted**: force pushed *down* on the already-compressed side, amplifying
  roll instead of resisting it. The car flipped on the first hard corner.
- **Coasting drag divided by `delta`**, making it framerate-dependent and ~35× too strong.
  `apply_force` already integrates over the tick.
- **A `Node3D`-typed `@export` does not resolve from a hand-authored `.tscn`** — it silently read
  null and the camera never moved. Worth remembering for every scene authored outside the editor.
- **Steering was inverted.** `InputRouter.steer` is `+1` for right, but a *positive* rotation about
  `+Y` turns the `-Z` forward vector toward `-X` — left. The headless tests missed it because they
  only ever steered one direction and never checked which.

Also fixed in that pass: wheel raycasts accepted wall faces as ground (free traction and a launch
ramp off any building), and road slabs were exactly coplanar with the ground plane and z-fought
across their whole surface.

The controller verified what it was built for: **drifting is *cheaper* than gripping** — 0.270 speed
scrubbed per second against 0.297, at a 12.6° peak slip angle against 16.4° — because breaking
lateral grip removes the cornering force that was scrubbing speed. Under `VehicleBody3D` the same
manoeuvre cost 30–57% extra and spun to 162°. Suspension settles at **50.6 mm sag** against 50.7 mm
predicted.

### 2026-07-29 — `P0-5a`: **custom raycast on `RigidBody3D`**, not `VehicleBody3D`

Measured, not assumed. A throwaway headless spike drove a `VehicleBody3D` through settle →
accelerate → steer → drift under Godot 4.7.1 + Jolt.

**`VehicleBody3D` is not broken under Jolt.** It instantiates, simulates, accelerates, steers and
brakes; the wheel query API works. Anyone repeating this spike should not expect a crash — the
problem is subtler. **The tuning schema is inexpressible:** of 18 `HandlingProfile` fields, 4 map
directly, 4 are fightable, and **10 are absent** — both speed caps, three steering-curve fields, two
drift fields, all three collision/recovery fields.

**The decisive finding: `wheel_friction_slip` is isotropic.** One friction number covers every
direction, so `grip_lateral` and `grip_longitudinal` collapse into each other, and a drift cannot
break lateral grip without destroying traction and braking with it. Measured while holding throttle,
friction × 0.35 on the rear axle only cost **30% of speed over 2 s** — an implied scrub of 0.151/s
against a target of 0.080 — at a **162.6°** peak slip angle against a 14° threshold. That is a full
spin, not a slide, and it violates `GAME_DESIGN.md` on two counts at once.

**Could it be tuned out? Partly — and that is the argument against it.** Yaw damping, counter-steer
assist and per-axle friction curves would suppress the spin, but that is an arcade correction layer
built on a physical model actively resisting it, leaving `VehicleBody3D` contributing only suspension
raycasts. Every future tuning change would be a negotiation with the engine rather than a dial, and
vehicle feel is expected to be iterated on more than anything else in the project.

Consequences: `HandlingProfile` gains a `Suspension` group and an `anti_roll` field. **Spring rate is
specified as natural frequency in Hz, not a raw N/m constant**, so it stays correct when vehicle mass
changes — but it is *not* gravity-independent: static sag is `g_eff / (2πf)²`, so `gravity_scale =
1.6` deepens sag by the same 1.6×. Anyone retuning `gravity_scale` must rescale the frequency with
it. Wheel **geometry** deliberately stays out of the profile — that is per-vehicle model data; the
resource describes feel, which is shared across the roster.

### 2026-07-29 — Device floor: **A13 / Adreno 618**, named as two separate floors

- **iOS floor: A13** — iPhone SE 2nd gen (2020) or iPhone 11 (2019).
- **Android floor: Adreno 618 tier** — Vulkan 1.1, 4 GB RAM. Spans Snapdragon 710/712/720G/730/730G.

**These are two decisions, not one, and the old single-device phrasing hid that.** The iOS floor is a
*support-matrix* question — A12 is off the current iOS train. The Android floor is a *performance*
question, and it is the only one that constrains the budget: A13 is roughly 3–4× the GPU throughput
of the Adreno 618 tier, so anything holding 60fps on the Android floor is free on iOS.

**The Mobile renderer requires Vulkan**, so the real floor is "Vulkan 1.1 with a maintained driver"
before it is any particular chip. Chosen over a more conservative floor because **Hong Kong skews
high-end** — a global-market floor would cost art fidelity for users this TAM does not have. It also
makes the perf budget coherent rather than arbitrary: <150 draw calls, <300k triangles and <128 MB
texture are sane Adreno-618 numbers.

### 2026-07-29 — `P0-4`: config declares its **datum**, not just its CRS

**HK1980 and WGS84 differ by ~304 m on the ground in Hong Kong.** Measured, not assumed: EPSG:2326's
own natural origin is published on the HK1980 datum, and feeding those identical digits in as WGS84
lands 304 m away — a fifth of the width of the region, and far larger than the ~10 m people expect.
So `hong_kong.yaml` declares `crs.geodetic` alongside `crs.projected`, `config.py` refuses to load
without it, and `test_crs.py` asserts the two datums disagree by >250 m. **That last assertion is
really a canary:** if it ever shrinks, PROJ has fallen back to a *ballpark* transformation.

**Verification is against external facts, not the code's own output.** The load-bearing test projects
the published grid origin and expects the published false easting/northing, reproducing them to
sub-millimetre.

Other choices worth knowing: `transformer()` is `@cache`d per CRS pair; `always_xy=True` everywhere,
because EPSG:4326 officially declares lat-then-lon and a silent axis swap is the classic way to
relocate a city into the Indian Ocean; `GameTransform` is **pyproj-free** so the per-vertex hot path
never re-enters PROJ; the origin is **rounded to whole metres**, so a library upgrade cannot renumber
every tile; and `deck_height_m()` raises on an unmapped `ELEVATION` rather than defaulting to 0.0.

⚠️ **Elevation-level keys reject `bool`, not just non-`int`.** PyYAML implements YAML 1.1, where a
bare `on`/`off`/`yes`/`no` key resolves to a boolean — and because `bool` subclasses `int`,
`isinstance(key, int)` waves it through. `False == 0` as a dict key, so a stray `off:` would silently
redefine **ground level**. Verified: a config with a boolean key loaded without error and returned
42.0 m for level 1.

### 2026-07-29 — Foundational decisions

**Engine: Godot 4.7.1, Mobile renderer, Jolt.** Chosen after the target shifted from a free web
release to a commercial store product, reversing an earlier web-first recommendation. Decisive:
native mobile performance versus Android WebView GPU throttling, and one codebase covering mobile,
desktop and a web demo. *(Originally 4.6; moved to 4.7.1 because Homebrew's cask ships it and nothing
depended on 4.6.)*

**Language: GDScript, not C#.** Desktop C# is fully supported; Android and iOS remain
**experimental**; web export is **unsupported entirely**. Mobile is a primary target and the free web
demo is the planned marketing funnel. The complex code lives in the Python ETL anyway, so C#'s
tooling advantage earns little. Performance escape hatch is **GDExtension** (C++/Rust), not C#.

**Targets: mobile + desktop/Steam.** Adds a gamepad/keyboard input layer, resolution-independent UI,
a desktop LOD tier and a Steam build path — ~15–20% engineering overhead, accepted for the broader
revenue options.

**Region: Wan Chai → Causeway Bay.** Chosen over Tsim Sha Tsui and Central: a natural circuit exists
in the real road layout, map edges are diegetic, and it has real grade separation without Central's
multi-level data risk.

**Building source: non-textured / 3D-BIT00 Level 1, NOT photogrammetry.** The tile-based
photogrammetry mesh has ground gaps, level differences and vehicles baked into the geometry; a prior
public attempt concluded it suited flight rather than driving simulation. Decimating photogrammetry
produces blobs, not low-poly style.

**Art direction: accurate city, toy vehicles.** Stylise the actors, not the stage. Recognition is the
product, so building proportions stay accurate; charm comes from Choro-Q vehicle proportions.

**Monetisation: free download + one-time unlock, deferred to launch.** Not F2P (2–5% conversion needs
volume this TAM cannot supply, and retention mechanics would corrode a 3-minute arcade loop). Not
paid-upfront (paid games are <5% of App Store revenue, and "it feels like Hong Kong" cannot be
conveyed in a screenshot — a free slice *is* the marketing). **Build implication:** design Wan Chai
to be standalone-playable.

**`P0-3` acceptance was split.** The written criterion "builds and runs on the device floor" bundled
a scaffold together with Android SDK setup, Xcode, an Apple signing identity and physical hardware.
Split into `P0-3` (project imports clean, exports verified) and `P0-3b` (signed on-device builds).
Android exports to a 25 MB APK using the prebuilt template with no Gradle or Android SDK required,
which is better than expected; iOS fails only on a missing App Store Team ID, which is the correct
failure. Discovered here: `rendering/textures/vram_compression/import_etc2_astc` must be enabled or
Godot refuses to export **any** arm64 target, including Apple Silicon macOS.

---

## Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Novelty does not survive the first session | **Medium** | The honest reading of the `Q8` verdict — "gimmick" was the user's own word, and a gimmick carries one session. `P3-*` is whether the fare loop sustains; `P3-9` is whether recognition holds up to people who know the streets. Three levers named 2026-08-01, all built from assets already scheduled: the **losable style chain** (`P3-2b`); a **drivable roster** (the minibus, double-decker and tram are already authored for `B3`, so making one drivable costs a `HandlingProfile` and a mount point); and **world-embedded challenges** pinned game-side to edge IDs. Only the first is in the slice; the others are named so **Phase 5** does not reinvent them. **Amended 2026-08-02:** `P3-9a` now asks this risk directly and earliest — a `B2` city with no fares, traffic or score is its harshest form — and `P3-11`'s generator is what makes the drivable-roster lever cheap, since the same script that builds the taxi builds the minibus, double-decker and tram |
| Doesn't read as HK to locals | **High** | `P3-9` with ≥3 real drivers; run again every phase after |
| The city has no ground | **Medium** | Between the roads and under the buildings is skybox. `B2` asks "does this read as Wan Chai?" and cannot be answered over a void. Mitigated by `P3-10`, scheduled into `B2` for exactly that reason — and `B2` now runs **first**, so this is next up rather than third in line |
| The player's car is two boxes | ✅ Closed | **2026-08-03**, by `P3-11` and pending only the review drive. 24 → 772 triangles, generated from the chassis the scene already published. The lesson it leaves: **the docs specified the car so fully that it read as done**, which is how a capability with no owner hides |
| Grade separation is unreachable | Medium | `Q13`. **Largely closed 2026-08-02** by `P2-7`'s sampling — median step 0.04 m — but the network is still *closed to driving* by `P2-2`'s refusal. Opening it is `P4-1` |
| Carriageway occupied by solid geometry | Medium | `Q19`, 5.17% at bumper height, real since collision shipped. Wants a verify tool that fails the build |
| Perf misses 60fps on device floor | Medium | Budget defined up front; untextured merged tiles are the main lever; `P2-6` is a dedicated pass — and it needs `P0-3b`'s hardware |
| TAM too small to be commercial | Medium | City-agnostic ETL is the scaling answer — city packs, not one city. `Q8` strengthens this: if recognition is the product, a second city is a YAML file |
| Landmark depiction IP | Low | Untextured massing; legal sight-check before launch (Phase 7). **Now the top item in that brief** — the government data terms were read verbatim on 2026-08-02 and are permissive, so depiction is the one question left with a plausible adverse answer. See `LICENSING.md` |
| GPLv3 forecloses the App Store | **Medium** | **New 2026-08-02.** GPLv3 §6 conflicts with App Store terms, so store builds need a separate proprietary grant — available only while one party owns the whole copyright. Mitigated by `CONTRIBUTING.md` taking contributions **inbound MIT**. Zero exposure today (no outside contributors) and **no retrofit** once one declines, so the file must land before the repo goes public |
| GDScript learning curve | Low | Small codebase; complexity lives in Python |

**Retired:** *Road data lacks Z values* (`Q1` — no Z, but `ELEVATION` encodes the level; region
holds). *Real geometry isn't fun to drive* (`Q8`, 2026-07-31 — replaced by the novelty risk above).
*Source data quirks* (`P1-3`/`P1-4` — both turned up and both were handled; the residual dissolved on
measurement). *Building meshes blow the triangle budget* (`P1-2`/`P2-1` — worst-case visible is
150,374 against 300k). *Terrain does not fit any budget* (224 of the 267 MB was the JPEG; `P3-10`
ships none of it).

---

## Metrics

Record measured values here, not estimates. **Bundle size is measured from a PCK, never summed from
source files** — that rule cost `Q16` two wrong answers in opposite directions.

| Metric | Target (mobile) | Latest | Date |
|---|---|---|---|
| FPS on device floor | 60 | — (no device yet — `P0-3b`) | — |
| FPS, Chrome on macOS, 2880×1450 | — | **119** (worst frame 9.7 ms) | 2026-07-31 |
| Draw calls | < 150 | **53** ✅ | 2026-08-01 |
| Visible triangles, worst measured | < 300k | **150,374** ✅ | 2026-08-01 |
| Resident triangles, worst measured | — | **280,807** (a ceiling, not a gate — 236,882 before `P3-10`'s ground) | 2026-08-05 |
| Texture memory | < 128 MB | **0** — no textures ship, ground included | 2026-08-05 |
| Bundle size | < 200 MB | **32.30 MB** PCK, + wasm. **27.73 MB immediately before `P3-10`**, measured either side of the same build with one variable changed, so the **+4.56 MB is the ground and its collider** — and only the total was measured, not the split | 2026-08-05 |
| Tile triangles, LOD0 / LOD1 | — | **521,798 / 253,070** (434,149 / 222,375 before the ground) | 2026-08-05 |
| Ground standing proud of the carriageway | — | 3.3% of area, **0.36% of sampled points** — the gap between the two is `Q24` | 2026-08-05 |
| Road surface triangles | — | **25,028** (35,039 before the 2026-08-04 kerb fix) | 2026-08-04 |
| Boot to drivable (web, warm) | — | 830 ms, of which 260 ms is tile instantiation | 2026-07-31 |
| Tab memory (web) | — | 307 MB | 2026-07-31 |
| ETL full-run time | — | **3.0 s**, whole region from an empty `out/` | 2026-08-02 |
| Deck error, \|error\| p90 vs shipped tiles | ≤ 0.50 m | **0.095 m** ✅ | 2026-08-02 |

---

## Planned vehicle roster (user direction, 2026-07-29)

Real models, not generic cars. Recorded because the **drive layout differs across them**, which is an
architecture constraint rather than an art note.

| Vehicle | Drivetrain | Notes |
|---|---|---|
| Old Toyota Crown (Comfort) | LPG, **rear-wheel drive** | The iconic HK red taxi |
| New Toyota Crown | Hybrid, **front-wheel drive** | |
| Toyota Hiace | CVT | Van proportions — tall, high centre of mass |

**Already supported without code changes:** `WheelMount.drives` is authored per wheel in each vehicle
scene, so RWD and FWD are scene data. Each vehicle gets its own `HandlingProfile`, and
`centre_of_mass_offset_y` plus `anti_roll` already cover the Hiace's height.

**This is why drift bias is derived from chassis geometry, not from `drives`.** `VehicleController`
computes `WheelMount.is_front` from the wheel's position along the chassis. Had it keyed off `drives`
or `steers`, the front-wheel-drive Crown would have had its drift bias inverted.

**Not yet modelled:** transmission character. `engine_force` is a flat constant with no gears or
torque curve, so an LPG Crown, a hybrid and a CVT would accelerate identically. Flag it before the
roster work in Phase 5.
