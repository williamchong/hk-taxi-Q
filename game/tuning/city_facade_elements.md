# city_facade_elements.tres

Rationale for `game/tuning/city_facade_elements.tres` (`Q119`).

`Q26`'s candidate `A‴`: the clean look with its facade elements on. The runner-up to the shipped
`C` (`city_facade.tres`), kept because the HK-driver round at `P3-9a` can still reopen `Q26`.

Not loaded by anything. Restoring it is `cp city_facade_elements.tres city_facade.tres` and a
reimport, no rebuild: same shader, same `TEXCOORD_0` payload.

Six values separate it from `city_facade.tres`, and a `diff` should show only these:

    solid_share 0.27 · glass_ratio 0.44 · shopfront_share 0.55 · accent_share 0.11
    floor_line_darkness 0.11 · mullion_darkness 0.12

- It is the elements half of what the user accepted. The surveyed half (`survey_apply`, `quiet_*`)
  went with the vision reader (`Q102`); every building takes the hashed treatment.
- `cornice_darkness` 0.28 is shared with `C` (`Q195`): a cornice is drawn only on a building with
  an iB1000 podium line in `COLOR_0.a`, never at `podium_height_m`.
- Everything else, the `night_spot_*` floodlights included, is argued in `city_facade.md`.
  `city_facade_warm.tres` is the third look, `B`.
