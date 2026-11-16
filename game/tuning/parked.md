# parked.tres

How the parked roster (`P3-73`, `Q161`) is read against the clock and cut into cells, plus the
liveries and masses shared with traffic. What a placement is (kind, hours, chance) is the ETL's
`parked_placements.json`. Every key is required: `parked_profile.gd` declares no defaults and
`ParkedLayer` refuses a zero cell or an empty day.

- `clock_start_h = 7.0`, `clock_end_h = 21.0`: the hours the rig's `time_of_day` 0 and 1 mean.
  Must equal `shift.tres`'s `opens_h` / `closes_h`; `verify_day_cycle` holds it. A free drive on
  DAY TO NIGHT runs past 1 (`Q225`) and the roster reads that as the hours after 21:00. The vans'
  8-19 window closes inside the day and the single-yellow fill (19-7) opens at twilight, so the
  night street carries more cars. Metered bays open at 08:00, so a shift's first game hour stands
  no metered car.
- `cell_m = 300.0`: `prop_cells.tres`'s cell. One `MultiMesh` per kind per cell.
- `range_margin_m = 15.0`: how far past the camera's `far` (400 m, `city_drive.tscn`) a cell's
  nearest edge must be before it is rebuilt, so nothing pops in view. Covers a bus's half length.
  There is no `range_m` or `visibility_range_end` (`Q214`): that range is measured to the cell's
  centre, so a whole cell appeared at once about 190 m ahead.
- `poll_s = 1.0`: how often the layer reads the clock and walks the cells. A game hour is 60 s
  (`Q233`).
- `reroll_s = 90.0`: a hidden cell holding a placement with a chance under 1 is redrawn after
  this. Longer than a lap of the region, so a bus is still there when the player comes straight
  back.

## `liveries`

Per library mesh, the colours its livery panels may wear (`Q167`). One is drawn per placement on
`ParkedRoster.LIVERY_ROLL`, so a colour listed twice is twice as common and a vehicle keeps its
colour. sRGB, painted by `vehicle_body.gdshader` over the vertices `make_parked.py` stamps
`MARKER_LIVERY`.

- Not listed where the colour means something: the taxi (red is the urban licence), the bus
  (Citybus yellow over blue), the tram (green).
- `minibus`: roof only, green 2 : red 1. Green is a scheduled route, red a free-running one.
- `car_a`, `car_b`, `van`: mostly white, silver, black and grey. No saturated red: the player's
  taxi is meant to be the one chromatic car in the frame (`ART_DESIGN.md`).
- `lorry`: cab and box, white 4 of 7 plus a blue, a dark green and a yellow. Authored.
- `coach`: the belt band only; the body stays white.
- `motorcycle`: tank, fairing and fender.

## `hazard_sources = ["layby", "frontage"]`

Which placement sources stand with hazards flashing (`P3-3f`), at the taxi's beat
(`vehicle_lamps.tres`). A lay-by is for stopping, and a `frontage` van or coach is loading. Not
`stop` or `stand` (the stop and rank licence the wait), not `bay` or `fill` (parked, switched off).

## `masses_kg`

Kerb mass of each kind something moves (`Q180`, `Q182`, `Q183`), against the taxi's own 1,400 kg
(`cars/crown_comfort.tres`). Kerb, not loaded (the user's call): the one figure every maker
publishes. A kind not listed (coach, lorry, motorcycle) is a wall. A pushed body takes
`m_taxi / (m_taxi + m)` of the change in speed, so a few hundred kg barely moves a hit.

| Kind | kg | Source |
|---|---|---|
| `bus` | 15,000 | Alexander Dennis Enviro500 MMC, 15,300 kg unladen (ADL's Mexico sheet) |
| `car_a` | 1,600 | Toyota Camry 2.5 Hybrid, 1,570–1,670 kg |
| `car_b` | 2,100 | Toyota Alphard IV, 2,060–2,290 kg |
| `van` | 2,200 | Hiace H300 long-wheelbase, 2,175–2,225 kg |
| `minibus` | 3,500 | export Coasters 3,100–3,450 kg; no figure for the Hong Kong LPG light bus |
| `taxi` | 1,400 | Crown Comfort, about 1,390 kg kerb (`Q153`); every licence colour alike |
| `tram` | 12,500 | Hong Kong Tramways, 2020-10-27: "the tramcar alone weighs 12 to 13 tons" |
