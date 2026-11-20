#!/usr/bin/env bash
# Copy built regions from the ETL into the Godot project.
#
#   tools/sync_generated.sh                      # the regions already synced, else wan_chai
#   tools/sync_generated.sh <region> [<region>...]
#   tools/sync_generated.sh --drop <region> [<region>...]   # and delete the rest
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

GENERATED="$ROOT/game/assets/generated"

# 🔴 A region synced now and missing from the arguments is deleted by the sweep
# at the bottom. `tools/sync_generated.sh wan_chai` on a two-region tree did
# exactly that, and nothing said so until verify_join failed. So dropping one
# takes --drop; without it the run refuses before touching anything.
DROP=0
if [[ "${1:-}" == "--drop" ]]; then
	DROP=1
	shift
	if [[ $# -eq 0 ]]; then
		echo "--drop takes the regions to keep" >&2
		exit 1
	fi
fi
SYNCED=""
if [[ -f "$GENERATED/regions.json" ]]; then
	SYNCED="$("$PYTHON" -c 'import json, sys; print(*json.load(open(sys.argv[1]))["regions"])' \
		"$GENERATED/regions.json")"
fi

# With no argument the list is the one the last sync wrote, in its order, so the
# frame region stays the frame. It was `wan_chai` alone, and the sweep at the
# bottom removes every region not listed: a bare re-sync of a two-region tree
# deleted the second one.
if [[ $# -eq 0 ]]; then
	# shellcheck disable=SC2086
	set -- $SYNCED
	if [[ $# -eq 0 ]]; then
		set -- wan_chai
	fi
fi
REGIONS=("$@")

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

DROPPED=""
for REGION in $SYNCED; do
	if ! printf '%s\n' "${REGIONS[@]}" | grep -qxF "$REGION"; then
		DROPPED="$DROPPED $REGION"
	fi
done
if ((!DROP)) && [[ -n "$DROPPED" ]]; then
	echo "this sync would delete the synced region(s)$DROPPED. List them too," >&2
	echo "or pass --drop first to delete them." >&2
	exit 1
fi

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

# The far versions of the regions not synced (`Q249`): a far-only region,
# seen across the harbour and never driven, or a driven one this sync does not
# hold. Each ships its far version alone — `backdrop.glb` and the manifest that
# places it — and the game hides one past `far_view.tres`'s `max_far_m`. Every
# one the ETL has built at the current schema goes with every sync.
# Captured before the loop rather than read from a process substitution, whose
# failure `set -e` never sees: a --built that died would list nothing, and the
# sweep below would then delete every far version synced before.
BUILT="$(cd "$ROOT/etl" && "$PYTHON" -m pipeline.backdrop --built)"
FAR=()
while IFS= read -r REGION; do
	[[ -z "$REGION" ]] && continue
	for RESIDENT in "${REGIONS[@]}"; do
		[[ "$REGION" == "$RESIDENT" ]] && continue 2
	done
	FAR+=("$REGION")
done <<<"$BUILT"
for REGION in ${FAR[@]+"${FAR[@]}"}; do
	SRC="$ROOT/etl/out/$REGION"
	DST="$GENERATED/$REGION"
	mkdir -p "$DST"
	# The whole directory is these two, so everything else goes — a region
	# synced whole before leaves directories — keeping the glb's import sidecar.
	find "$DST" -mindepth 1 -maxdepth 1 ! -name 'backdrop.glb.import' -exec rm -rf {} +
	cp "$SRC/backdrop.glb" "$SRC/backdrop.json" "$DST/"
	echo "==> $REGION -> ${DST#"$ROOT/"} (far only)"
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
	printf ']'
	printf ',\n  "far": ['
	sep=""
	for REGION in ${FAR[@]+"${FAR[@]}"}; do
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
	| sed 's|^\./||' | grep -vxF -f <(printf '%s\n' "${REGIONS[@]}" ${FAR[@]+"${FAR[@]}"}) || true)

echo "==> regions.json: ${REGIONS[*]} (frame ${REGIONS[0]}), far only: ${FAR[*]-none}"
