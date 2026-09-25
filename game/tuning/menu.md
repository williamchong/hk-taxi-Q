# menu.tres

Rationale for `game/tuning/menu.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The start menu (`P6-1`, the user's ask of 2026-09-26): start, options, credits, over the taxi
standing on the start line with the camera circling it. Two things live here — the hero orbit and
the column's geometry and type scale — and two deliberately do not: the colours and the panel shape
are `hud_style.tres`'s, so the menu is the cab's one housing (`Q139`) and a second car's theme
re-skins both, and the strings are `menu_text.json`'s, because a legal text wants a diffable file.

⚠️ EVERY KEY BELOW IS REQUIRED. `menu_profile.gd` declares no defaults, so a missing key reads
zero, and `verify_menu.gd` refuses a zero it would draw with.

## `orbit_distance_m = 7.5`

The spring arm while the menu is up, a metre longer than the chase's 6.5 so the whole car sits in
frame with road either side; `orbit_height_m` 1.6 puts the pivot at the roof sign, and
`orbit_pitch_deg` −12 looks down onto the bonnet rather than along it. The chase rig's own numbers
return on start (`DriveHarness.resume`).

## `orbit_period_s = 40.0`

One circle in forty seconds: slow enough to read as a showroom turntable, not a spin, and the
motion is what keeps the frame changing so a `--menu=on` capture never stalls on a static frame
(`SKILL.md`, "no frame drawn"). `orbit_start_deg` 35 opens on the front three-quarter — the
kerbside headlamp, the roof sign and the door the passenger uses.

## `orbit_fov_deg = 60.0`

Tighter than the chase's 70: a portrait of one car, not a view of the road ahead.

The car stands at `DriveHarness.showroom_fare_id` — `f_001`, the Harbour Road cross-harbour
stand, HKCEC's old wing behind it under open sky — not on the start line, which is under the
Phase II podium where every orbit angle looks at a soffit (measured 2026-09-26; `f_003` faces a
wall and `f_028` buries the arm in the pavement). `resume` returns the car to the start line.

## `margin_px = Vector2(96, 72)`

The column's inset from the safe area's bottom-left corner. Bottom-left keeps the car — which
the orbit frames about the centre — clear of the text, and it is the corner the racing genre puts
its menu in. `button_px` 420 × 72 is a thumb-sized target with room for 鳴謝及授權 at the Kai's
32 px; `button_gap_px` 14 is under a button's quarter so the column reads as one control.

## `credits_px = Vector2(1100, 760)`

The credits panel, centred: wide enough for the data credit's English to run six lines at 20 px
rather than a column of fragments, short enough to leave a strip of city above and below it.
`credits_pad_px` 28 keeps the text off the keyline.

## `guide_px = Vector2(1500, 560)`

The guide sheet: five steps abreast at `guide_picture_px` 240 × 150 each, with a caption of three
or four lines under, and the same pad and keyline as the credits. The pictures are drawn
(`guide_card.gd`) — the bundle ships no UI textures, and a screenshot of the city would be the
generated data committed in another form.

## `title_size = 72`

The project's name, in the theme's own face whatever the language. The rest are pairs, Chinese
first like `FareFace._say`: the Kai sets larger than the Latin at every line (`hud_style.md`,
`callout_*_zh`), so `button_size_zh` 32 against 28, `heading_size_zh` 28 against 24,
`body_size_zh` 24 against 20, `subtitle_size_zh` 30 against 26.
