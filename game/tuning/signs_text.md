# signs_text.tres

Rationale for `game/tuning/signs_text.tres`, kept beside it because Godot's resource writer
drops every comment on save. Each heading is the line the block sat above;
`Overview` is the file as a whole. `tools/check.sh` requires this file to exist
and stay non-empty, and refuses any `;` line in the resource itself.

## Overview

The lettering on a sign plate (`P3-20`) — the bundle's only textured material.

`tools/generated_scene_import.gd` maps the ETL's `signs_text` material name to
this path, and this dispatch does something no other row in that table does:
it **duplicates** this resource and hands the copy the atlas the glTF brought
in. Every other generated mesh shares one material across the whole city; this
one cannot, because the texture is region data and the resource is committed
code. The duplicate is per imported scene, so it is still one material for the
whole region's lettering, and still one draw call.

🔴 **This is the file that stops `Texture memory` being 0.** `Q63` decided that
deliberately and bought a ceiling with it: `generated_layer.gd` declares how
many pixels the sign layer may ship and `mesh_contract.gd` fails the bundle
above it, fails an *undeclared* texture anywhere else, and fails a declared
texture that never arrived. Nothing here is allowed to become the reason that
ceiling stops being read — a bigger atlas is a number moved in a diff.

⚠️ **`glyph_atlas` is deliberately not set here.** A path baked into this file
would point at a generated, gitignored, per-region asset — so it would resolve
on the machine that built the city and nowhere else, and a fresh clone would
open the editor to a broken resource. The dispatch supplies it at import.

⚠️ **The two surface numbers duplicate `signs.tres` rather than sharing it.**
They are the same painted aluminium and they must stay the same: a plate and
the words on it catching the light differently reads as a rendering bug. Kept
as two files anyway, because one material cannot hold two shaders and the
alternative — the plate shader growing a texture it does not use — would put a
sampler on 671 plates to serve 74.

Here rather than as shader defaults because CLAUDE.md hard rule 4 makes tuning
data, not constants.
