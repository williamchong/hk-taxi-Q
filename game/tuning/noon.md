# noon.tres

A look `day_to_night.tres` blends the rig through (`Q222`); `day_to_night.md` has the table and the
order. 12:00, the brightest look of the day: a clean blue sky with no grey band and a neutral
ambient at 1.25. Sky colours are the user's picks from frames. The fog is the day's.

`ground_bottom_color` stays the day's neutral grey: the sky is the ambient's source, and a blue
ground half turns every shadow purple.

A copy of `clean_daylight.tres`. Only what `LightingRig.BLENDED` and `BLENDED_SKY` name is read
from this file; the rest is carried unread (`night.md`).
