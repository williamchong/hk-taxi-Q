---
paths:
  - "etl/pipeline/signboards.py"
  - "etl/pipeline/signboard_text.py"
  - "game/assets/shaders/signboards_text.gdshader"
  - "game/tuning/signboards_text.{tres,md}"
  - "game/assets/shaders/signboards_screen.gdshader"
  - "game/tuning/signboards_screen.{tres,md}"
  - "etl/pipeline/config_blocks/signboards.py"
  - "etl/tests/test_signboards.py"
  - "tools/signboard_colour.py"
  - "game/tools/verify_signboards.gd"
  - "game/tuning/signboards.{tres,md}"
  - "game/assets/shaders/signboards.gdshader"
---

# Signboards — before marking work done

`P3-103`, `Q260`. The Buildings Department's registered signboards as coloured boxes on the walls,
their two faces lit at night, lettered with a generic shop name — **off** (`text.lettered: false`, the user's call), so colour only; two authored boards are LED screens. No canopies.

- Rerun `python -m pipeline.signboards` on both regions and read its line: `read`, `drawn`,
  `no_wall`, `stacked`, `over_road`, surveyed against palette colours, `triangles`. Then the
  manifest's `snap_m` (Wan Chai p50 0.27 m, p90 0.98 m), `facing_moved` and `facing_away`.
- 🔴 **`facing_away` is 0.** A box faces every way, so a frame does not catch a face wound
  inward; `test_every_face_is_wound_the_way_it_is_lit_and_only_the_faces_glow` does, per mount.
- 🔴 **Never a real name, logo or lettering.** The database names no shop and nothing from a
  photo but one colour ships.
- **The colour survey is build time and separate**: `tools/signboard_colour.py` downloads only
  under `PHOTO_PREFIX` into `etl/sources/signboard_colour/` and writes `signboard_colour.json`.
  Rerun it when a region is added (`--regions`), and look at `--sheet` before trusting a change to
  the outline reader. A colour under `survey_min_share` or with no outline takes the palette.
  `LICENSING.md` item 6.
- **The palette is a colour outside `materials:`**, the third exemption in
  `test_no_colour_escapes_the_materials_table`. Do not add another key that authors a colour.
- **Facing**: the board turns to the named street (`facing_weight_m`) when that wall is within
  reach. 613 of 2,031 boards in Wan Chai move. A change to the weight is judged on a plan or a
  frame on a corner, not on the count.
- **Heights are config** (`mounts:` `base_m`, `road_base_m`): a canopy stage will lift them. A
  blade over the drawn carriageway is raised to `road_base_m` above the ground (a double-decker is
  4.4 m). Nothing collides (`verify_signboards.gd`).
- Cost: Hennessy Road's street viewpoint +12,168 primitives and +5 draws; PCK +580,060 bytes
  (web, the glbs moved aside for the before side). A new mount or cell size re-measures both.
- 🔴 **The lettering is generic**: `signboard_text.pick_name`, seeded by `OBJECTID`, from
  `text.prefixes` and a trade's `suffixes`. FEHD's licences are read for position only; their
  `NSEARCH03_*` shop names must never be read. A new word must be in the brush subset: rerun
  `tools/make_fonts.py` (it reads the `text:` block) and `test_every_character_the_block_can_letter_is_in_its_font`.
- The atlas is a coverage mask, one cell a character, under `SIGNBOARDS_TEXT_ATLAS_BUDGET_PX`
  (512 x 1024 for 95 characters at 64 px). More vocabulary raises the atlas; raise the budget in
  the same diff, never ahead of it.
- The trade weights (`licences.boost` / `elsewhere`, `streets:`) are authored. The user corrects
  HK facts: a new street or trade is his call, shown on a frame.
- **Screens are authored** (`screens:`, by `OBJECTID`): the register does not say which board is
  one. A screen's loop is generic — never a brand, a logo or a real advert — and it is not lettered.
- A shader change owes a night render (`--time-of-day=0.95`) and `grep -i "shader error"`.
