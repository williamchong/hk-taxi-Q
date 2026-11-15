#!/usr/bin/env bash
# Take the App Store screenshots from the game itself.
#
#   tools/store_screenshots.sh [--compose]
#
# Six scenes in each language the game speaks, at the two sizes App Store
# Connect asks for, into fastlane/screenshots/<locale>/ — which `fastlane
# metadata` uploads. They are renders of the generated city, so they are build
# output and gitignored like it.
#
# Each scene shows one thing the game does and says so above the frame:
# tools/caption_screenshot.py sets the scene's line from
# fastlane/screenshot_captions.json in the menu's own faces. `--compose` sets
# the captions again over the frames the last run kept in build/store/raw/,
# for a change of wording: no window, nothing captured.
#
# A phone frame is drawn at 2868x1320 with the touch controls and a handset's
# insets. A 2732x2048 window does not fit this screen, so the iPad frame is
# drawn at 2048x1536 and scaled up.
#
# Needs a window, and the machine left alone while it runs: the game takes the
# focus for every scene. A scene whose capture stalls is tried three times.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
DRIVE="$ROOT/.claude/skills/run-hk-taxi-q/drive.sh"
RAW="$ROOT/build/store/raw"
SHOTS="$ROOT/fastlane/screenshots"

# name | the frame's time | the run
SCENES=(
	"1_hennessy|5|--spawn-fare=wan_chai/f_016 --seconds=6 --hold=accelerate@0.5+5.5"
	"2_drift|4.2|--seconds=6 --hold=accelerate@0.3+5.7 --hold=steer_right@3.0+1.5 --hold=handbrake@3.0+1.5"
	"3_shift|3|--mode=shift --spawn-fare=wan_chai/f_018 --seconds=6 --hold=accelerate@0.5+5.5"
	"4_harbour|5|--seconds=6 --hold=accelerate@0.5+5.5"
	"5_night|3|--time-of-day=0.95 --spawn-fare=wan_chai/f_017 --seconds=6 --hold=accelerate@0.5+5.5"
	"6_menu|2|--menu=on --seconds=3"
)
# locale | the game's language
LOCALES=("en-US|en" "zh-Hant|zh")
# device | window | insets | uploaded size
DEVICES=(
	"iphone|2868x1320|214,0,214,63|2868x1320"
	"ipad|2048x1536|0,0,0,0|2732x2048"
)

COMPOSE=0
case "$*" in
"") rm -rf "$RAW" ;;
--compose) COMPOSE=1 ;;
*)
	echo "usage: tools/store_screenshots.sh [--compose]" >&2
	exit 2
	;;
esac
rm -rf "$SHOTS"
for locale in "${LOCALES[@]}"; do
	IFS='|' read -r store_locale lang <<<"$locale"
	mkdir -p "$SHOTS/$store_locale"
	for device in "${DEVICES[@]}"; do
		IFS='|' read -r device_name window insets size <<<"$device"
		for scene in "${SCENES[@]}"; do
			IFS='|' read -r name at run <<<"$scene"
			out="$RAW/$store_locale/$device_name/$name"
			# drive.sh names a frame by its time.
			frame="$out/$(printf 't%05.2f' "$at").png"
			mkdir -p "$out"
			read -r -a run_args <<<"$run"
			captured=0
			if [[ "$COMPOSE" -eq 1 ]]; then
				[[ -f "$frame" ]] && captured=1
			else
				for _ in 1 2 3; do
					if "$DRIVE" "${run_args[@]}" --shots="$at" --lang="$lang" --window="$window" \
						--safe-area="$insets" --touch=on --debug-view=off --fare-seed=7 \
						--out="$out" >"$out.log" 2>&1; then
						captured=1
						break
					fi
				done
			fi
			if [[ "$captured" -eq 0 ]]; then
				echo "$store_locale $device_name $name has no frame; see $out.log" >&2
				exit 1
			fi
			"$PYTHON" "$ROOT/tools/caption_screenshot.py" "$frame" \
				"$SHOTS/$store_locale/${device_name}_$name.jpg" \
				--size "$size" --scene "$name" --lang "$lang"
			echo "$store_locale/${device_name}_$name.jpg"
		done
	done
done
