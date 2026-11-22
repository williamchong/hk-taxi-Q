---
paths:
  - "etl/pipeline/config_blocks/signs.py"
  - "etl/pipeline/signs.py"
  - "etl/pipeline/drawnroad.py"
  - "etl/pipeline/sign_text.py"
  - "etl/pipeline/sign_sheets.py"
  - "tools/sign_face_survey.py"
  - "etl/tests/test_signs.py"
  - "etl/tests/test_sign_sheets.py"
  - "game/assets/shaders/signs*.gdshader"
  - "game/tools/verify_signs.gd"
  - "game/tuning/signs*.{tres,md}"
---

# Traffic signs and their lettering — before marking work done

- **Library** (`Q115`): `signs.glb` is one mesh per face variant plus a unit `pole`; the city is
  `signs_placements.json`. A mirrored board is its own mesh, never a negative scale. The rotation
  convention is `GeneratedLandmarks.placement_of` / `gltf.placed_positions`; do not write another
  copy. Draw calls are one per library mesh times the shadow passes; only `pole` casts
  (`GeneratedLayer`'s `shadow_meshes`, checked by `verify_signs.gd`).
- **`signs.outset_m`, `max_shift_m`, `signs._register`** (`Q78`): `tools/battery.py signs --region
  <r> --before <root>`. From `signs.json` compare `drawn`, `poles_drawn`,
  `posts_kept_as_surveyed`, `posts_over_shift`, `posts_in_carriageway`,
  `posts_in_carriageway_area`, `posts_merged_after_shift`, `shift_m`. A/B render a street with
  kept posts: `city_preview.tscn`, explicit `--camera`/`--look`, each side twice (`Q62`).
  - `shift_m` is absolute and cannot report direction. The registration pushes outward only; a
    post it would pull toward the road is kept as surveyed. `railings.py` is deliberately not
    aligned.
  - `drawn` is the invariant, not `poles_drawn`. `len(shift_m) == poles_drawn + posts_over_shift
    + posts_in_carriageway + posts_merged_after_shift`; an unmoved post appends 0.0.
  - The foot is also tested against the asphalt (`drawnroad.drawn_carriageway`, `Q237`): a kerb
    station inside a junction is a share. A change to R or its islands moves which posts stand.
  - A widening moves the drawn kerb and every post.
- **`signs.faces_against_traffic`, `facing_from_side`, `_plate_facing_deg`** (`Q72`): compare
  `plates_turned`, `no_entry_against_flow`, `no_entry_on_two_way`, `facing_away`, and
  mutation-check the flag by turning it off. A counter counts only if a reachable configuration
  moves it. `no_entry_against_flow` is a config-and-code ratchet, not data-sensitive.
  `plates_turned` must equal the drawn NO ENTRY family (`TS115` + `TS116`). Which faces turn is
  config. Evidence is an A/B render.
- **`signs.faces`, `signs.colours`, a plate dimension, glyph geometry**:
  `tools/sign_face_survey.py`, and paste its two tables (`Q67`). It rasterises the config's face
  and diffs area and extent per livery colour against TD's cell; area alone is not enough. It
  exits 0. It cannot see a face on the wrong code (`Q64`): run `--contact` and look at the page.
- **`text` layers, `text_cell_px`, `text_source`, `sign_text.py`** (`Q68`): compare `text_plates`,
  `text_facing_away` (must be 0), `text_atlas_px`, `text_coverage`, and move
  `GeneratedLayer.SIGNS_TEXT_ATLAS_BUDGET_PX` in the same diff. `text_coverage` detects a cell
  cropped off the lettering. A shader change owes a render and `grep -i "shader error"`; the
  shader is shared with the lamps.
- **`back_to_back`, `stack_of`** (`P3-92`): TD files a double-sided sign as two features at one
  point and one angle (18 of Wan Chai's 24 `TS324` poles). The second hangs on the first's back;
  compare `plates_back_to_back`. Only a flagged face pairs: `TS115` twice on a pole still stacks.
- **Three ways a cell is read** (`Livery`): a knockout (`TS101`, `TS324`), black ink on paper
  (`TS102`), and a coloured ink on paper (`chromatic`: `TS322` / `TS323`, whose border is the same
  ink, so the cell is the whole plate). A `text` layer's `accent` adds the cell's red as a second
  ink (`TS3643`'s taxi); red is the only cast `_accent` reads. Green is in `sign_sheets.INK` and
  `_plate_mask` for the stand plates. A new baked face owes a look at `signs_text.png`.
- The atlas ships as `signs_text.png`, named by `city.json`'s `signs_text_atlas`, never embedded in
  `signs.glb` (`Q70`): Godot extracts an embedded image to a file the manifest does not name, and
  `sync_generated.sh` deletes it. Any second image owes the same. `signs.json`'s `bytes` is the
  `.glb` alone; `text_atlas_bytes` is the image.
- **Signals**: `P3-17`'s surveyed signal-head layer is removed (`Q77`): an unlit head asserts "out
  of service" and a lit one cannot be derived from anything published. It does not come back as a
  re-declared block. Signals now ship as an authored phase plan (`Q173`); see the `signals` rule.
  `signs.disc`, `facing_from_side` and `plate_frame` stay public for it.
- **Colliders** (`Q191`): `region.tscn`'s `posts` stands a cylinder up every `pole`. A face drawn
  standing on its origin would gain a post (`check_posts`). Never a collider in `signs.glb`.
