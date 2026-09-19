---
paths:
  - "etl/pipeline/config_blocks/signs.py"
  - "etl/pipeline/signs.py"
  - "etl/pipeline/sign_text.py"
  - "etl/pipeline/sign_sheets.py"
  - "tools/sign_face_survey.py"
  - "etl/tests/test_signs.py"
  - "etl/tests/test_sign_sheets.py"
  - "game/assets/shaders/signs*.gdshader"
  - "game/tools/verify_signs.gd"
  - "game/tuning/signs*.{tres,md}"
---

# Traffic signs, their lettering, and the removed signals — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- 🔴 **`signs.glb` is a LIBRARY since `P5-2` and the city is `signs_placements.json`** (`Q115`): one mesh
  per face variant plus a unit `pole`, stood by 1,251 entries — 671 plates + 83 lettering quads + 497
  poles, asserted in the stage. `triangles`/`vertices`/`aabb` still describe what is DRAWN and read the
  merged build's numbers, because the expansion was measured against it (0.13 mm). ⚠️ **A mirrored
  board is its own mesh, never a negative scale** — under `cull_back` a mirror is a missing plate, and
  `placement_of` refuses one. ⚠️ **The rotation convention is `GeneratedLandmarks.placement_of`'s and
  `gltf.placed_positions`'s, one per side** — the ETL's copy is shared by `clearance.py`, the
  occupancy grader and the signs, and was three hand-written copies before `P5-2`'s review; do not
  write another. ⚠️ Draw calls are **one per library mesh
  and the shadow passes multiply it**: +35 on the throttle route for 24 meshes, not +22.
- **`signs.outset_m`, `max_shift_m`, or `signs._register`: paste `signs.json`'s `drawn`,
  `poles_drawn`, `posts_kept_as_surveyed`, `posts_over_shift`, `posts_in_carriageway`,
  `posts_merged_after_shift` and `shift_m`, before and after — and A/B render one street that
  carries kept posts.** 🔴 **`shift_m` is an absolute value, so it CANNOT report the direction of
  the move it measures.** That is what let the registration pull 95 of 654 posts *toward* the
  carriageway — a correction whose stated reason runs outward only — through three published
  distributions and a green `check.sh` (`Q78`). ⚠️ **`drawn` is the invariant, NOT `poles_drawn`**:
  a post left where it was surveyed keeps its separation from its neighbour, so
  `posts_merged_after_shift` can only fall and `poles_drawn` rises by exactly what it stops folding
  away. A stop-condition on `poles_drawn` halts a correct build. ⚠️ **The identity must still
  close** — `len(shift_m) == poles_drawn + posts_over_shift + posts_in_carriageway +
  posts_merged_after_shift` — which is why a post that does not move appends a real `0.0` rather
  than being skipped. ⚠️ **A position on this layer cannot be graded against anything published**
  (`Q62`), so the evidence is an **A/B render at one fixed camera** — `city_preview.tscn` with an
  explicit `--camera`/`--look`, never a driven frame, and shoot each side twice and `cmp` them.
  ⚠️ **`railings.py` computes `shift_m` the same way and is deliberately NOT
  aligned**: a fence is a run and the bar is per sample, so a conditional push would zigzag it. Do
  not "restore consistency". ⚠️ **A widening change is a sign-position change** — `surface.floor_default_m`
  moves the drawn kerb and therefore moves every post, silently and plausibly. Numbers in `Q78`.
- **`signs.faces_against_traffic`, `_facing_from_side` or `_plate_facing_deg`: paste `signs.json`'s
  `plates_turned`, `no_entry_against_flow`, `no_entry_on_two_way` and `facing_away`, before and
  after — and mutation-check the flag by turning it off and confirming the counters move.** 🔴 **The
  counter that stood here before `Q72` was a tautology that certified the wrong state**: every NO
  ENTRY in the region faced the traffic it was not addressing while `no_entry_with_flow` read 0,
  because the rule turned every one-way sign to face its traffic and 0 was unreachable. The test of
  a counter here is not whether it reads 0 but whether **any reachable configuration makes it
  non-zero**. ⚠️ **`no_entry_against_flow` is a config-and-code ratchet and NOT data-sensitive** —
  no readable input moves it, only dropping the flag or the turn does — so mutate it rather than
  reading its 0, and do not describe it as grading the city. ⚠️ **`plates_turned` must equal the drawn NO ENTRY family exactly** (195 = `TS115` 177 + `TS116` 18 today; the invariant is the equality, not the number); a fall means the turn stopped happening, and a turn that stops renders perfectly.
  ⚠️ **Which faces turn is config, never a code constant** — a second face quietly gaining the flag
  rotates a whole code across the region and renders perfectly (`Q64`'s class).
  ⚠️ **A facing change cannot be graded against anything published** (`Q62`), so the evidence is an
  **A/B render at one camera**, before and after. Numbers in `Q72`.
- **`signs.faces`, `signs.colours`, any plate dimension, or `pipeline/signs.py`'s glyph geometry:
  also `tools/sign_face_survey.py`, and paste its two tables.** It rasterises the config's own face
  from `layer_polygons` and diffs it against the cell TD published that code in, as **area and
  extent per livery colour**. It is the only instrument that can see a face drawn in the wrong
  *proportions*, and on its first run it found five: `TS414` drawn in negative, `TS735` given the
  wrong border, `TS115`'s bar a quarter short, `TS116`'s ring a third thick, and every straight
  mandatory arrow 17% small (`Q67`). ⚠️ **Area alone is not enough and that is the point**: the
  shipped NO ENTRY bar and the published one have the same area to four points and are visibly
  different bars. ⚠️ It **grades rather than checks** and exits 0 whatever it finds — the truth side
  is a drawing whose corner radii and keylines this pipeline does not model. ⚠️ **It cannot see a
  face on the wrong CODE**, because it looks the config up by code and fetches that code's cell;
  `Q64`'s own defect would still be invisible. Run `--contact` and *look at the page* when the change
  touches which code draws what.
- **`text` layers, `text_cell_px`, `text_source`, or `pipeline/sign_text.py`: paste `signs.json`'s
  `text_plates`, `text_facing_away`, `text_atlas_px` and `text_coverage`, before and after** — and
  move `GeneratedLayer.SIGNS_TEXT_ATLAS_BUDGET_PX` in the same diff. 🔴 **This is the one place the bundle
  ships an image**, admitted by `Q63`'s declaration check rather than in spite of it, so a budget
  with slack in it is a metric nobody reads. ⚠️ **`text_coverage` is the detector**: a cell cropped
  off the lettering bakes paper, and a blank square on a plate renders as the blank plate it already
  was. ⚠️ `text_facing_away` must be **0** — a quad wound the wrong way under `cull_back` is not a
  backwards word, it is no word. ⚠️ **A lettering change is also a shader change** — `check.sh` exits
  0 on a shader that fails to compile, so render and `grep -i "shader error"`. Numbers in `Q68`.
  🔴 **The atlas ships as its own file, `signs_text.png`, named by `city.json` under
  `signs_text_atlas` — never embedded in `signs.glb`, and that is not a style preference** (`Q70`).
  Godot's `gltf/embedded_image_handling` defaults to *Extract Textures*, so an embedded image
  becomes a PNG beside the asset that the manifest has never heard of, and `sync_generated.sh`
  deletes exactly that — on every run, leaving `verify_signs` red until someone forces a re-import
  by hand. ⚠️ **Anything that adds a second image owes the same treatment**: name it in the
  manifest, or the sweep is right to delete it. ⚠️ **`signs.json`'s `bytes` is `signs.glb` alone**
  and `text_atlas_bytes` is the image — two numbers where there was one.
- 🚫 **`P3-17`'s signal layer is REMOVED — code and all (`Q77`, then `P3-35a` / `Q133`, 2026-09-19, the
  user's call: "we will re-add it much later").** `city.json` lost the `signals` key at schema **34**;
  the code is at the commit before `P3-35a`. 🔴 **Bringing it back is a PORT, not a re-declared
  block** — it owes `P5-2`'s library + placements shape first — and the reason it was dropped still
  stands: an unlit head asserts a signal out of service and a lit one cannot be derived from anything
  published. ⚠️ What a return must keep is in `Q76`. ⚠️ `signs.disc`, `facing_from_side` and
  `plate_frame` stay public for it.
