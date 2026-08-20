#!/usr/bin/env bash
# Run every Godot-side check, and fail if any of them fails.
#
#   tools/check.sh
#
# Exists because none of these checks can fail on their own. Godot exits 0 no
# matter what: 0 when a script fails to parse, 0 when a GDScript warning is
# treated as an error, 0 when --import cannot compile a dependency. quit(1) in
# a verify tool only runs if that tool parsed, which is exactly the case a
# parse error rules out — dea1f36 fixed one route to that failure and promoting
# warnings to errors opened another. So stderr is the signal, and this script
# is the only thing that turns it into an exit code.
#
# Expects the repo-root venv the README creates, and godot on PATH. Override
# with GODOT= / GDFORMAT= if yours live elsewhere, and VERIFY_GENERATED=0 if
# there is no built city to check.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GODOT="${GODOT:-godot}"
GDFORMAT="${GDFORMAT:-$ROOT/.venv/bin/gdformat}"

# The verify tools assert facts about generated assets, which are build output —
# absent from a fresh clone until the ETL has run and been synced. Set
# VERIFY_GENERATED=0 where there is no city to check; CI does, because building
# one there means downloading 320 MB from a government server on every push. The
# skip is announced, never silent: a check that reported nothing because it had
# nothing to look at is the exact failure this script exists to turn into an
# exit code.
#
# Compared as a string, and only an exact 0 skips. `((VERIFY_GENERATED))` was
# the obvious form and is a trapdoor: under `set -u`, VERIFY_GENERATED=true dies
# mid-run with `unbound variable` and still exits 0, while =1x reports "value
# too great for base", takes the skip branch, and prints "All checks passed".
# Both are the false green this whole script exists to prevent. Anything
# unrecognised therefore runs the checks.
VERIFY_GENERATED="${VERIFY_GENERATED:-1}"
VERIFY_TOOLS=(
	verify_city verify_tiles verify_road_surface verify_road_graph verify_city_streamer
	verify_spawn verify_landmarks verify_tramway
)

# The verify tools that need no built region, so they run whatever
# VERIFY_GENERATED says. Both grade the taxi, which is a committed authored asset
# plus its tuning: verify_beam_budget builds its own stub rigs, and
# verify_vehicle instantiates taxi.tscn. Grouping them with the generated-asset
# tools above would skip them exactly where they are cheapest to run: CI builds
# no region, so these are the only runtime contracts it can check at all.
ALWAYS_TOOLS=(verify_beam_budget verify_vehicle)

# Godot reports a compile failure with any of these and still exits 0.
FATAL='Parse Error|SCRIPT ERROR|Failed to load script|Failed to compile'

failed=0

# Runs a Godot command and fails the script if either signal says it went
# wrong: a compile failure named in the output, or a non-zero status. Both are
# needed. The output check catches parse failures, which exit 0. The status
# check catches a verify tool that parsed fine and then found real problems,
# which reports them through quit(1) and prints nothing matching FATAL.
run_godot() {
	local label="$1"
	shift
	local out status
	out="$("$GODOT" "$@" 2>&1)"
	status=$?
	echo "$out"
	if ((status != 0)); then
		echo "  FAIL  $label — exit $status" >&2
		failed=1
		return
	fi
	if grep -qE "$FATAL" <<<"$out"; then
		echo "  FAIL  $label — compile failure, and Godot still exited 0" >&2
		failed=1
		return
	fi
	echo "  ok    $label"
}

echo "==> gdformat"
if ! "$GDFORMAT" --check "$ROOT/game"; then
	failed=1
fi

echo "==> import"
run_godot "import" --headless --path "$ROOT/game" --import

# The GDScript lint pass. --import alone is not it: measured, it compiles
# autoloads and what they reach, so an untyped variable planted in
# greybox_builder.gd — reachable only through a dev scene — went unreported.
# --check-only reaches every file, and grepping for the promoted warnings keeps
# it honest, since it exits 0 and also reports autoload identifiers it cannot
# resolve on its own.
#
# The cd is load-bearing. Run from anywhere else, res:// does not resolve, every
# script analyses clean, and this passes having checked nothing.
echo "==> warnings"
lint_hits="$(
	cd "$ROOT/game" || exit 1
	find . -name '*.gd' | sed 's|^\./|res://|' | while IFS= read -r script; do
		"$GODOT" --headless --check-only --script "$script" 2>&1 | sed "s|^|$script: |"
	done | grep 'treated as error'
)"
if [[ -n "$lint_hits" ]]; then
	echo "$lint_hits"
	echo "  FAIL  warnings — see above" >&2
	failed=1
else
	echo "  ok    warnings"
fi

for tool in "${ALWAYS_TOOLS[@]}"; do
	echo "==> $tool"
	run_godot "$tool" --headless --path "$ROOT/game" --script "res://tools/$tool.gd"
done

if [[ "$VERIFY_GENERATED" != 0 ]]; then
	for tool in "${VERIFY_TOOLS[@]}"; do
		echo "==> $tool"
		run_godot "$tool" --headless --path "$ROOT/game" --script "res://tools/$tool.gd"
	done
else
	echo "==> verify tools"
	echo "  SKIP  ${VERIFY_TOOLS[*]} — VERIFY_GENERATED=0."
	echo "        The generated-asset contracts were NOT checked."
fi

if ((failed)); then
	echo >&2
	echo "FAILED — at least one check above did not pass." >&2
	exit 1
fi
echo
echo "All checks passed."
