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
# Python
ruff check . && ruff format --check .      # from the repo root, not etl/ — the root
                                           # ruff.toml extends the ETL rules to tools/*.py
cd etl && pytest && cd ..

# Godot — the only route that fails on error; the target scene must also run
tools/check.sh
```

⚠️ **Do not run the Godot steps by hand and read the output.** Godot exits `0` even when a script
fails to parse, so only `tools/check.sh`'s exit code means anything. This has produced a green check
that checked nothing more than once.

⚠️ **`pytest` passes more on your machine than it does in CI, and the difference is `etl/sources/`.**
That tree is gitignored and `.github/workflows/ci.yml` deliberately never fetches, so a test that
reaches a fetched artefact passes for you and fails for everyone else. The convention is that such a
test skips itself — `requires a fetched sheet index` — and the trap is a test that reaches one
*through a stage* without meaning to. Run the CI condition before you push:

```bash
cd etl && python -c "
import pathlib, sys, tempfile
import pytest
import pipeline.fetch as fetch
fetch.SOURCES_ROOT = pathlib.Path(tempfile.mkdtemp())
sys.exit(pytest.main(['-q']))
"
```

It should pass exactly as a plain run does, bar the handful that skip themselves; a **failure** there
is a test coupled to your own build. `carve.build_region` took a whole `Placement` for its `out_dir`
alone, so refusing to carve an already-carved bundle needed a fetched sheet index — which left CI red
for eight runs, and nobody running the suite locally could see it (`docs/DECISIONS.md` `Q19`).

If you changed the ETL, the pipeline must run end to end on the Wan Chai config.

**Then there are the graders, and `CLAUDE.md`'s "Before marking work done" is the list** — kept per
change, naming which file you touched, which tool that owes and the numbers to paste. Read it there;
a second copy of it here goes stale against it.

What the list is *for* is not obvious from any single row: **`tools/check.sh` cannot see any of it.**
A yellow line on the wrong kerb, a fence standing in the road, a sign face drawn in negative, an
arrow turned 180° — every one of them renders perfectly, and the only thing that catches them is a
measurement pasted into a doc where the next person can see it go stale. That is why the graders exit
0 whatever they find: they **grade**, they do not gate, and a widening gap is a finding to go and
look at rather than a bar to retune against.

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
  evidence, keeping one number locally so the refusal sticks. ⚠️ **A `schema_version` history is the
  exception**: a bump means a reader would be *wrong* to keep its old interpretation (`CLAUDE.md` hard
  rule 5), which cannot be stated without naming the old one.
- **Generated assets are build output.** Never commit anything under `game/assets/generated/`,
  `etl/out/` or `etl/sources/`.
- ⚠️ **Never commit `game/project.godot` or `game/export_presets.cfg` as a side effect.** Opening the
  editor or running an export rewrites both and strips their comments. Restore with
  `git checkout` and verify with `git diff --exit-code`.
- **Update [`docs/PROGRESS.md`](docs/PROGRESS.md)** when a task changes status or a number is
  re-measured, and **[`docs/DECISIONS.md`](docs/DECISIONS.md)** when a decision is made or a question
  closes. Decision records are keyed by ID and stated in the present tense — no dates, no narration.

## Scope

If a task's acceptance criteria turn out to be wrong, say so and propose a change rather than quietly
redefining it. If your change touches the ETL↔game data contract, both sides move in the same commit
and `schema_version` bumps — see the rule in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
