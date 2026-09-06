# hud_style.tres

Rationale for `game/tuning/hud_style.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

White is the city speaking, dark is the car speaking. See hud_style.gd.

⚠️ The plate white is NOT the road's paint constant.
roadmarks.tres records the marking white as its fifth authored copy and
boxjunctions.tres the yellow as its third; a sixth and a fourth here would be
that debt again, and a street name plate is not paint (Q53, Q79).

⚠️ THE SIZE RULE, measured off the references this layout is taken from: the
speed reads at about 7% of frame width and the plate under about 18%, which is
where Midtown Madness 2 puts the same two things. Anything larger reads as
furniture, and the city is the deliverable.

⚠️ EVERY KEY BELOW IS REQUIRED. `hud_style.gd` declares no defaults, so a key
missing here is zero rather than something sensible; `verify_hud.gd` refuses a
zero it would otherwise draw with.

## `warn_disc = Color(0.761, 0.102, 0.149, 1)`

NO ENTRY (TS115), the same sign standing on 179 posts in the region. The red
and the two proportions are quoted from the world sign and graded against it
by verify_hud; the bar draws in plate_field. See hud_style.gd and Q81.
