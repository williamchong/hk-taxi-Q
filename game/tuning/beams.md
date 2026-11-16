# beams.tres

Rationale for `game/tuning/beams.tres` (`Q119`).

How many thrown beams the renderer can pay for, and how `BeamBudget` hands them out (`P3-11e`).
Forward Mobile pairs a fixed list of spot lights per rendered object, and the road chunk under the
cars is one object, so every beam on it contends for the same list.

Every key is required: `beam_profile.gd` declares no defaults (`Q150`), so a missing key reads as
zero and the editor's writer cannot drop a value. `BeamBudget.adopt` refuses a zero `regrant_hz`.
`verify_beam_budget.gd` refuses a shipped cap or rate of zero and pins this path to
`BeamProfile.PATH` and `BeamBudget.PROFILE_PATH`.

- `max_spot_lights` 8: measured. Brightness is linear to eight and the ninth light on an object is
  absent, with no warning. Two lamps a car, so four cars. Lower it for headroom; raising it buys
  nothing.
- `regrant_hz` 6.0: deliberately not every frame. Beams re-ranked at frame rate swap at frame rate
  and flicker.
- `swap_margin_m` 8.0: hysteresis, so two cars abreast do not trade beams every regrant.
