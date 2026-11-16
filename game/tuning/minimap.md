# minimap.tres

Rationale for `game/tuning/minimap.tres` (`Q119`).

The minimap's scale and orientation (`P3-44`, `Q136`). Colours are `hud_style.tres`'s `map_*`; the
slot is `hud_layout.tres`'s `minimap`.

Every key is required: `minimap_profile.gd` declares no defaults, and `verify_hud.gd` refuses a
zero by name (`arrow_px` and `route_px` may be 0). `min_stroke_px`, `casing_px`, `route_px` and the
arrows are baked into the mesh at build as metres at the slot's scale, so a change to them, to
`span_m` or to the slot's width shows on the next launch.

- `span_m` 320: metres of city across the slot; 0.875 px to the metre at 280 px, so a 10 m
  carriageway is 8.75 px. `fares.tres`'s `place_m` and `retire_m` are sized off it.
- `heading_up` true (the user's call): the nose is up and the map turns, like a GPS.
- `anchor` `(0.5, 0.66)`: the car sits two thirds down, so more of the slot is road ahead. Under
  north-up the honest value is `(0.5, 0.5)`.
- `min_stroke_px` 2.0: an alley under 2 px flickers out as the map turns. A floor, never a
  multiplier (`Q95`).
- `casing_px`: the field-coloured casing that separates a deck from the street beneath.
- `arrow_px` 0.0: the one-way arrows, off (the user's call). At a readable size they are wider
  than most streets; the route does their job. The mesh code and its `verify_hud` assertions
  stay, so the dial turns them back on. `arrow_spacing_px` 56 is their spacing, about 64 m.
- `marker_px`: the car's chevron.
- `route_px` 5.0 (`P3-46`): the legal route to the destination in `map_route`, over the roads and
  under the pins. Over the stroke floor and under a carriageway's width, so it reads as a line on
  the road. 0 draws none; `P3-9` runs so.
