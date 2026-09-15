#!/usr/bin/env bash
# Copy built regions from the ETL into the Godot project.
#
#   tools/sync_generated.sh                      # wan_chai
#   tools/sync_generated.sh <region> [<region>...]
#
# Each region lands in its own directory, game/assets/generated/<region>/, and
# the list goes to game/assets/generated/regions.json in argument order — the
# FIRST region is the frame every other one is placed relative to (P5-9b). The
# list is a fact about this sync, not tuning: it is build output, gitignored
# with the bundles, and hard rule 4 does not reach it.
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

if [[ $# -eq 0 ]]; then
	set -- wan_chai
fi
REGIONS=("$@")
GENERATED="$ROOT/game/assets/generated"

# Every region is checked before any is copied, for the reason the per-region
# --check below gives: a sync that stops half way leaves a tree every check
# downstream reads as authoritative.
# No associative array for the duplicate test: macOS ships bash 3.2.
for REGION in "${REGIONS[@]}"; do
	if [[ ! "$REGION" =~ ^[a-z0-9_]+$ ]]; then
		echo "bad region '$REGION' — a region id is lower-case letters, digits and _" >&2
		exit 1
	fi
	if (($(printf '%s\n' "${REGIONS[@]}" | grep -cxF "$REGION") > 1)); then
		echo "region $REGION listed twice" >&2
		exit 1
	fi
	if [[ ! -f "$ROOT/etl/out/$REGION/city.json" ]]; then
		echo "No manifest at etl/out/$REGION/city.json. Build the region first:" >&2
		echo "  cd etl && python -m pipeline --region $REGION" >&2
		exit 1
	fi
done

LIST="$(mktemp)"
trap 'rm -f "$LIST"' EXIT

sync_region() {
	local REGION="$1"
	local SRC="$ROOT/etl/out/$REGION"
	local DST="$GENERATED/$REGION"

	# Validate before copying a single byte. rsync --files-from aborts on the first
	# name it cannot find and leaves everything after it uncopied, which would put
	# fresh tiles beside a stale manifest — a half-synced directory that every
	# check downstream would then read as authoritative.
	(cd "$ROOT/etl" && "$PYTHON" -m pipeline.export --region "$REGION" --check)

	# --list writes the paths to stdout and its logging to stderr, so this reads
	# cleanly. city.json leads the list; it names the others but not itself.
	(cd "$ROOT/etl" && "$PYTHON" -m pipeline.export --region "$REGION" --list) >"$LIST"
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

	echo "==> $REGION -> ${DST#"$ROOT/"} ($(wc -l <"$LIST" | tr -d ' ') files)"
}

for REGION in "${REGIONS[@]}"; do
	sync_region "$REGION"
done

# Written last, so a failed region above leaves the previous list in place
# rather than one naming a directory that never arrived.
{
	printf '{\n  "schema_version": 1,\n  "regions": ['
	sep=""
	for REGION in "${REGIONS[@]}"; do
		printf '%s"%s"' "$sep" "$REGION"
		sep=", "
	done
	printf ']\n}\n'
} >"$GENERATED/regions.json"

# The top level holds the list and the listed regions, and nothing else: a flat
# bundle from before P5-9b, or a region synced before and not listed now, is
# stale on exactly the terms the per-region sweep gives — it costs PCK and
# nothing complains, because nothing loads it.
while IFS= read -r stale; do
	[[ -z "$stale" ]] && continue
	echo "  removing stale ${stale}"
	rm -rf "${GENERATED:?}/$stale"
done < <(cd "$GENERATED" && find . -mindepth 1 -maxdepth 1 ! -name regions.json ! -name .gitkeep \
	| sed 's|^\./||' | grep -vxF -f <(printf '%s\n' "${REGIONS[@]}") || true)

echo "==> regions.json: ${REGIONS[*]} (frame ${REGIONS[0]})"
