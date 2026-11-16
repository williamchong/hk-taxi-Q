# signs_text.tres

The lettering on a sign plate (`P3-20`), the bundle's only textured material.

- `tools/generated_scene_import.gd` duplicates this resource per imported scene and hands the copy
  the region's atlas (`signs_text.png`, uniform `glyph_atlas`). `glyph_atlas` is deliberately not
  set here: a baked path would point at a generated, gitignored, per-region asset.
- The atlas is the texture budget (`Q63`): `generated_layer.gd` declares the pixel ceiling and
  `mesh_contract.gd` fails a bundle over it, an undeclared texture, or a declared one that is
  missing.
- `plate_roughness = 0.55`, `sheeting_glow = 0.06`: must equal `signs.tres`; a plate and its words
  catching light differently reads as a bug. Two files because one material cannot hold two
  shaders.
