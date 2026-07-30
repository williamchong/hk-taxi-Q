#!/usr/bin/env bash
# Copy a built region from the ETL into the Godot project.
#
#   tools/sync_generated.sh                      # hong_kong / wan_chai
#   tools/sync_generated.sh <city> <region>
#
# Copies exactly the files city.json names, asked of the ETL rather than
# guessed at (`export.py --list`). That is the point: two stage intermediates,
# buildings.json and roadsurface.json, sit in the same output directory and must
# never reach the bundle. A directory copy would ship them; this cannot.
#
# game/assets/generated/ is gitignored build output. Nothing here is committed,
# and a fresh clone has an empty directory until this runs.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"

CITY="${1:-hong_kong}"
REGION="${2:-wan_chai}"

SRC="$ROOT/etl/out/$CITY/$REGION"
DST="$ROOT/game/assets/generated"

if [[ ! -f "$SRC/city.json" ]]; then
	echo "No manifest at $SRC/city.json. Build the region first:" >&2
	echo "  cd etl && python -m pipeline --city $CITY --region $REGION" >&2
	exit 1
fi

LIST="$(mktemp)"
trap 'rm -f "$LIST"' EXIT

# --list writes the paths to stdout and its logging to stderr, so this reads
# cleanly. city.json is appended because it names the others but not itself.
(cd "$ROOT/etl" && "$PYTHON" -m pipeline.export --city "$CITY" --region "$REGION" --list) >"$LIST"
echo "city.json" >>"$LIST"

mkdir -p "$DST"
rsync -a --files-from="$LIST" "$SRC/" "$DST/"

# A tile the previous build wrote and this one did not. Left behind it costs
# bundle size and nothing complains, because every check starts from the
# manifest and the manifest has forgotten it. The .import sidecar goes with it;
# an orphaned one makes Godot re-scan on the next editor open.
if [[ -d "$DST/tiles" ]]; then
	while IFS= read -r stale; do
		echo "  removing stale ${stale#"$DST/"}"
		rm -f "$stale" "$stale.import"
	done < <(find "$DST/tiles" -name '*.glb' | while IFS= read -r found; do
		grep -qxF "${found#"$DST/"}" "$LIST" || echo "$found"
	done)
fi

echo "==> $CITY / $REGION -> ${DST#"$ROOT/"} ($(wc -l <"$LIST" | tr -d ' ') files)"
