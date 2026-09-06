# clean_daylight.tscn

Rationale for `game/scenes/world/clean_daylight.tscn`, kept beside it because Godot's resource writer
drops every comment on save. Each heading is the line the block sat above;
`Overview` is the file as a whole. `tools/check.sh` requires this file to exist
and stay non-empty, and refuses any `;` line in the resource itself.

## Overview

The lighting rig for the clean facade look — midday rather than golden hour.

The alternative to `golden_hour.tscn`, and the same shape: one Environment
resource plus one sun, instanced by every scene that needs to be looked at.
Which rig ships is one `ext_resource` line in each dev scene, and **both must
name the same one** — the city getting judged under two looks at once is what
that file's header warns against, and splitting the rigs does not change it.

⚠️ **A low warm sun is load-bearing for the *other* look and not for this one.**
Golden hour flatters flat shading by raking across faces; a white city under a
low sun goes to two values, blown and blue, with the massing lost between them.
The sun here is at 48° for the same reason the reference art's is: it separates
the faces by shading rather than by shadow, and leaves the long shadows to be
something the street furniture casts rather than the whole skyline.

## `[node name="Sun" type="DirectionalLight3D" parent="."]`

`directional_shadow_mode = 1` is SHADOW_PARALLEL_2_SPLITS, and 400 m is the
chase camera's far plane. Both carried over unchanged from `golden_hour.tscn`,
which measured them — see its header for the per-cascade primitive counts and
the three artefacts that ruled out a single cascade. Nothing about raising the
sun changes that argument, and re-deriving it here would only let the two rigs
drift apart.
