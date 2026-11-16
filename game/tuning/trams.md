# trams.tres

How the trams run (`P3-4`, `Q176`). Every value is authored: neither TD nor Hong Kong Tramways
publishes a timetable, dwell or running speed. `tram_system.gd` says what each rule does.

Every key is required: `tram_profile.gd` declares no defaults and `TramSystem` refuses a zero, or
a `brake_max_mps2` not over `brake_mps2`.

- `trams = 16`: the fleet at once, about one per 350 m of the 5.7 km of directed track.
  `verify_trams.gd` measures how many stand held.
- `cruise_mps = 7.0`, `accel_mps2 = 0.9`, `brake_mps2 = 1.2`, `brake_max_mps2 = 3.5`: 25 kph, a
  slow heavy thing the taxi overtakes. Amber is judged at the hard rate, as in `traffic.tres`.
- `dwell_s = 10.0`: long enough to see the stop and pass, short enough that a queue clears.
- `gap_m = 3.0`, `look_m = 35.0`, `follow_heading_deg = 45.0`: `look_m` covers the planned stop
  from cruise (20.4 m) plus gap and body. The heading bar is `traffic.tres`'s; the taxi is stopped
  for whatever its heading.
- `start_clear_m = 25.0`, `run_off_m = 30.0`: a tram sets out 30 m past the region's edge, out of
  sight, and only with 25 m clear.
- `bogie_m = 2.7`: half the 5.39 m between the mesh's axles (`tools/make_parked.py`), so the body
  swings.
- `taxi_half_m = 2.5`: the taxi bumper a tram stops `gap_m` short of. The body is set back over
  its boot (`Q190`: nose 2.07 m ahead of the origin, rear 2.505 m behind), so the further is used.
- `seam_join_m = 30.0`, `seam_heading_deg = 40.0`: each region's rails are cut at its rectangle;
  these join the ends. Both tracks must join on both sides or a tram vanishes at the seam;
  `verify_trams` prints the joins.
- `bell_voices = 3`, `bell_range_m = 110.0`, `bell_repeat_s = 4.0`: three rings at once is a busy
  street; four seconds is impatient without being an alarm.
