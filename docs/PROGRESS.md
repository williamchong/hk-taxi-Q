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
| `P0-3b` | Mobile device build verification | ⬜ Not started | Split out of `P0-3`. Needs `Q4`, a signing identity and hardware. Not on the critical path. |
| `P0-4` | ETL scaffold | ⬜ Not started | |
| `P0-5` | Grey-box fun test | ⬜ Not started | **The critical path.** Unblocked by `P0-3`. Subjective gate — needs the user |
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
| Q4 | Confirm the device floor | Sets the whole perf budget. **Assumed:** iPhone XR (A12) / Snapdragon 730-class, ~2019–2020. Now also blocks `P0-3b` — we cannot verify on a device floor we have not named. | user | 🟡 Assumed |
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

---

## Decision log

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
