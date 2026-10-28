# signal_plan.tres

Rationale for `game/tuning/signal_plan.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

How long a signalled junction holds each part of its cycle (`P3-3b`, `Q173`). The STAGES are the
ETL's (`signals_plan.json`: approaches grouped by travel axis); this table is only their timing.
🔴 **Authored, every value**: TD publishes no stage plan, no timings and no intergreens, and its
signals are largely vehicle-actuated, so no one fixed timing is "the" Hong Kong one.

A stage runs red-and-amber, green, amber, then all red, and the next stage begins. A one-axis
junction (a crossing) runs its one stage and then `crossing_s` of all red. Each junction is offset
along its cycle by its id, so the city does not change at once.

⚠️ EVERY KEY BELOW IS REQUIRED. `signal_plan_profile.gd` declares no defaults, so a missing key
reads as zero, and `SignalController` refuses to run on a zero. `verify_signals.gd` reads this file.

## `red_amber_s = 2.0`

Red and amber together before a green: Hong Kong's signals follow the British sequence (road signs
in Hong Kong closely follow the UK's). 2 s is the British value; TD's own figure is unread.

## `green_s = 15.0`

Short for a real junction (actuated greens run 7–60 s) on purpose: the region is small and a fare
lasts a minute or two, so a 60 s red would be most of a trip. A game value, the user's to move.

## `amber_s = 3.0`

The British value; TD's own figure is unread. Long enough that a car at the mouth's speed limit can
stop or clear.

## `all_red_s = 2.0`

The clearance between two stages. Every approach red, so a car that entered on amber clears the box
before the cross street moves.

## `crossing_s = 10.0`

A one-axis junction's second stage: the crossing it serves. Nobody walks yet, so this is only how
long the traffic waits.
