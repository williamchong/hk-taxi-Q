---
paths:
  - "etl/pipeline/kerbside.py"
  - "tools/kerbside_error.py"
  - "tools/kerbside_source_audit.py"
  - "etl/tests/test_kerbside*.py"
---

# Kerbside restrictions — before marking work done

Moved verbatim from the root `CLAUDE.md`, which keeps the trigger and points here.

- **`pipeline/kerbside.py`, the `NSR` config block, or any kerbside-marking change: also
  `tools/kerbside_error.py`, and paste its table.** It grades the shipped `roads.glb` against the runs
  `roadgraph.json` publishes, and it is the only instrument that can see the side convention flip —
  a mirrored city renders as a city. ⚠️ It **does not** grade the join itself: the truth side is what
  the pipeline published, so a restriction on the wrong centreline is agreed with rather than caught.
  What covers that is `etl/tests/test_kerbside.py`, which pins the side against `surface.mitres`
  rather than against a comment.
- **`painted_vehicle_types`, `kinds`, or anything that changes *which* restrictions are published:
  also `tools/kerbside_source_audit.py`, and paste its table.** It runs the pipeline's own join over
  the Traffic Aids Drawings — a second, independently digitised source of the same restrictions —
  and diffs the two answers. It is **the only instrument that can grade the kind**: every consumer
  takes double-versus-single on trust from `NSR.TIME_ZONE`, so a wrong mapping renders perfectly
  (`Q56`). ⚠️ It needs `traffic_aids_drawings_gdb`, a **218 MB** fetch; get it with `--only` on a
  clone that has not built. ⚠️ **It is ordinary build input since `P3-12`/`P3-14`** — seven config
  blocks read it — 🔴 **and the audit's second-source property never rested on that**: it rests on
  the *layer*, TD's drawn marking codes against `NSR`'s restriction register.
  ⚠️ It grades rather than checks — a widening gap is a finding to go and look at, never a
  bar to retune against — and it **cannot** see the side convention flip, because that mirrors both
  sources at once.
