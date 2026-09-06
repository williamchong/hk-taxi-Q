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
	verify_spawn verify_landmarks verify_fence verify_tramway verify_arrows verify_boxjunctions
	verify_railings verify_signs verify_roadmarks verify_signals verify_lamps
)

# The verify tools that need no built region, so they run whatever
# VERIFY_GENERATED says. Most grade the taxi, which is a committed authored asset
# plus its tuning: verify_beam_budget builds its own stub rigs, and
# verify_vehicle instantiates taxi.tscn. Grouping them with the generated-asset
# tools above would skip them exactly where they are cheapest to run: CI builds
# no region, so these are the only runtime contracts it can check at all.
#
# verify_hud is here for a sharper version of that reason: what it protects is
# P2-4's future screen space, and P2-4 is exactly the kind of work that lands on
# a branch where nobody has built a city.
#
# verify_input is here for the sharpest version of it: P0-3b has no handset, so
# until it lands that tool is the only thing that exercises the touch scheme at
# all. Gating it on a built region would mean the input path went unchecked on
# exactly the branches where input work happens.
ALWAYS_TOOLS=(verify_beam_budget verify_vehicle verify_mesh_contract verify_hud verify_input)

# Tuning resources and scenes that carry no sidecar .md, and are allowed not
# to. The `tuning` step below fails anything else without one, so the default
# is inverted: a new .tres has to explain itself or be named here deliberately.
# Reasons are given, because an unexplained exemption is how a list like this
# rots into a way of silencing the check.
#
#   camera.tres       Q98 is three commits old and its argument is still in the
#                     decision entry rather than in the file.
#   handling.tres     The drift model's rationale is CLAUDE.md's and Q84-Q89's,
#                     and it is far too long to mirror at the resource.
#   golden_hour.tres  clean_daylight.tres carries the comparison for both rigs.
#   streaming.tres    Three numbers, all of them in ARCHITECTURE.md's budget.
#   beams.tres        Same, and verify_beam_budget states the contract in full.
#   greybox.tscn      A P0-5 harness that predates the convention.
UNDOCUMENTED_OK=(
	game/tuning/camera.tres
	game/tuning/handling.tres
	game/tuning/golden_hour.tres
	game/tuning/streaming.tres
	game/tuning/beams.tres
	game/scenes/dev/greybox.tscn
)

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

# ⚠️ The file count is asserted, not just the status. Pointed at a directory
# holding no .gd — a wrong $ROOT, a partial checkout — gdformat prints "0 files
# would be left unchanged" and exits 0, so the step passed having formatted
# nothing. Same shape as the warnings sweep below, and the only step that
# reported no `ok` line at all to say what it had covered.
echo "==> gdformat"
fmt_out="$("$GDFORMAT" --check "$ROOT/game" 2>&1)"
fmt_status=$?
echo "$fmt_out"
fmt_files="$(sed -n 's/^\([0-9][0-9]*\) file.*/\1/p' <<<"$fmt_out" | head -1)"
if ((fmt_status != 0)); then
	echo "  FAIL  gdformat — see above" >&2
	failed=1
elif [[ -z "$fmt_files" || "$fmt_files" == 0 ]]; then
	echo "  FAIL  gdformat — checked 0 files under $ROOT/game, so nothing was" >&2
	echo "        checked. That is not the same as nothing being wrong." >&2
	failed=1
else
	echo "  ok    gdformat — $fmt_files files"
fi

# Rationale for a .tres/.tscn lives in a sidecar .md beside it, never in the
# file. Godot's writer regenerates a resource from the object in memory on every
# editor save and drops every comment — on 2026-08-31 one save took ~30 lines
# of Q31's contrast argument out of clean_daylight.tres, and on 2026-09-07 the
# 1,334 comment lines then inside 26 files were moved out so a save costs
# nothing. Measured before the move: the writer omits only what already equals
# the class default, so a .tres cannot lose a value that is doing work (0
# differing stored properties across the stripped Environment, Sky and sky
# material). What was at risk was always the argument, never the numbers.
#
# Three assertions, and each is a false green rather than a style point:
#   1. Every .tres/.tscn has a non-empty sidecar unless UNDOCUMENTED_OK names
#      it, so a new tuning resource cannot slip in unexplained.
#   2. No .tres/.tscn carries a `;` line at all. A comment put back into the
#      resource is the hazard returning, and it would survive exactly until
#      the next editor save.
#   3. No sidecar stands beside a file that is gone, and no exemption names a
#      file that has since gained a sidecar — the list must describe the tree.
#
# ⚠️ Three shell guards here, each a false green rather than a style point.
# `-type f`, because a directory named `*.tres` makes the grep fail with empty
# stdout and the old `grep -c` form read that as 0. `grep -q` rather than `-c`,
# because the question is existence and its error status reads as "no prose",
# which fails loudly. And `[@]+`, because bash 3.2 ships on macOS and
# `"${arr[@]}"` on an EMPTY array under `set -u` aborts the whole script.
echo "==> tuning"
resources="$(
	{
		find "$ROOT/game/tuning" -type f -name '*.tres'
		find "$ROOT/game/scenes" -type f -name '*.tscn'
	} | sort
)"
# One pass over the resources answers both questions; the two lists are split
# by their prefix afterwards, because a `while` in a `$( )` cannot set two
# variables in the calling shell.
findings="$(
	while IFS= read -r doc; do
		rel="${doc#"$ROOT/"}"
		grep -q '^;' "$doc" && echo "I  $rel"
		exempt=0
		for ok in "${UNDOCUMENTED_OK[@]+"${UNDOCUMENTED_OK[@]}"}"; do
			if [[ "$rel" == "$ok" ]]; then
				exempt=1
				break
			fi
		done
		((exempt)) && continue
		sidecar="${doc%.*}.md"
		if [[ ! -f "$sidecar" ]] || ! grep -q '[^[:space:]]' "$sidecar"; then
			echo "M  $rel — no sidecar ${sidecar#"$ROOT/"}"
		fi
	done <<<"$resources"
)"
missing="$(sed -n 's/^M //p' <<<"$findings")"
inline="$(sed -n 's/^I //p' <<<"$findings")"
orphans="$(
	{
		find "$ROOT/game/tuning" -type f -name '*.md'
		find "$ROOT/game/scenes" -type f -name '*.md'
	} | sort | while IFS= read -r sidecar; do
		stem="${sidecar%.md}"
		if [[ ! -f "$stem.tres" && ! -f "$stem.tscn" ]]; then
			echo "  ${sidecar#"$ROOT/"} — no .tres or .tscn beside it"
		fi
	done
)"
stale="$(
	for ok in "${UNDOCUMENTED_OK[@]+"${UNDOCUMENTED_OK[@]}"}"; do
		if [[ ! -f "$ROOT/$ok" ]]; then
			echo "  $ok — no such file"
		elif [[ -f "$ROOT/${ok%.*}.md" ]]; then
			echo "  $ok — has a sidecar now, so the exemption is stale"
		fi
	done
)"
if [[ -n "$missing" ]]; then
	echo "$missing"
	echo "  FAIL  tuning — the files above carry no rationale. Write the sidecar;" >&2
	echo "        do NOT add them to UNDOCUMENTED_OK to quiet this." >&2
	failed=1
fi
if [[ -n "$inline" ]]; then
	echo "$inline"
	echo "  FAIL  tuning — the files above carry a \`;\` comment. Rationale goes in" >&2
	echo "        the sidecar .md; the next editor save would delete this." >&2
	failed=1
fi
if [[ -n "$orphans" ]]; then
	echo "$orphans"
	echo "  FAIL  tuning — orphan sidecars. Delete them or restore the resource." >&2
	failed=1
fi
if [[ -n "$stale" ]]; then
	echo "$stale"
	echo "  FAIL  tuning — UNDOCUMENTED_OK no longer describes the tree. Drop" >&2
	echo "        the entries above; each one is a hole in the check." >&2
	failed=1
fi
if [[ -z "$missing$inline$orphans$stale" ]]; then
	echo "  ok    tuning"
fi

echo "==> import"
run_godot "import" --headless --path "$ROOT/game" --import

# 🔴 NO GODOT PROCESS MAY BE LAUNCHED ABOVE `==> import`. That is the durable
# rule; what follows is why, and which step learned it the hard way.
#
# A `class_name` resolves out of .godot/global_script_class_cache.cfg, which
# only the import scan writes — so on a clone that has never been imported,
# every autoload naming one fails to parse and Godot reports that on stderr of
# WHATEVER command ran first. ⚠️ The tool itself need not name a global:
# verify_settings.gd names none, and the autoloads Godot instantiates around
# any --script run name four between them. This step was that command, and it took CI red on
# CityManifest, VehicleController, TouchProfile and HudLayout while the tool
# itself printed `ok`. It ran first when it was a grep, which needed no engine;
# turning it into a Godot script gave it a prerequisite the position never had.
# Nothing is lost by moving it. The import does read two of the pinned settings
# — the [importer_defaults] keys and import_etc2_astc — but this script never
# exits early: a failed step sets `failed` and the run continues, so the import
# always ran on whatever project.godot said whether or not the check had already
# reported the loss. Checking first never protected that import; it only
# reported sooner, into a run that goes on to the end regardless.
# docs/DECISIONS.md `Q119` "The settings step needed the import that ran
# after it" has the measurement and the CI log that named the wrong step.
#
# Settings that no other check would notice going missing, read back through
# ProjectSettings by tools/verify_settings.gd rather than grepped out of
# project.godot. The grep was the wrong instrument: Godot's own writer — the
# editor's save and ProjectSettings.save() alike — omits every key whose value
# equals the engine's registered default, so three of the 21 warning promotions
# and rendering_method.web vanish from the FILE on every save while staying in
# FORCE. For three weeks that read as "an editor save dropped the settings";
# it never had. Reading the value back passes a canonical, editor-written
# project.godot and fails a setting that has really been lost — which is the
# only distinction worth checking. docs/ARCHITECTURE.md "Project settings" has
# the rows and the history.
echo "==> settings"
run_godot "verify_settings" --headless --path "$ROOT/game" --script "res://tools/verify_settings.gd"

# The GDScript lint pass. --import alone is not it: measured, it compiles
# autoloads and what they reach, so an untyped variable planted in
# greybox_builder.gd — reachable only through a dev scene — went unreported.
# --check-only reaches every file, and grepping for the promoted warnings keeps
# it honest, since it exits 0 and also reports autoload identifiers it cannot
# resolve on its own.
#
# The project directory is load-bearing. Resolve res:// from anywhere else and
# every script analyses clean, so this passes having checked nothing — measured
# with a planted `var x = 1`: `--path game` and a `cd` into it both report the
# promoted warning, and neither reports it.
#
# 🔴 Which is why the file list is taken FIRST and its emptiness is a failure.
# `cd` inside a `$( )` exits the SUBSHELL, not this script — so written as one
# substitution, `cd ... || exit 1` set `lint_hits` empty, `[[ -n ]]` read that as
# "no warnings", and the step printed `ok` having swept nothing. That is the
# exact false green the paragraph above warns about, sitting inside the check
# that warns about it. Splitting the list out makes the failure representable: a
# failed `cd` and a failed `find` both leave `$scripts` empty, and empty is
# fatal. The count is printed for the same reason — a swept 0 must be visible,
# and it is `grep -c .` rather than `wc -l` because a herestring appends a
# newline and `wc -l` would report a swept 0 as 1.
#
# 🔴 `Parse Error` is in the pattern as well as `treated as error`, and that is
# the hole this step shipped with. A file no autoload reaches, carrying a
# SEMANTIC parse error — `var x: NoSuchType = null` — formats clean under
# gdformat and is refused by Godot, and the old pattern matched neither. Measured
# on this tree: `check.sh` printed `ok warnings — 72 scripts swept` and
# `All checks passed`, exit 0, over a script the engine cannot parse. That is the
# header's own failure mode surviving inside the sweep built to catch it. ⚠️ A
# plain syntax error is caught by gdformat, which is why this went unseen; a
# semantic one is invisible to a formatter by construction.
#
# ⚠️ The pattern is NOT `$FATAL`, and widening it to that would break every run:
# `--check-only` resolves no autoloads, so a healthy sweep emits **4** lines
# matching `SCRIPT ERROR|Failed to load script` — `Identifier not found:
# DebugHud`, and `hud.gd` / `road_graph_overlay.gd` failing to compile behind it.
# `Parse Error` is measured at **0** across the healthy 71, which is what makes
# it the one term that can be added.
#
# ⚠️ Serial on purpose, and the usual reason for that is measured FALSE — record
# it rather than re-deriving it. `--check-only` writes nothing under `.godot/`
# (hashed before and after, byte-identical), so concurrent runs do not race the
# import cache, and `xargs -P 8` is 1.47 s against 10.09 s with identical output.
# What refuses it is portability and safety, not correctness: BSD/macOS `xargs`
# has no `-d`, and the `-I{} sh -c` form interpolates a filename into a shell
# command. That trades ~8.6 s — noise beside CI's 76 MB engine download — for a
# metacharacter in a path executing, in the one script whose job is not lying.
# `find -print0 | xargs -0 -P8 -n1` is the safe form if it is ever revisited.
#
# ⚠️ The sweep itself takes `--path` and does NOT cd, deliberately. A second `cd`
# here would be the same subshell-exit shape again — succeeding on line one and
# failing here leaves `lint_hits` empty and prints `ok` with the stale count —
# and it bought nothing `--path` does not, which is what every other Godot call
# in this file already passes.
echo "==> warnings"
scripts="$(cd "$ROOT/game" && find . -name '*.gd' | sed 's|^\./|res://|')"
if [[ -z "$scripts" ]]; then
	echo "  FAIL  warnings — swept 0 scripts under $ROOT/game, so nothing was" >&2
	echo "        checked. That is not the same as nothing being wrong." >&2
	failed=1
else
	lint_hits="$(
		while IFS= read -r script; do
			"$GODOT" --headless --path "$ROOT/game" --check-only --script "$script" 2>&1 |
				sed "s|^|$script: |"
		done <<<"$scripts" | grep -E 'treated as error|Parse Error'
	)"
	if [[ -n "$lint_hits" ]]; then
		echo "$lint_hits"
		echo "  FAIL  warnings — see above" >&2
		failed=1
	else
		echo "  ok    warnings — $(grep -c . <<<"$scripts") scripts swept"
	fi
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
