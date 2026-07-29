#!/usr/bin/env bash
# Export the game.
#
#   tools/export.sh              # macos + web
#   tools/export.sh macos|web|android|ios
#
# Output paths come from export_path in game/export_presets.cfg — do not repeat
# them here. Godot will not create the target directory itself, hence the mkdir.
# Signing credentials never live in export_presets.cfg; they come from Godot
# editor settings or the environment. See P0-3b.

set -euo pipefail

GODOT="${GODOT:-/Applications/Godot.app/Contents/MacOS/Godot}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export_preset() {
	echo "==> $1"
	"$GODOT" --headless --path "$ROOT/game" --export-release "$1"
}

mkdir -p "$ROOT"/build/{macos,web,android,ios}

case "${1:-default}" in
	macos)   export_preset "macOS" ;;
	web)     export_preset "Web Demo" ;;
	android) export_preset "Android" ;;
	ios)     export_preset "iOS" ;;
	default)
		export_preset "macOS"
		export_preset "Web Demo"
		;;
	*)
		echo "unknown target: $1 (macos|web|android|ios)" >&2
		exit 1
		;;
esac
