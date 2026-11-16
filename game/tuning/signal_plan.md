# signal_plan.tres

How long a signalled junction holds each part of its cycle (`P3-3b`, `Q173`). The stages are the
ETL's (`signals_plan.json`); this is only their timing. Every value is authored: TD publishes no
stage plan, timings or intergreens.

A stage runs red-and-amber, green, amber, all red. A one-axis junction (a crossing) runs its one
stage and then `crossing_s` of all red. Each junction is offset along its cycle by its id.

Every key is required: `signal_plan_profile.gd` declares no defaults and `SignalController` refuses
a zero. `verify_signals.gd` reads this file.

- `red_amber_s = 2.0`: the British sequence and value; TD's own figure is unread.
- `green_s = 15.0`: short on purpose. A fare lasts a minute or two, so a 60 s red would be most of
  a trip. A game value, the user's to move.
- `amber_s = 3.0`: the British value; TD's own figure is unread.
- `all_red_s = 2.0`: clearance, so a car that entered on amber clears the box.
- `crossing_s = 10.0`: a one-axis junction's second stage. Nobody walks yet, so it is only how long
  traffic waits.
