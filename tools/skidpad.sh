#!/usr/bin/env bash
# Grade the handling model on the skidpad and print the table.
#
#   tools/skidpad.sh [ablation args...]
#
# Everything after the script name is passed to skidpad_ablation.gd:
#
#   --only=drift                     one manoeuvre instead of all five
#                                    (corner, drift, tap, brake, coast)
#   --sweep=FIELD=0.4,0.6,0.8        sweep any HandlingProfile float. A drift_*
#                                    field re-runs only drift and tap, since the
#                                    rest cannot move; anything else re-runs all
#                                    five. One sweep per run — a second is
#                                    refused, not merged
#   --drift-grip=0.38,0.40,0.42      alias for --sweep=drift_rear_grip_scale=...
#   --scene=res://scenes/dev/...      grade a different car on the same ground
#
# Run it before AND after any change to VehicleController's drive model,
# HandlingProfile or handling.tres, and paste both tables (CLAUDE.md).
#
# Sweep with --sweep rather than by editing handling.tres in a shell loop: one
# such loop blanked the field it was sweeping and published a table of all-zero
# rows that read like a finding (Q86).
#
# Exists for the same reason drive.sh and tools/check.sh do: Godot exits 0 when a
# script fails to parse, so quit(1) never runs and a broken tool reports success.
# The ablation's own `_printed_rows` guard cannot cover that case — on a parse
# error _finish never runs at all. The exit code below comes from reading the
# output. tools/check.sh is the source of truth for the FATAL list; if a new
# exits-zero failure string turns up there, it belongs here too.
#
# Headless on purpose: nothing is captured, and the dummy rasteriser is faster
# and works over SSH. Override GODOT= if yours is not on PATH.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GODOT="${GODOT:-godot}"
TOOL="$ROOT/tools/skidpad_ablation.gd"

if ! command -v "$GODOT" >/dev/null 2>&1; then
	echo "godot not found as '$GODOT' — install it, or set GODOT=/path/to/godot" >&2
	exit 1
fi

FATAL='Parse Error|SCRIPT ERROR|Failed to load script|Failed to compile'

LOG="$(mktemp -t hk-taxi-skidpad)"
trap 'rm -f "$LOG"' EXIT

# ⚠️ The car's own scripts spray SCRIPT ERROR under --script — vehicle_lamps.gd
# resolves its controller by class, which is exactly the lookup that cannot work
# here — so the FATAL grep would fire on every healthy run. Filtered to lines the
# ablation itself is responsible for: anything naming the tool, and the
# parse/compile failures, which name a file either way. (wheel_visual.gd was the
# other one until Q50 deleted it: a VehicleWheel3D moves its own mesh.)
"$GODOT" --headless --path "$ROOT/game" --script "$TOOL" -- "$@" 2>&1 | tee "$LOG"
status=${PIPESTATUS[0]}

if grep -E "$FATAL" "$LOG" | grep -qv 'vehicle_lamps.gd'; then
	echo >&2
	echo "FAILED — a script error, and Godot still exited 0." >&2
	exit 1
fi
if ((status != 0)); then
	echo >&2
	echo "FAILED — the ablation exited $status." >&2
	exit "$status"
fi
if ! grep -q 'ABLATION OK' "$LOG"; then
	echo >&2
	echo "FAILED — no ABLATION OK; it died before finishing." >&2
	exit 1
fi
