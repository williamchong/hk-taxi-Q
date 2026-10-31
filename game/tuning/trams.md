# `trams.tres`

How the trams run (`P3-4`, `Q176`). Every value is AUTHORED: TD and Hongkong Tramways publish no
timetable, dwell or running speed in any dataset this project reads. `tram_system.gd` says what
each rule does; this says why each number.

⚠️ EVERY KEY BELOW IS REQUIRED. `tram_profile.gd` declares no defaults, so a missing key reads as
zero and `TramSystem` refuses to run. `brake_max_mps2` is held as a difference over `brake_mps2`.

## `trams = 16`

The fleet at once, over about 5.7 km of directed track: one every ~350 m of rail. `verify_trams.gd`
measures how many stand held; the frame cost is in `Q176`.

## `cruise_mps = 7.0`, `accel_mps2 = 0.9`, `brake_mps2 = 1.2`, `brake_max_mps2 = 3.5`

25 kph: a slow, heavy thing the taxi overtakes, and not one that holds up a shift. The acceleration
and the planned brake are an old tram's gentle pair; the hard rate is what an amber is judged at and
what one cut up by the taxi uses. As `traffic.tres`, amber is judged at the hard rate.

## `dwell_s = 10.0`

Long enough to see the tram stop and to pass it, short enough that a queue behind it clears.

## `gap_m = 3.0`, `look_m = 35.0`, `follow_heading_deg = 45.0`

Three metres short of what is ahead. `look_m` covers a stop from cruise at the planned rate
(20.4 m) with room for the gap and the body. The heading bar is `traffic.tres`' value; the taxi is
stopped for whatever its heading.

## `start_clear_m = 25.0`, `run_off_m = 30.0`

A tram sets out 30 m past the region's edge, out of sight past the closure, and only with 25 m clear:
one body and a tram's stopping room.

## `bogie_m = 2.7`

Half the 5.39 m between the mesh's axles (`tools/make_parked.py`), so the body swings as a tram does.

## `taxi_half_m = 2.3`

Half the saloon's length, read off the taxi's mesh: the bumper a tram stops `gap_m` short of.

## `seam_join_m = 30.0`, `seam_heading_deg = 40.0`

The two regions' rails are each cut at their rectangle, so the ends stand a gap apart; `verify_trams`
prints the joins. Both tracks must join on both sides or a tram vanishes at the seam.

## `bell_voices = 3`, `bell_range_m = 110.0`, `bell_repeat_s = 4.0`

Three rings at once is a busy street. Past 110 m the bell is not worth a voice. Four seconds is
impatient without being a car alarm.
