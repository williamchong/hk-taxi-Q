# menu.tres

Rationale for `game/tuning/menu.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The start menu (`P6-1`, the user's ask of 2026-09-26): start, options, credits, over the taxi
standing on the start line with the camera placed by the page (`Q164`). Two things live here — the camera's shot per page and
the column's geometry and type scale — and two deliberately do not: the colours and the panel shape
are `hud_style.tres`'s, so the menu is the cab's one housing (`Q139`) and a second car's theme
re-skins both, and the strings are `menu_text.json`'s, because a legal text wants a diffable file.

⚠️ EVERY KEY BELOW IS REQUIRED. `menu_profile.gd` declares no defaults, so a missing key reads
zero, and `verify_menu.gd` refuses a zero it would draw with.

## `shot_home`

HOME's shot, the turntable (`turn_period_s` 40): a circle in forty seconds reads as a showroom
turntable, not a spin. `distance_m` 7.5 is a metre longer than the chase's 6.5 so the whole car sits
in frame with road either side; `height_m` 1.6 puts the pivot at the roof sign and `pitch_deg` −12
looks down onto the bonnet. `yaw_deg` 35 is where the circle starts on a cut; coming back from
another page it turns on from wherever the camera stands. `fov_deg` 60 is tighter than the chase's
70: a portrait of one car.

Every shot's `yaw_deg` is round the car from its chase position — 0 behind it, 180 in front, and
negative toward its left, the kerbside.

## `shot_play`

PLAY (`Q164`, the user's ask: "the side-front angle of taxi (as in ready to go)"): the kerbside
front three-quarter, `yaw_deg` −140, low (`height_m` 1.0, `pitch_deg` −6) and close (6 m) so the
car looks ready to pull away, with `door_open` — the rear kerbside door, the one the driver's lever
swings for the fare (the user's second ask). −120 shows the leaf less edge-on but loses the front.

## `shot_options`

OPTIONS (`Q164`: "goes to back of taxi (as in settings)"): just off the tail, `yaw_deg` 10, close
and low — the boot and the plate, the car's back to the street.

## `shot_sheet`

The guide, credits and notices cover the screen with a blurred sheet, so this is a backdrop of
colour more than a picture: high over the street (`distance_m` 24, `pitch_deg` −35), the car small
on its road.

## `shot_report`

The shift's REPORT: head on (`yaw_deg` 180), the headlamps lit toward the player at the handover.

## `sway_deg` / `sway_period_s`

Each standing shot rocks a few degrees either side of its yaw over 12–30 s: enough that the frame
is never still — a still menu stalls a `--menu=on` capture on "no frame drawn" (`SKILL.md`) — and
slow enough to read as a held shot. `verify_menu` refuses a shot that neither turns nor sways.

## `shot_response = 2.5`

How fast the camera closes on a new page's shot, per second, on the chase rig's first-order filter:
about 90% of the way in a second, so a click reads as a camera move, not a cut, and a page changed
mid-move just bends toward the next. The page the menu opens on is cut to.

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

## `backdrop_lod = 3.5`

The blur behind the menu's text (`Q163`, the user's ask: "background blur/shadowing in the menu so
that the texts are more readable"), `backdrop_blur.gdshader`. The frame is read from the screen's
mips at 3.5 — about an eleventh of the resolution, which turns the city's edges into soft fields
— and pulled toward `HudStyle.scrim`. HOME's columns (HOME, PLAY, OPTIONS, the report) take a side
panel `backdrop_width_px` 760 wide from the left edge, fading out from 0.55 of that width so the
car stays the picture; a sheet takes the whole screen.
