# golden_hour.tscn

Rationale for `game/scenes/world/golden_hour.tscn`, kept beside it because Godot's resource writer
drops every comment on save. Each heading is the line the block sat above;
`Overview` is the file as a whole. `tools/check.sh` requires this file to exist
and stay non-empty, and refuses any `;` line in the resource itself.

## Overview

The one lighting setup, per docs/ART_DESIGN.md "Lighting": golden hour by
default. A low warm sun flatters flat shading, separates building faces
without any texture work, and gives long readable shadows.

Instanced by every scene that needs to be looked at, rather than each one
carrying its own Environment — two dev scenes lit differently means the city
gets judged twice under two looks, neither of them the shipping one.

The Environment is a .tres so the values stay tuning data (CLAUDE.md rule 4).

## `[node name="Sun" type="DirectionalLight3D" parent="."]`

`directional_shadow_mode = 1` is SHADOW_PARALLEL_2_SPLITS. A .tscn stores the
enum as a bare integer, so the name has to live here or the value is
unreadable. It was unset, and Godot's default is 2 — four PSSM cascades.

Per-second primitives on a `drive.sh` run from the HKCEC spawn:

            t=1      t=3      t=6
  4 casc  244,888  215,071  263,077   <- the default this replaces
  2 casc  159,739  132,845  155,032   -35%
  1 casc  110,644   93,206  112,142   -55%, and unusable, see below

⚠️ One cascade is what ART_DESIGN.md "Lighting" specifies for the desktop
tier, and it was tried first. It has a distinct artefact at every distance:

  150 m  shadows fade out 120-150 m while the camera draws to 400 m, so the
         far half of a long street is flatly lit with a visible cutoff
  250 m  the HKCEC shadow across Expo Drive East comes out visibly banded —
         the shadow map's own texels through the filter, at 0.092 m each
  400 m  the HKCEC shadow disappears entirely; the caster is behind the
         camera and falls outside the ortho volume's near plane

The distance ones are one artefact, not two: `directional_shadow_fade_start`
is a *fraction* of max_distance (0.8), so shortening the distance moves the
fade band with it. Two cascades gives a fine near split and a coarse far one,
which is what removes all three at once.

400 m rather than the old 600 because it is exactly the chase camera's far
plane in city_drive.tscn and the streamer's unload distance — past it nothing
is drawn, so shadow reach and draw distance now end together. Distance costs
nothing either way: 150, 250, 400 and 600 measure bit-identically.

shadow_bias, shadow_normal_bias, pancake_size, blur and fade_start are left at
engine defaults — peter-panning was the artefact to expect, since Godot scales
directional bias by cascade extent, and a matched pair with the car in open
sun shows its shadow still attached. Shots in build/driver/. See PROGRESS.md.
