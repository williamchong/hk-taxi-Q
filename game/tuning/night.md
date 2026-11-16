# night.tres

A look `day_to_night.tres` blends the rig through (`Q160`); `day_to_night.md` has the table and the
order. A city night, not a black one (the user's call): navy zenith over a horizon that still
glows, blue ambient at 0.75 so an unlit wall is dark and legible.

A copy of `clean_daylight.tres`. Only what `LightingRig.BLENDED` and `BLENDED_SKY` name is read
from this file (ambient, fog, glow intensity, saturation, the sky's four colours). Its switches,
tonemapper and glow levels are carried unread; a property that should move with the hour is added
to those lists first.
