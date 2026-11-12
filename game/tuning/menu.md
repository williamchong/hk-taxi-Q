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

The game's name, `menu_text.json`'s `title` (`Q208`): 香港的士車神 in the Kai, Hong Kong Taxi Ace
in the theme's face, two lines at 72 in the column. The rest are pairs, Chinese first like
`FareFace._say`, and the Kai sets larger than the Latin at every line but this one (`hud_style.md`,
`callout_*_zh`), so `button_size_zh` 32 against 28, `heading_size_zh` 28 against 24,
`body_size_zh` 24 against 20, `subtitle_size_zh` 30 against 26. The title is the exception:
`title_size_zh` 60 against 72, because at 72 the column wrapped 神 alone onto a second line
(HOME frame, `--lang=zh`, 2026-11-13).

## `backdrop_lod = 3.5`

The blur behind the menu's text (`Q163`, the user's ask: "background blur/shadowing in the menu so
that the texts are more readable"), `backdrop_blur.gdshader`. The frame is read from the screen's
mips at 3.5 — about an eleventh of the resolution, which turns the city's edges into soft fields
— and pulled toward `HudStyle.scrim`. HOME's columns (HOME, PLAY, OPTIONS, the report) take a side
panel `backdrop_width_px` 760 wide from the left edge, fading out from 0.55 of that width so the
car stays the picture; a sheet takes the whole screen.

## `ledger_px`

The 成績表 (`LedgerCard`, `P3-76`), beside REPORT's and PAUSE's column and inside RECORD's sheet. 1120 wide fills
what the 760 px column leaves on a 1920 canvas. 770 tall holds a full sheet with both optional lines, floor and
walked: 640 left the total hanging under the panel, which nothing but a frame shows. A row added to
`SessionTally.BONUSES` needs more height here.

## `ledger_row_px`

40 px a row carries the Kai at `body_size_zh` 24 with air, and is what a thumb can read on a phone in a paused car.
`ledger_rule_px` 2 is `frame_ink`'s ruled line: what makes the two tables a sheet rather than two lists.

## `ledger_count_px`

The two number columns. 64 holds a lifetime count of four digits, 104 a lifetime `+12345.6`, right-aligned so the
digits stand under each other. `ledger_gutter_px` 40 keeps the tables apart; `ledger_gap_px` 28 sets the books under them.

## `ledger_stacked_scale = 1.4`

On a touch screen (`Q206`, the user's pick of one scrolling column over two scrolling columns and tabs) the 成績表
stacks — bonuses, penalties, bests, sums — in one column the thumb scrolls, with the page's buttons pinned outside
the scroll. Side by side at the desk's 20 px it read about 10 pt on an iPhone Air (20 units × the touch table's
1.25 × 420 pt / 1080), RECORD's BACK fell under the screen's foot and REPORT's sheet covered the shift's total.
1.4 makes the body 28 units, ~14 pt there, and the Kai's 24 34; rows and the number columns scale with it so the
digits still stand in line. The desk keeps its two tables at 1.0.

`ledger_stacked_width_px` 1000 is RECORD's sheet on a phone: the 1.4× bonus table's four columns with air, centred
on a 20:9 handset's 1596-unit safe width. REPORT's and PAUSE's sheet is not a width but what is left right of the
page's column, so it never lands on the total again.

## `sheet_image_scale`

SAVE RESULT's picture of the 成績表 (`SheetImage`, `P3-80`, `Q188`): laid out at the sheet's own size on screen
(REPORT's 1120 × 770, `ledger_px`; RECORD's taller, its runs and best over the tables) and drawn 2.0 times over, so the type stays sharp when a phone or a chat app scales the picture down.
The text is drawn at the scale, never stretched from a 1× picture.

## The boot cover — `cover_*`, `warm_*`

The opaque cover `ShaderWarmup` holds over the menu's first seconds, so the web build compiles its
shaders where a wait is expected instead of in the menu and on the first frames of a drive. The
Compatibility renderer compiles a shader the first time something draws with it; measured cold on
the export (Chrome's Metal shader cache emptied), that was 733, 2124 and 595 ms frames in the
menu's first seconds and 312 and 462 ms as the drive started.

- `cover_wait_frames = 600`: the most it waits for the city's first settle (`CityRegions.built`)
  before warming anyway, so a city that never settles cannot hold the cover up.
- `cover_settle_frames = 30`: frames after the settle, for the traffic and the parked cells to
  stand.
- `cover_warm_frames = 2`: frames the copies stand. One is enough to draw; the second covers a
  frame the first one's compile ran over.
- `cover_fade_s = 0.4`: the cover's fade once the copies are gone. The menu takes input from the
  fade's first frame.
- `warm_distance_m = 3.0`, `warm_size_m = 0.08`: the copies' grid, that far in front of the camera,
  each shrunk to that size — 33 draws on the boot of 2026-11-05, so the grid is about 0.7 m across
  and inside the frame at the menu's 60° shots. A copy outside the frustum is culled and warms
  nothing.

The cover is `HudStyle.plate_field`, the housing, opaque. On it stands the loading screen
(`LoadingCover`, `Q209`): the toy taxi idling over the cab's meter, drawn from
`assets/authored/loading/taxi.json`, the same drawing the boot splash is a still of. Its meter
counts real steps — the most tiles the streamers owed at once, then each settle frame, then each
warm frame — so `cover_settle_frames` and `cover_warm_frames` are also how much of the meter the
last stretch takes.
