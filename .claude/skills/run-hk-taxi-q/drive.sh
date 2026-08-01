#!/usr/bin/env bash
# Launch a scene, drive it with scripted input, and screenshot it.
#
#   .claude/skills/run-hk-taxi-q/drive.sh [driver args...]
#
# Everything after the script name is passed to driver.gd. With no arguments it
# drives city_drive.tscn for 6 s under full throttle and writes three frames.
#
#   --scene=res://scenes/dev/city_preview.tscn
#   --seconds=8
#   --shots=0.5,4,8                  sim times (s) to capture
#   --out=dir                        default build/driver/, relative to the repo
#   --camera=x,y,z --look=x,y,z      place the camera (preview scenes only)
#   --hold=accelerate@0.5+5.0        press an action at 0.5 s, hold for 5 s
#                                    (repeatable; actions are the [input] names
#                                    in project.godot — steer_left, steer_right,
#                                    accelerate, brake_reverse, drift, look_back)
#   --debug-view=off|minimal|full    debug overlay; defaults to minimal here
#
# Exists for the same reason tools/check.sh does: Godot exits 0 when a script
# fails to parse, so quit(1) in the driver never runs and a broken driver
# reports success. The exit code below comes from reading the output, not from
# trusting the engine. tools/check.sh is the source of truth for that pattern
# and for the FATAL list — if a new exits-zero failure string turns up there,
# it belongs here too.
#
# Override GODOT= if yours is not on PATH. Needs a real window — a --headless
# run has no rasteriser, and the driver refuses to screenshot without one.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
GODOT="${GODOT:-godot}"
DRIVER="$ROOT/.claude/skills/run-hk-taxi-q/driver.gd"

if ! command -v "$GODOT" >/dev/null 2>&1; then
	echo "godot not found as '$GODOT' — install it, or set GODOT=/path/to/godot" >&2
	exit 1
fi

if [[ $# -eq 0 ]]; then
	set -- --seconds=6 --shots=0.5,3,6 --hold=accelerate@0.5+5.5
fi

# The debug overlay is off by default in the game and on by default here, and
# the two are not in conflict: a person launching the game is playing it, while
# everything that comes through this script is a scripted run someone is reading
# afterwards. A screenshot that does not say where it was taken cannot be acted
# on — the frame shows a wall, and the position block is what makes it a
# *located* wall.
#
# `minimal` and not `full`: two lines in the top left and +8 draw calls measured,
# against +19 and a five-line text block over the city for `full`. Pass your own
# --debug-view= to override — `off` for a frame judged on how it looks, `full`
# for the road graph's chevrons and readout.
case " $* " in
*" --debug-view="*) ;;
*) set -- "$@" --debug-view=minimal ;;
esac

# Godot reports a failure with any of these and still exits 0.
FATAL='Parse Error|SCRIPT ERROR|Failed to load script|Failed to compile'

# Streamed through tee rather than captured into a variable, so the per-second
# telemetry arrives while the run is happening. A captured run shows nothing
# until the process exits, which makes a hang — the failure this and the
# driver's capture timeout are both built against — look identical to a slow
# start: no output at all, and no clue which.
LOG="$(mktemp -t hk-taxi-drive)"
trap 'rm -f "$LOG"' EXIT

"$GODOT" --path "$ROOT/game" --script "$DRIVER" -- "$@" 2>&1 | tee "$LOG"
status=${PIPESTATUS[0]}

if grep -qE "$FATAL" "$LOG"; then
	echo >&2
	echo "FAILED — a script error, and Godot still exited 0." >&2
	exit 1
fi
if ((status != 0)); then
	echo >&2
	echo "FAILED — driver exited $status." >&2
	exit "$status"
fi
if ! grep -q 'DRIVER OK' "$LOG"; then
	echo >&2
	echo "FAILED — the driver never reported DRIVER OK; it died before finishing." >&2
	exit 1
fi
