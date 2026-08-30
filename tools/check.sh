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
	verify_spawn verify_landmarks verify_tramway verify_arrows verify_boxjunctions
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

# Promotions docs/ARCHITECTURE.md "GDScript warnings" says project.godot must
# carry. Named here so the number the settings check wants and the number its
# diagnostic prints cannot drift apart — the failure it warns against is
# someone editing one of them down to match a regression.
WANT_PROMOTED=21

# Tuning resources and scenes that carry no rationale in the file, and are
# allowed not to. The `tuning` step below fails anything else that carries
# none, so the default is inverted: a new .tres has to explain itself or be
# named here deliberately. Reasons are given, because an unexplained exemption
# is how a list like this rots into a way of silencing the check.
#
#   camera.tres       Q98 is three commits old and its argument is still in the
#                     decision entry rather than in the file.
#   handling.tres     The drift model's rationale is CLAUDE.md's and Q84-Q89's,
#                     and it is far too long to mirror at the resource.
#   golden_hour.tres  clean_daylight.tres carries the comparison for both rigs.
#   streaming.tres    Three numbers, all of them in ARCHITECTURE.md's budget.
#   beams.tres        Same, and verify_beam_budget states the contract in full.
#   greybox.tscn      A P0-5 harness that predates the convention.
#   main.tscn         Four lines that do nothing but hand off to city_drive.
UNDOCUMENTED_OK=(
	game/tuning/camera.tres
	game/tuning/handling.tres
	game/tuning/golden_hour.tres
	game/tuning/streaming.tres
	game/tuning/beams.tres
	game/scenes/dev/greybox.tscn
	game/scenes/main.tscn
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

echo "==> gdformat"
if ! "$GDFORMAT" --check "$ROOT/game"; then
	failed=1
fi

# Settings that no other check would notice going missing. Opening the editor
# rewrites project.godot from scratch: it discards every comment, and it drops
# hand-written feature overrides — keys with a `.web` / `.mobile` suffix — which
# the editor only persists when it created them itself. That is not
# hypothetical. 78c077e, a commit about the start line, silently took three
# warning promotions and rendering_method.web out in one editor save, and
# nothing failed for three weeks: the warnings sweep below greps Godot's output
# for "treated as error", and Godot emits that only for a warning project.godot
# itself promotes, so the sweep reads its own enforcement list out of the file
# it is enforcing. A promotion that is no longer set cannot fail.
#
# Counts, not names: docs/ARCHITECTURE.md "GDScript warnings" and "Project
# settings" hold the durable list and the rationale, and this is the tripwire
# that says go and read them. untyped_declaration is named as well as counted,
# because CLAUDE.md makes it a hard rule rather than one of 21 equals, and a
# count passes happily when it is swapped for some other promotion.
#
# Every pattern is anchored, and the renderer pins its value. An unanchored key
# matches a comment that merely mentions it, and passes that key commented out
# or set to the wrong renderer; all three were demonstrated against this file.
# The two feature overrides are pinned separately rather than counted as a
# class, because they did not share a fate: 78c077e took rendering_method.web
# and left run/max_fps.mobile standing.
echo "==> settings"
project_godot="$ROOT/game/project.godot"
promoted="$(grep -c '^gdscript/warnings/.*=2$' "$project_godot" || true)"
untyped="$(grep -c '^gdscript/warnings/untyped_declaration=2$' "$project_godot" || true)"
web_renderer="$(grep -c '^renderer/rendering_method\.web="gl_compatibility"$' "$project_godot" || true)"
mobile_fps="$(grep -c '^run/max_fps\.mobile=' "$project_godot" || true)"
# 🔴 Pinned to its VALUE, not counted. MSAA degrades silently: dropped or set to
# 0, nothing errors, no counter moves and the only symptom is thin geometry —
# the box junction hatch, sign poles, lamp columns — breaking into dashes at
# middle distance, which is what it was turned on to stop. 4x (2) is also the
# ceiling WebGL2 guarantees, so 8x here would be clamped on the web cut and
# quietly diverge the platforms. `Q91` measured it; docs/ARCHITECTURE.md
# "Project settings" has the row.
msaa="$(grep -c '^anti_aliasing/quality/msaa_3d=2$' "$project_godot" || true)"
# 🔴 Pinned to its VALUE, not merely counted. Godot quantises imported vertex
# positions over each mesh's own AABB, so the step scales with how wide a layer
# is rather than how big its objects are — 0.025 m across `lamps.glb`, against a
# 0.06 m bracket arm and 0.032 m sign poles. Dropped or set false, every
# generated mesh imports slightly different geometry from the one the ETL built,
# and the only symptom is a verify tool's count disagreeing with a stage's own.
# `Q82` measured it; `docs/ARCHITECTURE.md` "Project settings" has the row.
# ⚠️ The trailing comma is optional because it is not ours to control: this key
# sits in a `scene={...}` dict and Godot puts a comma after every entry but the
# last, so adding a third importer default would move one onto this line. Pinned
# strictly, that reads as the setting having been LOST — a false alarm pointing
# at a message that says not to edit the check down to match.
mesh_compression="$(grep -c '^"meshes/force_disable_compression": true,\{0,1\}$' "$project_godot" || true)"
if [[ "$promoted" != "$WANT_PROMOTED" || "$untyped" != 1 || "$web_renderer" != 1 || "$mobile_fps" != 1 || "$mesh_compression" != 1 || "$msaa" != 1 ]]; then
	echo "  promoted warnings:    $promoted (want $WANT_PROMOTED)"
	echo "  untyped_declaration:  $untyped (want 1)"
	echo "  rendering_method.web: $web_renderer (want 1)"
	echo "  max_fps.mobile:       $mobile_fps (want 1)"
	echo "  mesh compression off: $mesh_compression (want 1)"
	echo "  msaa_3d=2 (4x):       $msaa (want 1)"
	echo "  FAIL  settings — project.godot lost settings, most likely to an" >&2
	echo "        editor save. Restore them; do NOT edit the numbers here down" >&2
	echo "        to match. See docs/ARCHITECTURE.md \"Project settings\"." >&2
	failed=1
else
	echo "  ok    settings"
fi

# Godot's .tres/.tscn writer regenerates a file from the resource in memory, so
# it drops every comment — the same loss the settings step above catches in
# project.godot, in a file class nothing was watching. On 2026-08-31 one editor
# save took both: project.godot lost three warning promotions and
# rendering_method.web, and clean_daylight.tres lost the ~30 lines carrying
# Q31's contrast measurement and the ambient/glow balance argument.
#
# ⚠️ The two halves failed DIFFERENTLY, and the difference is what this step is
# shaped by. Measured afterwards, the .tres lost no value at all — 0 differing
# stored properties across the Environment, its Sky and its sky material —
# because the writer omits only what already equals the class default, so it
# cannot drop a value that is doing work. What is at risk in a .tres is the
# argument for the numbers, never the numbers. This step therefore tests for
# prose, and pinning values here would be guarding the half that is safe.
#
# 🔴 Presence, not a count. Comments die ALL AT ONCE — the writer never
# preserves one — so "carried prose, now carries none" is a signature no honest
# edit produces. A per-file count would fail on every legitimate rewording and
# teach the reader to edit the number down, which is the failure the settings
# step's own diagnostic exists to warn against; a noisy check is how you cause
# it.
#
# The default is inverted: everything in these two globs must carry a comment
# unless UNDOCUMENTED_OK names it, so a newly added tuning resource cannot slip
# in unwatched. 20 of 25 .tres and 6 of 8 .tscn carry prose today —
# city_facade.tres is 83 comment lines of 160, and city_drive.tscn is 99.
# ⚠️ Three guards here, and each is a false green rather than a style point.
# `-type f`, because a directory named `*.tres` makes the grep fail with empty
# stdout, and the old `grep -c` form compared that to 0, came out false and
# dropped the file from the report. `grep -q` rather than `-c`, because the
# question is existence and not a count — and its error status reads as "no
# prose", which fails loudly instead. And `[@]+`, because bash 3.2 ships on
# macOS and `"${arr[@]}"` on an EMPTY array under `set -u` aborts the whole
# script: every check below this line would be skipped rather than failed, on a
# list the comment above invites people to shorten.
echo "==> tuning"
stripped="$(
	{
		find "$ROOT/game/tuning" -type f -name '*.tres'
		find "$ROOT/game/scenes" -type f -name '*.tscn'
	} | sort | while IFS= read -r doc; do
		rel="${doc#"$ROOT/"}"
		exempt=0
		for ok in "${UNDOCUMENTED_OK[@]+"${UNDOCUMENTED_OK[@]}"}"; do
			if [[ "$rel" == "$ok" ]]; then
				exempt=1
				break
			fi
		done
		((exempt)) && continue
		grep -q '^;' "$doc" || echo "  $rel"
	done
)"
if [[ -n "$stripped" ]]; then
	echo "$stripped"
	echo "  FAIL  tuning — the files above carry no rationale. Most likely an" >&2
	echo "        editor save: Godot rewrites a .tres/.tscn from the resource" >&2
	echo "        in memory and drops every comment. Restore them from git; do" >&2
	echo "        NOT add them to UNDOCUMENTED_OK to quiet this." >&2
	failed=1
fi

# The exemption list is checked against the tree, not merely read. A renamed
# file leaves a dead entry behind, and a file that GAINS rationale keeps an
# exemption it no longer needs — the list shrinking the rule quietly, which is
# exactly what its own comment says not to let happen. Publishing the refusals
# is only worth something if the refusals are still true.
stale="$(
	for ok in "${UNDOCUMENTED_OK[@]+"${UNDOCUMENTED_OK[@]}"}"; do
		if [[ ! -f "$ROOT/$ok" ]]; then
			echo "  $ok — no such file"
		elif grep -q '^;' "$ROOT/$ok"; then
			echo "  $ok — carries rationale now, so the exemption is stale"
		fi
	done
)"
if [[ -n "$stale" ]]; then
	echo "$stale"
	echo "  FAIL  tuning — UNDOCUMENTED_OK no longer describes the tree. Drop" >&2
	echo "        the entries above; each one is a hole in the check." >&2
	failed=1
fi

if [[ -z "$stripped" && -z "$stale" ]]; then
	echo "  ok    tuning"
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
