# parked.tres

Rationale for `game/tuning/parked.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

How the parked roster (`P3-73`, `Q161`) is read against the clock and cut into cells. What a
placement IS — its kind, its hours, its chance — is the ETL's (`parked_placements.json`); this
table says only which hour the rig's `time_of_day` means and how the layer rebuilds out of view.
Every key is required: `parked_profile.gd` declares no defaults, and `ParkedLayer` refuses a zero
cell or an empty day rather than stand on a literal.

## `clock_start_h = 7.0`

`time_of_day` 0 is 07:00, 特更's opening hour (`shift.tres`, `Q162`, 2026-10-11): the roster reads
the same clock the player reads on the HUD, so a van that leaves at 19:00 leaves when the dash
says 19:00. 🔴 **This pair must equal `shift.tres`'s `opens_h` / `closes_h`** —
`verify_day_cycle` holds it. The cycle holds the authored day until 0.71 and reaches dusk at 0.79,
twilight at 0.86 and night at 0.93: 17:00, 18:00, 19:00 and 20:00, a Hong Kong October evening.
Was 12.0 against the 240 s cycle that opened at noon.

## `clock_end_h = 21.0`

`time_of_day` 1 is 21:00, 交更, where the cycle's night holds — in free mode too, whose day runs
the same table when its option is DAY TO NIGHT. The vans' 8-19 window closes inside the day and
the single-yellow fill (19-7) opens at twilight, which is what makes the night street carry more
cars than the day. The metered bays' 8am-to-midnight window opens an hour in, so the first game hour
of a shift (about 21 s) stands no metered car — the window as published.

## `cell_m = 300.0`

`prop_cells.tres`'s cell: the lamps' unit, measured there (`P3-67`). One `MultiMesh` a kind a
cell, about nine kinds, so Wan Chai's 863 vehicles are some forty draws resident.

## `range_margin_m = 15.0`

How far past the camera's `far` (400 m, `city_drive.tscn`) a cell's NEAREST EDGE must be before
the cell is rebuilt: a vehicle appearing or leaving inside the camera's reach is a pop, and the
street in view never changes under the player. 15 m covers a bus's half length (6 m) over the
edge of the cell its origin is in, with room. ⚠️ **No `range_m` and no `visibility_range_end`
any more** (`Q214`): the engine measured that range to the centre of a cell's `MultiMesh` — the
centre of a 300 m box — so a whole cell's cars appeared at once about 190 m ahead. The camera's
own `far` clips a vehicle where it stands, and nothing else hides one.

## `poll_s = 1.0`

How often the layer asks the rig's clock and walks the cells. A placement's windows are whole
hours and an hour is about 21 s of the 300 s day, so once a second is twenty chances to catch it.

## `reroll_s = 90.0`

A hidden cell holding a placement with a chance under 1 — a bus at a stop a third of the time —
is drawn again this long after it was built. Longer than a lap of the region at the pace the
fare loop drives, so the same bus is there when the player comes straight back and may be gone
the next time round.

## `liveries`

What each kind's livery panels wear (`Q167`, the user's ask 2026-10-13: "some variation of colors
instead of all same color, unless color means sth"). Keyed by library mesh, one colour drawn per
placement on `ParkedRoster.LIVERY_ROLL`, so a colour listed twice is twice as common and a vehicle
keeps its colour on every visit. sRGB, painted by `vehicle_body.gdshader` over the vertices
`make_parked.py` stamps `MARKER_LIVERY` (each `Shape`'s `livery`).

- **Where the colour means something, it is not listed.** The taxi stays red (the urban taxi's
  colour is its licence; green and blue taxis cannot ply Wan Chai), the bus stays Citybus yellow
  over blue, the tram stays green.
- **`minibus`: the roof only, green 2 : red 1.** The colour is the licence there too, and there
  are exactly two: green is a scheduled route, red a free-running one. Island streets carry more
  green.
- **`car_a`, `car_b`, `van`: mostly neutrals, as the street is.** White, silver, black and grey
  carry 11 of the saloon's 16 draws, with one each of navy, maroon, champagne, dark green and a
  mid blue; the MPV is white and black (an Alphard) with a champagne and a grey; the Hiace almost
  all white, with a grey and a navy for the trade's own. The last two of each came with `P3-85`. 🔴 Kept off saturated red on purpose: the
  player's red taxi is meant to be the one chromatic car in the frame (`ART_DESIGN.md`), and
  `maroon` is dark enough not to compete.
- **`lorry`: cab and box together, white 4 of 7** with a blue, a dark green and a yellow — a
  trade's own colours on a plain box lorry (`P3-85`). Authored: nothing publishes a fleet's paint.
- **`coach`: the belt band** — navy 2, red, green, orange; a tour coach's body stays white.
- **`motorcycle`: tank, fairing and fender** — red and black 2 each, white, blue.

## `hazard_sources = ["layby", "frontage"]`

Which published sources stand with their hazards on (`P3-3f`, the user's drive 2026-10-29: parked
cars split into the switched-off and the stopping). Both indicators flash at the taxi's own beat
(`vehicle_lamps.tres`); the head lamps and tails stay dark.

- **`layby`**: a lay-by is a place to stop, not to park — a car setting down, a taxi waiting for
  a fare, a van loading. In Hong Kong a vehicle there sits on its hazards.
- **`frontage`**: the vans and coaches a building's name puts at its kerb (a goods entrance, a
  hotel's coach) are loading.
- **Not `stop` or `stand`**: a bus at its stop and a taxi on a rank wait with their hazards off;
  the stop and the rank are what licence them to stand.
- **Not `bay` or `fill`**: a metered or invented kerb car is parked, switched off.

## `masses_kg` — each moving kind's kerb mass (`Q180`)

What a car or a tram gives when the taxi pushes it, against the taxi's own 1,400 kg
(`cars/crown_comfort.tres`). **Kerb, not loaded** (the user's call, 2026-11-04): the one figure
every maker and the tram's operator publish, empty, so all five sit on one footing. Only the kinds
something moves are listed; a parked vehicle stands as a wall in this version (`Q180`), so the bus,
the coach and the motorcycle carry none, and a kind not listed is a wall. The taxi moves since
`Q183`, and every licence's taxi carries the one mass: they are one car. The bus moves since
`P3-78` (`Q182`), on its routes.

| Kind | kg | Read off |
|---|---|---|
| `bus`, the 12 m three-axle double-decker | 15,000 | Alexander Dennis Enviro500 MMC, 15,300 kg unladen (ADL's Mexico sheet; the Hong Kong sheet publishes no weight) |
| `car_a`, the 4.5 m saloon | 1,600 | Toyota Camry 2.5 Hybrid, 1,570–1,670 kg by generation and standard (autotijd.be, cars-data.com) |
| `car_b`, the Alphard | 2,100 | Alphard IV, 2,060 kg (2.5 petrol) to 2,290 kg (hybrid E-Four) (auto-data.net) |
| `van`, the Hiace | 2,200 | Hiace H300 long-wheelbase van, 2,175–2,225 kg (carsales.com.au) |
| `minibus`, the Coaster | 3,500 | export Coasters 3,100–3,450 kg (UNICEF supply listing, Toyota GIB); no figure for the Hong Kong LPG light bus, bounded by TD's gross cap of 5.5 t until July 2020 — 19 aboard leaves under about 4.2 t |
| `taxi`, the Crown Comfort (red, green and blue alike, `Q183`) | 1,400 | the player's own car, `cars/crown_comfort.md`: about 1,390 kg kerb (`Q153`); the AI taxi is the same model |
| `tram` | 12,500 | Hong Kong Tramways' own post, 2020-10-27: "the tramcar alone weighs 12 to 13 tons; when it is full of passengers, there might be an extra 5 tons". A fan page's 27.0 t is not used |

⚠️ What a mass changes is the share: a pushed body takes `m_taxi / (m_taxi + m)` of the change
in speed, so a few hundred kilograms either way barely moves a hit. The tram, on its rails alone,
takes about a tenth.
