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
#
# Expects the repo-root venv the README creates. Override with
# PYTHON=$(which python) tools/sync_generated.sh if yours lives elsewhere.

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

# Validate before copying a single byte. rsync --files-from aborts on the first
# name it cannot find and leaves everything after it uncopied, which would put
# fresh tiles beside a stale manifest — a half-synced directory that every
# check downstream would then read as authoritative.
(cd "$ROOT/etl" && "$PYTHON" -m pipeline.export --city "$CITY" --region "$REGION" --check)

LIST="$(mktemp)"
trap 'rm -f "$LIST"' EXIT

# --list writes the paths to stdout and its logging to stderr, so this reads
# cleanly. city.json leads the list; it names the others but not itself.
(cd "$ROOT/etl" && "$PYTHON" -m pipeline.export --city "$CITY" --region "$REGION" --list) >"$LIST"
if [[ ! -s "$LIST" ]]; then
	echo "the manifest named no files — refusing to treat everything as stale" >&2
	exit 1
fi
# The sweep below deletes whatever is not in this list, so a --list that stopped
# emitting the manifest would delete the manifest. Pinned here, at the use.
if ! grep -qxF "city.json" "$LIST"; then
	echo "--list did not name city.json; the sweep would delete it" >&2
	exit 1
fi

mkdir -p "$DST"
rsync -a --files-from="$LIST" "$SRC/" "$DST/"

# Anything the manifest does not name. Left behind it costs bundle size and
# nothing complains, because every check in the project starts from the
# manifest and the manifest has forgotten it — 120 MB of P1-2t terrain
# evaluation was shipping this way. The sweep covers the whole tree rather than
# tiles/ alone, which is where the first version of this stopped.
#
# .import sidecars follow their asset rather than being matched themselves, and
# .gitkeep is committed. grep -vxF -f does the whole comparison in one pass;
# per-file greps would delete on any grep failure, including an unreadable list.
while IFS= read -r stale; do
	echo "  removing stale $stale"
	rm -f "$DST/$stale" "$DST/$stale.import"
done < <(cd "$DST" && find . -type f ! -name '*.import' ! -name '.gitkeep' \
	| sed 's|^\./||' | grep -vxF -f "$LIST" || true)
find "$DST" -type d -empty -delete

echo "==> $CITY / $REGION -> ${DST#"$ROOT/"} ($(wc -l <"$LIST" | tr -d ' ') files)"
