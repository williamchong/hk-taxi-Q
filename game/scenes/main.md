# main.tscn

The boot scene: `Main` is the entry point, `World` holds the level, `GUI` holds what is drawn over
it, so a level change swaps `World`'s children without touching the HUD.

- `Main` (`main.gd`, `P5-24`): hands the HUD its car. `level`, `hud` and `menu` are typed exports
  pointing down; nothing under `GUI` searches for a car. `level` and `hud` are null-checked with a
  warning. `menu` is checked with `wanted()` and `is_instance_valid`, because under `--menu=off`
  it frees itself in `_ready`.
- `World/CityDrive`: the one level, `city_drive.tscn`.
- `GUI`: after `World`, and the order is load-bearing: a sibling's subtree is readied and
  processed first, so everything under `GUI` finds the car placed and its `speed_kph` written.
- `GUI/Hud` (`hud.gd`, `P3-24`): layer 10, under `DebugHud` (127). `--hud=off` frees it, for
  `P3-9`'s drive without navigation aids and for clean art frames.
- `GUI/StartMenu` (`start_menu.gd`, `P6-1`, `Q146`): layer 20, over the HUD. `Main` parks the
  level while it is up (`DriveLevel.park`) and resumes on `started`; a language pick retires the
  HUD and readies a fresh one. `--menu=off` frees it, and `drive.sh` passes that for every
  scripted run. Numbers in `tuning/menu.tres`, strings in `tuning/menu_text.json`.
