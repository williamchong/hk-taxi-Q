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
# with GODOT= / GDFORMAT= if yours live elsewhere.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GODOT="${GODOT:-godot}"
GDFORMAT="${GDFORMAT:-$ROOT/.venv/bin/gdformat}"

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

for tool in verify_city verify_tiles verify_road_surface; do
	echo "==> $tool"
	run_godot "$tool" --headless --path "$ROOT/game" --script "res://tools/$tool.gd"
done

if ((failed)); then
	echo >&2
	echo "FAILED — at least one check above did not pass." >&2
	exit 1
fi
echo
echo "All checks passed."
