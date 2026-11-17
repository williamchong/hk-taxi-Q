# music.tres

Rationale for `game/tuning/music.tres` (`Q119`).

The driving music (`P3-97`, `Q246`, the user's ask and the user's picks by ear): a quiet bed under
the drive that changes with the hour, and layers that come in as the style combo climbs. Read by
`scripts/audio/music_profile.gd`; played by `scripts/audio/drive_music.gd`, the `Music` node of
`city_drive.tscn`. The files are `tools/make_bgm.py`'s, thirteen loops of the same eight bars at
75 bpm, held in one `AudioStreamSynchronized` and only ever turned up and down. No `@export`
declares a default, so a key absent here is 0 and `usable()` refuses it.

## Level

- `bed_db` −12: the music's level into the `Music` bus with both sliders full. ⚠️ **Not yet set
  against a drive.** It was picked to sit under the engine (`engine_db` −18 on a file that peaks
  near full scale; the beds average −23 to −26 dBFS), and the audio rule's bar is a drive heard,
  so the first one moves this.
- `start_fade_s` 5 (the user's ask: "fade in the music when game start"): from silent to its
  level as the car first drives off, and again after every park. The level follows the travel
  squared, as the sliders do, so the fade is heard along its whole length: half way is 12 dB under.
- `park_fade_s` 1.5: parked, the music falls silent with the taxi's own loops (`Q185`), then
  pauses. The menu has no music.

## Hour

The beds follow the rig's cycle (`day_to_night.tres`: 0 is 07:00, 1 is 21:00, `loop_at` 1.714 the
next 07:00), so the music and the sky cannot disagree and a shift hears morning to night.

| Bed | `mood_from` | Hour | Side |
|---|---|---|---|
| `morning` | 1.607 | 05:30, with first light | day |
| `afternoon` | 0.286 | 11:00 | day |
| `night` | 0.821 | 18:30, between dusk and twilight | night |
| `midnight` | 1.214 | 00:00 | night |

- `mood_fade` 0.036: half an hour on the clock, 30 game seconds, for a bed to fade in over the one
  before. Equal power, so the level holds through it; each night chord shares three notes or more
  with the day chord in its slot (`make_bgm.py`), so the half hour around 18:30 and 05:30 is not
  a clash.
- `mood_side`: which chords a bed is in. The layers that play chords (`sided_stems`) have a file
  for each side and cross with the beds.
- `held_mood` `afternoon`: free mode's ALWAYS DAY and any rig that rests. The authored day is
  09:26, which is `morning`'s hour; the held hour takes the fuller bed instead, since it is the
  only one that run will ever hear.
- `mood_ease_s` 3: how fast a bed moves where the hour jumps (a run starting, a restart). The
  hour's own passing is `mood_fade`.

## Combo

`tiers` is a row of six for each count, ×1 first: `shaker`, `thump`, `bass`, `arp`, `top`, `clap`.

| Count | shaker | thump | bass | arp | top | clap | What comes in |
|---|---|---|---|---|---|---|---|
| ×1 | 0 | 0 | 0 | 0 | 0 | 0 | the bed alone |
| ×2 | 0.5 | 0 | 0 | 0 | 0 | 0 | the shaker |
| ×3 | 0.7 | 0.6 | 0 | 0 | 0 | 0 | a soft thump on the beat |
| ×4 | 0.8 | 0.7 | 0.6 | 0 | 0 | 0 | the root in quavers |
| ×5 | 0.9 | 0.8 | 0.7 | 0.6 | 0 | 0 | the quaver arpeggio |
| ×6 | 1 | 0.9 | 0.85 | 0.85 | 0 | 0.5 | a clap on two and four |
| ×7 | 1 | 1 | 1 | 1 | 0.6 | 0.7 | the semiquaver top line |
| ×8 | 1.2 | 1.15 | 1 | 1.1 | 1 | 1 | everything, lifted |

- The count is `StyleCombo.total()`; a count past ×8 keeps the last row. Every row adds a layer
  or lifts one and none drops one (`verify_music`), so a climbing combo is never heard to fall.
- ⚠️ The last row is mirrored by `make_bgm.py`'s `FULL`: the files share one scale, set so that
  row over the loudest bed peaks at 0.9. A louder row clips; `test_make_bgm.py` holds the mirror.
- `tier_rise_s` 1, `tier_fall_s` 2.5: a layer takes a second from silent to full, so a skill is
  answered within the bar it was done in (a bar is 3.2 s); when the combo ends the layers leave
  over 2.5 s, its own `combo_gap_s`, rather than cut.
- The combo is still never money and still has no one-shot (`fares.md`: built, heard, removed).
