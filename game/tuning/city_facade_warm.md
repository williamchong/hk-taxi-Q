# city_facade_warm.tres

Rationale for `game/tuning/city_facade_warm.tres` (`Q119`).

`Q26`'s candidate `B`: `P3-7`'s measured Hong Kong window bands, at the pitch read off real facade
textures (one LandsD sheet, read offline, never shipped; `docs/DATA_SOURCES.md`).

Not loaded by anything. Switching is `cp city_facade_warm.tres city_facade.tres` and a reimport, no
rebuild: `city_facade.gdshader` reads the same `TEXCOORD_0` payload.

It is a record of what `P3-7` measured, on the older shader. `city_facade_clean.gdshader` was
forked from it and fixed in three places never back-ported, so this look reintroduces:

- `band()` without the analytic duty-cycle convergence: diagonal moire on walls at a shallow angle.
- `along_m` from the face normal's plan-perpendicular: per-triangle grid origins, so a curved
  podium breaks into chevrons.
- A 90–240 m fade (`fade_start_m`, `fade_end_m`), safe against the 250 m LOD1 switch by accident.

Port the three before shipping it. It has no `night_spot_*`; `lit_window_share` and
`emission_strength` are 0.0.
