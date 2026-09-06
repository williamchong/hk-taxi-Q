# road_markings.tres

Rationale for `game/tuning/road_markings.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The road's markings — lane lines, centre lines, kerbside yellows (`P3-12`).

`tools/generated_scene_import.gd` maps the ETL's `road_markings` material name
to this path and only this path, so this file is the switch: delete the entry
there and the surface falls straight back to the `BaseMaterial3D` it imported
with before `P3-12`, with no rebuild.

Here rather than as shader defaults because CLAUDE.md hard rule 4 makes tuning
data, not constants — and beside `golden_hour.tres`, because the low sun these
are judged under is tuned in the same directory. Loaded as **one** resource for
the whole region: the road surface is a single primitive.

⚠️ **The widths are in lane widths, not metres, and they are wider than life.**
A truthful line is under a pixel at the distance the player is actually looking,
and the honest version simply vanished. The pitch values are the opposite case:
V is metres, so `dash_length_m` and `dash_gap_m` are the real thing and want no
fudge.

🔴 **A U-lane is NOT `lane_width_m`, and this block said it was.** U is
normalised to the ribbon *as drawn*, so one U-lane is `2 * half_width / lanes`
— **5.12 m** across this region (p10 4.16, p90 5.12) against the 3.20 m
`lane_width_m` authors. This used to read "0.031 is a real 10 cm line at this
region's 3.2 m lane … it ships at 0.05 — a 16 cm line", which understated every
width here by the 1.6x widening. `line_width` 0.05 is a **26 cm** line;
`centre_width` 0.055 is **28 cm**. `surface.py::_u_metres` is the same
correction on the ETL side, and `P3-12` records what confusing the two cost.

⚠️ **The centre line is TD's DOUBLE white line and its two numbers are the
sheet's.** `CT174/51-5(1)F` gives RM1001 DOUBLE LINES `LINE WIDTH = 150,
LINES SPACING = 100`, and LINES SPACING is the **clear gap, not a pitch** —
`centre_gap` is that gap, held at exactly the sheet's 100/150 of `centre_width` (0.0367) so
the shape stays TD's whatever legibility does to the scale. Both are 1.88x life
size, which is `line_width`'s exaggeration and not a second decision.

🔴 **This is a marking that says something, and it is drawn from an INFERRED
join.** A double continuous white line instructs *no overtaking*; `Q117` finds
the opposed pairs geometrically, so the instruction rests on that pairing and
not on a survey. TD publishes the real thing — **19,308 m of RM1001 in this
region**, second only to RM1109 — and drawing that instead is the sourced route
and the open item. `draw_centre_line` is the switch if a recognition round
reports the instruction as wrong rather than the line as missing.

⚠️ **`fade_m` is not only cosmetic, and it is the one value here that is priced
rather than chosen.** A junction cap overlaps its arms rather than abutting
them — 6,051 m² of 52,985 m² of cap area, 210 of 1,398 trimmed ends — and that
overlap is invisible today only because cap and carriageway are the same colour
in one material. Markings drawn under it read as a patch. So the fade has to
reach at least as far back as the cap does, and that was measured per arm end
across the region rather than guessed:

  overlap depth   p50 0.00   p90 1.17   p95 2.36   p99 3.62   worst 4.21 m
  overlapped at all: 203 of 1,398 ends (14.5%), reproducing the published 210

**6 m clears every end with 42% margin.** It shipped at 9 for one round, from
no measurement at all, and the cost of that is the other direction of the same
dial: an edge shorter than twice the fade never carries a full marking, and the
region's edges are short — p10 is 4.0 m, p25 is 12.5 m.

  fade   edges with no marking at all   share of carriageway area
  9 m    169 of 797  (21.2%)            8.7%
  6 m    121 of 797  (15.2%)            6.0%   <- ships
  5 m    104 of 797  (13.0%)            5.2%

Going below 5 m starts eating into the measured worst case, and the overlap
figure is a derivation from the published trims rather than the hull's own
reach — so the margin is doing real work. Some of that 15.2% is *correct*: a
4 m link between two junctions is a junction mouth, and real roads do not mark
one. The real fix for the rest is a non-convex cap, which is polygon clipping
and is not built. `Q53`.

⚠️ **`draw_double_yellow` is the one marking here with no source behind it.**
Every other line is either geometry (a lane boundary) or a published flag —
`TRAVEL_DIRECTION`, `BUS_ONLY_LANE`. A kerbside waiting restriction is neither.
It is near universal in urban Wan Chai, which is the argument for drawing it,
and it is still an invention on streets `P3-9a`'s drivers know. On its own
switch for exactly that reason: this is the first thing to turn off if a
recognition round reports the markings as wrong rather than as missing.

Judged at the `street` and `kerb` viewpoints per `ART_DESIGN.md`'s table, and
at a junction approach — the fade is what wants looking at, and the question is
whether the lines stop where a driver expects rather than whether they stop.
