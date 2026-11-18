# signboards_text.tres

The signboards' lettering (`P3-103` step 2, `Q260`): `TEXT_MATERIAL` in
`etl/pipeline/signboard_text.py`, dispatched by `TEXTURED` in `tools/generated_scene_import.gd`,
which duplicates it per region and hands the copy the imported atlas, on `signs_text.tres`' terms.

- The atlas is a coverage mask (`signboards_text.png`, generated, never committed), one cell a
  character, rendered from the committed brush subset. `cut` 0.5 is the alpha scissor: a texel
  under it is not ink. A scissor rather than a blend keeps the lettering in the opaque pass.
- The ink rides `COLOR_0`: the ETL picks the one of `signboards.text.inks` with the most contrast
  against the board.
- `ink_glow` 2.0: the lettering (`COLOR_0` alpha 0) burns brighter than its board's 1.5, so a name
  reads on its face at night. Under the glow pass's 3.0 threshold.
- `roughness_value` 0.6: the board's own.
- If the dispatch is lost the glyphs sample white and every quad draws as a block, so
  `verify_signboards.gd` checks the shader and the budget.
