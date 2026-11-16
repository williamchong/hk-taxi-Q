# Contributing

**Read [`CLAUDE.md`](CLAUDE.md) first.** It carries the locked decisions and the hard rules, and most
review comments on a first PR are things it already answers.

---

## Licensing of contributions

**By submitting a pull request you license your contribution to this project under the MIT licence**,
regardless of the licence the project distributes under.

That asymmetry is deliberate and it is worth understanding before you contribute:

- **Outbound**, this project is **GPL-3.0-or-later** (code) and **CC BY-SA 4.0** (authored assets),
  and a distributed build also carries a third-party **CC BY 4.0** typeface whose attribution travels
  with it (`LICENSING.md`, `Q79`). That does not change, and your contribution reaches the public
  under those terms.
- **Inbound is MIT** because GPLv3 cannot be distributed through the App Store, so mobile builds must
  ship under a separate proprietary grant — and a grant can only be given for code the project is
  free to relicense. A GPL-only patch would permanently close that route.

MIT permits sublicensing, which is the specific property that makes this work. It is the lightest
arrangement that does; the alternative is a signed CLA, which is more friction for everyone.

If you are not willing to contribute on those terms, please open an issue instead of a PR — the
suggestion is still welcome, and it keeps the copyright position clean.

See [`LICENSING.md`](LICENSING.md) for the full picture, including what the generated city data is
governed by (it is not ours to license).

---

## Before you open a PR

```bash
# Python — ruff from the repo root, not etl/: the root ruff.toml extends the ETL rules to tools/*.py
.venv/bin/ruff check . && .venv/bin/ruff format --check .
(cd etl && ../.venv/bin/pytest)             # `pytest -n auto` runs it across your cores

# Godot — the only route that fails on error; the target scene must also run
tools/check.sh
```

- **Git LFS is required, before the clone.** The authored binaries are LFS objects (`P5-27`); a
  clone without `git-lfs` holds pointer files and `tools/check.sh` fails on them.
  `brew install git-lfs && git lfs install`, then `git lfs pull` in a clone already made.
- **Do not run the Godot steps by hand and read the output.** Godot exits `0` even when a script
  fails to parse, so only `tools/check.sh`'s exit code means anything. `VERIFY_GENERATED=0` skips
  the verify tools that need a built city; CI runs it that way.
- **A headless import re-tabs the tracked `game/assets/authored/greybox_wanchai.json`** (`Q115`).
  Run `git status` after `check.sh` and `git checkout` that file.
- **`pytest` passes more on your machine than in CI, and the difference is `etl/sources/`.** That
  tree is gitignored and CI never fetches, so a test that reaches a fetched artefact must skip
  itself. The trap is a test that reaches one through a stage without meaning to (`Q19`). Run the
  CI condition before you push; it should pass as a plain run does, bar the tests that skip:

  ```bash
  cd etl && ../.venv/bin/python -c "
  import pathlib, sys, tempfile
  import pytest
  import pipeline.fetch as fetch
  fetch.SOURCES_ROOT = pathlib.Path(tempfile.mkdtemp())
  sys.exit(pytest.main(['-q']))
  "
  ```

- **ETL changes:** the pipeline must run end to end on the Wan Chai config.
- **Graders:** `tools/check.sh` cannot see a yellow line on the wrong kerb or a fence standing in
  the road; a measurement does. `CLAUDE.md`'s "Before marking work done" is the index: a table of
  triggers, each naming the `.claude/rules/<name>.md` that says which tool a change owes.
  `tools/battery.py --list` carries the same triggers with their commands. Its exit code says every
  item ran, not that a number held.

---

## Conventions

- **Commits:** `<emoji> <task-id> <imperative summary>`, no brackets — e.g.
  `🐛 P2-3 Stop the camera clipping through podium frontage`. The task ID is required when the work
  maps to a task in [`docs/PLAN.md`](docs/PLAN.md) and omitted otherwise. `CLAUDE.md` has the emoji
  table.
- **Python:** `ruff` for lint and format, type hints on public functions, `pytest` for tests.
- **GDScript:** `snake_case` files and functions, `PascalCase` classes, **static typing is enforced**
  — untyped declarations fail the build. `gdformat` owns layout; do not hand-format around it.
- **Comments state what is true, not what changed.** A comment carries the claim and the refusal —
  *"never hold these apart"* — not the edit that produced it: *"this used to be two maps"*. Where the
  reasoning is a decision, cite its ID and let [`docs/DECISIONS.md`](docs/DECISIONS.md) hold the
  evidence, keeping one number locally so the refusal sticks. **A `schema_version` history is the
  exception**: a bump means a reader would be *wrong* to keep its old interpretation (`CLAUDE.md` hard
  rule 5), which cannot be stated without naming the old one.
- **Generated assets are build output.** Never commit anything under `game/assets/generated/`,
  `etl/out/` or `etl/sources/`.
- **Rationale for a resource goes in its sidecar, never in the file.** Godot rewrites every
  `.tres`, `.tscn`, `project.godot` and `export_presets.cfg` on save and drops comments, so each
  resource's argument lives in `<name>.md` beside it and the config files' in
  [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). `tools/check.sh` refuses a `;` line in a resource
  and requires the sidecar (`Q119`).
- **Update [`docs/PROGRESS.md`](docs/PROGRESS.md)** when a task changes status or a number is
  re-measured, and **[`docs/DECISIONS.md`](docs/DECISIONS.md)** when a decision is made or a question
  closes. Decision records are keyed by ID and stated in the present tense — no dates, no narration.

## Scope

If a task's acceptance criteria turn out to be wrong, say so and propose a change rather than quietly
redefining it. If your change touches the ETL↔game data contract, both sides move in the same commit
and `schema_version` bumps — see the rule in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
