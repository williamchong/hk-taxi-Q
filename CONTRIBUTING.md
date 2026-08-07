# Contributing

**Read [`CLAUDE.md`](CLAUDE.md) first.** It carries the locked decisions and the hard rules, and most
review comments on a first PR are things it already answers.

---

## Licensing of contributions

**By submitting a pull request you license your contribution to this project under the MIT licence**,
regardless of the licence the project distributes under.

That asymmetry is deliberate and it is worth understanding before you contribute:

- **Outbound**, this project is **GPL-3.0-or-later** (code) and **CC BY-SA 4.0** (authored assets).
  That does not change, and your contribution reaches the public under those terms.
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
ruff check . && ruff format --check .      # from the repo root, not etl/
cd etl && pytest && cd ..

# Godot — the only route that fails on error
tools/check.sh
```

⚠️ **Do not run the Godot steps by hand and read the output.** Godot exits `0` even when a script
fails to parse, so only `tools/check.sh`'s exit code means anything. This has produced a green check
that checked nothing more than once.

If you changed the ETL, the pipeline must run end to end on the Wan Chai config. If you changed the
road surface or deck heights, also run `tools/deck_error.py` and `tools/overhang.py` — they grade the
shipped bundle and need a built region. If you moved the height ramp or the façade survey, run
`tools/ring_weights.py` and paste what it derives: the surveyed material weights are authored against
both, and nothing in the checks can see that they have gone stale (`Q34′`).

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
