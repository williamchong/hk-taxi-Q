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

# Templates are installed per Godot version, and a point upgrade leaves the new
# version with none. The export then fails under a screen of adb noise, and a
# stale build/web/index.pck reads like a measurement. Named here, before any
# export runs. ~/.local/share is where Linux keeps them.
# `4.7.2.stable.official.ed1daf0bf` -> `4.7.2.stable`, `4.8.rc1.official.x` -> `4.8.rc1`.
version="$("$GODOT" --version | sed -E 's/^([0-9]+\.[0-9]+(\.[0-9]+)?\.[a-z]+[0-9]*)\..*/\1/')"
templates=""
for dir in "$HOME/Library/Application Support/Godot/export_templates" \
	"${XDG_DATA_HOME:-$HOME/.local/share}/godot/export_templates"; do
	if [[ -d "$dir/$version" ]]; then
		templates="$dir/$version"
		break
	fi
done
if [[ -z "$templates" ]]; then
	echo "no export templates for Godot $version. Unzip that release's" >&2
	echo "export_templates.tpz (templates/*) into export_templates/$version/ under" >&2
	echo "~/Library/Application Support/Godot/ (macOS) or ~/.local/share/godot/ (Linux)." >&2
	exit 1
fi

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
