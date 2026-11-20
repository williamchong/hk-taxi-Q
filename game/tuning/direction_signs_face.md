# direction_signs_face.tres

The faces of TD's gantry boards (`P3-105`, `Q265`), on the sign lettering's own shader
(`signs_text.gdshader`): an opaque atlas with the field colour baked behind the legend, so no
transparency pass.

- `tools/generated_scene_import.gd` duplicates this resource per imported scene and hands the copy
  the region's atlas (`direction_signs_text.png`, uniform `glyph_atlas`). `glyph_atlas` is
  deliberately not set here: a baked path would point at a generated, gitignored, per-region asset.
- The atlas is a texture budget (`Q63`): `generated_layer.gd`'s `DIRECTION_SIGNS_ATLAS_BUDGET_PX`
  declares the ceiling and `mesh_contract.gd` fails a bundle over it, an undeclared texture, or a
  declared one that is missing.
- `plate_roughness = 0.55`, `sheeting_glow = 0.06`: must equal `signs.tres`, which the gantry's
  steel and the boards' backs are drawn on. A board and its face catching light differently reads
  as a bug. Its own file rather than `signs_text.tres` because the importer swaps a material by
  name, and the two atlases are different images.
