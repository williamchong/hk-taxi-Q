# car_outline.tres

Rationale for `game/tuning/car_outline.tres` (`Q119`).

The outline's answer to the car (`P3-65`, `Q158`): the city's line thins and fades with speed. Read
by `CarOutline` on `taxi_tyre.tscn`. What the line does with the speed is `cel_outline.tres`'s
`speed_thin_px` and `speed_fade`; the drift's light tail is `light_tail.tres`.

- `full_speed_kph` 120: where the `outline_speed` global reaches 1 and the line is thinnest and
  faintest. It holds above. Required: the script declares no default.
