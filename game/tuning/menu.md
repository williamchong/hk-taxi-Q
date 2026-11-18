# menu.tres

Rationale for `game/tuning/menu.tres` (`Q119`).

The start menu (`P6-1`): the camera's shot per page (`Q164`), the column's geometry and the type
scale. Colours and panel shape are `hud_style.tres`'s (`Q139`); strings are `menu_text.json`'s.

Every key is required: `menu_profile.gd` declares no defaults, and `verify_menu.gd` refuses a zero
it would draw with. A `MenuShot` key absent from a sub-resource is 0 or false.

## Shots

A shot's `yaw_deg` is round the car from its chase position: 0 behind, 180 in front, negative
toward the kerbside. The car stands at `DriveLevel.showroom_fare_id` (set on the scene), not the
start line, which is under a podium; `resume` returns it.

- `shot_home`: the turntable. `turn_period_s` 40 reads as a showroom, not a spin. A metre longer
  than the chase camera and a tighter `fov_deg` 60: a portrait of one car.
- `shot_play`: the kerbside front three-quarter (`yaw_deg` −140), low and close, with `door_open`,
  the rear kerbside door. The user's ask: ready to go.
- `shot_options`: just off the tail (`yaw_deg` 10), close and low.
- `shot_sheet`: the guide, credits and notices cover the screen with a blurred sheet, so this is
  a backdrop: high over the street, the car small.
- `shot_report`: head on (`yaw_deg` 180).
- `sway_deg`, `sway_period_s`: each standing shot rocks a few degrees. A still menu stalls a
  `--menu=on` capture, and `verify_menu` refuses a shot that neither turns nor sways.
- `shot_response` 2.5: how fast the camera closes on a new page's shot, about 90% in a second.
  The opening page is cut to.

## Column and sheets

- `margin_px`: the column's inset from the safe area's bottom-left corner, clear of the car.
- `button_px` 420 × 72: a thumb-sized target. `button_gap_px` 14 keeps the column one control.
- `volume_step` 0.05 (`Q221`): a notch of the volume slider on OPTIONS' SOUND page; twenty from
  full to nothing. The level heard is the travel squared (`Settings.level_db`).
  `volume_track_px` 6 is the drawn line. OPTIONS is a list of groups, a page each (`Q223`); a
  group that outgrows its page splits, never scrolls.
- `credits_px`, `credits_pad_px`: the credits panel, centred, wide enough for the data credit's
  English at `body_size`.
- `guide_px`, `guide_picture_px`: the guide sheet, five steps abreast. The pictures are drawn
  (`guide_card.gd`); the bundle ships no UI textures.
- `backdrop_lod` 3.5, `backdrop_width_px` 760, `backdrop_fade_from` 0.55 (`Q163`): the blur behind
  the text (`backdrop_blur.gdshader`), read from the screen's mips and pulled toward
  `HudStyle.scrim`. A column takes a side panel fading out from 0.55 of its width; a sheet takes
  the whole screen. A row of three choices runs past the panel.

## Type

Pairs, the `_zh` size for Chinese. A Chinese face sets larger than the Latin at every line: the
brush is thin (`button_size_zh`, `heading_size_zh`), the 黑體 dense (`body_size_zh`,
`subtitle_size_zh`). Which line takes which face is `street_plate.json`'s `_faces` (`Q218`).

- `title_size`, `title_size_zh` 96 (`Q208`): the game's name on one line, which may run past the
  column but stays inside the backdrop and under the top bracket on a handset.

## The 成績表

`LedgerCard` (`P3-76`), beside REPORT's and PAUSE's column and inside RECORD's sheet.

- `ledger_px` 1120 × 840: what the 760 px column leaves on a 1920 canvas, and tall enough for a
  full sheet. Only a frame shows the total hanging under the panel; a row added to
  `SessionTally.BONUSES` needs more height.
- `ledger_row_px` 40, `ledger_rule_px` 2: a row, and the ruled line in `frame_ink`.
- `ledger_count_px` 64, `ledger_money_px` 104: the number columns, for a four-digit count and
  `+12345.6`, right-aligned. `ledger_gutter_px`, `ledger_gap_px`: between the tables, and above
  the books.
- `ledger_head_size*`, `ledger_title_size*`, `ledger_total_size*`, `ledger_total_row_px`: the
  sheet's ranks of type (`LedgerCard.Rank`): column head under the body, block title over it, the
  total about 1.8 rows.
- `ledger_stacked_scale` 1.4 (`Q206`, the user's pick): on a touch screen the sheet stacks into
  one scrolling column, the buttons pinned outside the scroll, every rank scaled. 1.4 makes the
  body about 14 pt on an iPhone. `ledger_stacked_width_px` 1000 is RECORD's sheet on a phone.
- `sheet_image_scale` 2.0 (`P3-80`, `Q188`): SAVE RESULT's picture is drawn at twice the sheet's
  size, text at the scale, never stretched.

## The pause

- `pause_fps` 30 (`Q165`): the most frames a second the pause draws. The tree is held but the city
  is still drawn behind the menu, and the screen never sleeps (`keep_screen_on` is the engine's
  default), so a phone left on PAUSE would draw at the drive's rate for as long as it lay there.
  30 is a whole number of a 60 Hz panel's refreshes and keeps a tap's answer prompt; 15 lags.
  Never above the cap in force, and 0 holds nothing. Not low-processor mode: the water and the
  blinkers read `TIME`. The saving is not measured on a handset.

## The saved run

- `autosave_s` 30 (`Q253`): game seconds between saves of the run in play. The pause, the app
  losing the screen, the window closing and every fare's boarding, delivery and walk-off save it
  too, so this only bounds what a kill with no notice loses: a crash, or the system reclaiming a
  foreground app. Half a minute of driving is the most the player can lose; one save is a small
  `ConfigFile` write (`RunSave`), so a shorter step costs little but buys nothing a player feels.
  0 is refused as a zero dial.

## The boot cover

`ShaderWarmup` holds an opaque cover over the menu's first seconds so the web build compiles its
shaders there (`Q184`); cold, they cost frames of 0.3–2 s in the menu and at the drive's start.
The cover is the loading screen (`LoadingCover`, `Q209`), whose meter counts real steps.

- `cover_wait_frames` 600: the most it waits for the city's first settle (`CityRegions.built`).
- `cover_settle_frames` 30: frames after the settle, for the traffic and parked cells to stand.
- `cover_warm_frames` 2: frames the warm-up copies stand.
- `cover_fade_s` 0.4: the fade. The menu takes input from its first frame.
- `warm_distance_m` 3.0, `warm_size_m` 0.08: the copies' grid in front of the camera. A copy
  outside the frustum is culled and warms nothing.
