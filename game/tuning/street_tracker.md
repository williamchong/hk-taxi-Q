# street_tracker.tres

The street plate's dwell (`P3-24`, `P5-26`). The key is required: `street_tracker_profile.gd`
declares no default and the tracker refuses a zero.

- `dwell_s = 0.6`: how long a different street must stay nearest before the plate follows it.
  Seconds, not metres, because the artefact is a name changing faster than it can be read. About
  8 m at 50 kph, inside a junction mouth and well short of a block.
