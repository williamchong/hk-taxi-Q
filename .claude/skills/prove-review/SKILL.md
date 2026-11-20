---
name: prove-review
description: Review a change in hk-taxi-Q by proving it safe with something that runs - a mutation, a battery item, a byte or triangle-set comparison against a before side, a frame - and drop any finding that was not run. Also checks that the comments the diff adds or touches are still true. Use when asked to prove, interrogate or blast-radius a change, before committing a refactor that must not change output, or when a reading review is not enough.
---

# Prove a change by running it

`code-review` reads code. This proves it. A finding nobody ran is an opinion, and it reads in the
same confident voice as a real one, so it is dropped.

## 1. Name the one fact

Write one sentence: the fact the change is safe because of. Examples:

- "The pole's triangles are the same set before and after; only the cap's fan corner moves."
- "No column stands nearer the kerb than before: `min_kerb_clearance_m` does not drop."
- "The grader still imports nothing it grades."

If you cannot write it, you do not know what the change does yet. Read more before reviewing.

## 2. Prove it by running something real

Pick the cheapest instrument that can fail on that fact:

| The fact is about | Run |
|---|---|
| A test or counter catches a defect | `~/.claude/skills/godot-mutation-check/mutate.sh` on the code under test (GDScript or Python); a SURVIVED is a finding |
| A stage's output did not move, or moved only where intended | `tools/battery.py <trigger> --region <r> --before <root>` (`--list` for triggers); read the diff, never the exit code |
| A refactor changed no geometry | Load both sides' glb or JSON and compare: vertex sets, triangle sets, normals, byte equality of the rest |
| Something looks right | A frame from each side (`godot-ab-render`); crop before comparing |
| A change reaches past its own rule | `CLAUDE.md`'s "Three changes reach past their own rule": widening, shader, carve |

The before side is a detached worktree at the base commit (`ARCHITECTURE.md`, "Grading tools";
`--tools-from side` once the schema has moved).

## 3. Check the comments the diff touches

For each comment or docstring the diff adds or edits, and each one next to a changed line:

- Every symbol, file and function it names still exists (`grep`).
- Every `Qnnn` it cites is about this topic: read the entry's heading. `test_decision_citations.py`
  only proves the entry exists; `Q59` cited for the winding signs passed it.
- Every number it states matches the code or a fresh run, where re-running is cheap.
- A refusal it states ("never merge…", "do not iterate…") could be a test. Offer the test; do not
  write it unasked.

A comment that is wrong gets corrected, never deleted for being long: this repo keeps the measured
reason beside the code (`CONTRIBUTING.md`). Before deleting a comment a new test replaces, check
`Q259`'s "held by" list: some exceptions are held by their docstring alone.

## 4. Report

Only findings you ran. For each: the fact, the command, what it printed, the verdict. Put
everything you suspected but did not run under "Not proven", one line each, or leave it out.
