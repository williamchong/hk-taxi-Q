---
paths:
  - "etl/pipeline/kerbside.py"
  - "tools/kerbside_error.py"
  - "tools/kerbside_source_audit.py"
  - "etl/tests/test_kerbside*.py"
---

# Kerbside restrictions — before marking work done

- **`pipeline/kerbside.py`, the `NSR` block, any kerbside-marking change**:
  `tools/kerbside_error.py --region <r>`, and paste its table. It grades the shipped `roads.glb`
  against the runs `roadgraph.json` publishes and is the only instrument that sees the side
  convention flip. It cannot see a restriction joined to the wrong centreline;
  `etl/tests/test_kerbside.py` pins the side against `surface.mitres`.
- **`painted_vehicle_types`, `kinds`, or which restrictions are published**:
  `tools/kerbside_source_audit.py --region <r>`, and paste its table. It runs the pipeline's join
  over the Traffic Aids Drawings (TD's drawn marking codes, against `NSR`'s register) and diffs the
  answers. It is the only grader of the kind: double-versus-single comes on trust from
  `NSR.TIME_ZONE` (`Q56`). It needs `traffic_aids_drawings_gdb` (218 MB). It grades, never gates,
  and cannot see the side flip, which mirrors both sources.
