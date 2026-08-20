"""The second-source audit (`tools/kerbside_source_audit.py`, `Q56`).

The same standard as the other tool tests: pin only what fails silently. What
the tool prints is loud, and the join it runs is `pipeline/kerbside.py`'s, tested
in `test_kerbside.py`. What would not announce itself is the translation between
them — a drawing's marking code becoming a synthetic time zone — and the cell
arithmetic that turns two sets of runs into metres.

⚠️ **The failure this file exists for: an audit that agrees by construction.**
`_as_restriction_spec` must carry the graded block's *sampling* numbers over
unchanged while replacing its *kinds* entirely. Get that backwards — inherit the
kinds, or re-choose the pitch — and the tool reports agreement it did not
measure, on every region, for ever, with no symptom.
"""

from __future__ import annotations

import pytest
from kerbside_source_audit import (
    _PAINTED,
    _UNMAPPED,
    Report,
    _as_restriction_spec,
    _Cell,
    _cell_range,
    _kind_codes,
    _tally,
)

from pipeline import kerbside
from pipeline.config import KerbsideAudit, KerbsideRestrictions, SourceLayer

_AUDIT = KerbsideAudit(
    source="drawings",
    layer=SourceLayer(layer="DRAWN", fields={"line_type": "LINETYPE"}),
    kinds={"RM1040": "double", "RM1041": "single"},
)

_SPEC = KerbsideRestrictions(
    layer=SourceLayer(layer="NSR", fields={"vehicle_type": "VT", "time_zone": "TZ"}),
    painted_vehicle_types=frozenset({1, 5}),
    kinds={1: "double", 2: "single"},
    sample_m=1.0,
    bridge_gap_m=3.0,
    min_run_m=5.0,
    max_offset_m=20.0,
    audit=_AUDIT,
)


class TestSpec:
    def test_the_sampling_numbers_are_carried_over_untouched(self) -> None:
        """The diff has to be a difference between sources. Re-choosing a pitch
        here would make the two answers differ because they were measured
        differently, which is the one thing this tool must not do."""
        translated = _as_restriction_spec(_SPEC, _AUDIT)
        assert translated.sample_m == _SPEC.sample_m
        assert translated.bridge_gap_m == _SPEC.bridge_gap_m
        assert translated.min_run_m == _SPEC.min_run_m
        assert translated.max_offset_m == _SPEC.max_offset_m

    def test_the_kinds_are_replaced_rather_than_inherited(self) -> None:
        """Inheriting them would route both sources through one `TIME_ZONE`
        table, and the audit would agree with the thing it is grading."""
        translated = _as_restriction_spec(_SPEC, _AUDIT)
        assert set(translated.kinds.values()) == {"double", "single"}
        # Every synthetic code resolves — `kind_for` raises otherwise, which is
        # how a marking code with no slot would surface.
        assert {translated.kind_for(code) for code in translated.kinds} == {"double", "single"}

    def test_a_kind_survives_the_round_trip_through_its_synthetic_code(self) -> None:
        """The seam between the two halves of the translation. `_as_restriction_layer`
        writes `_kind_codes`' numbering into the column; this table is what
        `kerbside.build` reads it back through. Derived twice and drifted apart —
        `sorted` dropped on one side, say — the codec inverts and every `RM1040`
        grades as a single, which prints as a full directional disagreement table
        and so reads as a finding about the source rather than as a bug."""
        translated = _as_restriction_spec(_SPEC, _AUDIT)
        codes = _kind_codes(_AUDIT)
        assert {
            marking: translated.kind_for(codes[kind]) for marking, kind in _AUDIT.kinds.items()
        } == _AUDIT.kinds

    def test_only_the_synthetic_painted_code_paints(self) -> None:
        """The graded block's own vehicle-type list is meaningless here: the
        drawings carry no such field. Carrying it over would let a code the
        translation assigns to 'unmapped' be painted by coincidence."""
        translated = _as_restriction_spec(_SPEC, _AUDIT)
        assert translated.painted_vehicle_types == frozenset({_PAINTED})
        assert _UNMAPPED not in translated.painted_vehicle_types


class TestCellRange:
    def test_a_run_covers_the_cells_between_its_ends(self) -> None:
        assert list(_cell_range(3.0, 7.0, 1.0)) == [3, 4, 5, 6]

    def test_the_pitch_is_the_join_s_own(self) -> None:
        """Both sides come out of one sampler at one pitch, so the raster is
        lossless — a half-metre run at a metre pitch cannot arise."""
        assert list(_cell_range(4.0, 6.0, 2.0)) == [2]


def _cells(rows: dict[tuple[int, str], dict[int, tuple[str | None, str | None]]]):
    return {
        key: {index: _Cell(published=pair[0], drawing=pair[1]) for index, pair in found.items()}
        for key, found in rows.items()
    }


class TestTally:
    def test_agreement_counts_once_per_metre(self) -> None:
        report = Report()
        _tally(_cells({(1, kerbside.NEARSIDE): {0: ("double", "double")}}), 1.0, {}, report)
        assert (report.both, report.agreed) == (1.0, 1.0)
        assert report.kind_agreement == pytest.approx(1.0)
        assert report.union == 1.0

    def test_a_kind_disagreement_is_kept_directional(self) -> None:
        """Which way round it goes is the finding. 'Published double where the
        drawing says single' is a restriction the game over-asserts; the reverse
        is one it under-asserts, and a symmetric counter hides both."""
        report = Report()
        _tally(_cells({(1, kerbside.NEARSIDE): {0: ("double", "single")}}), 1.0, {}, report)
        assert report.kinds == {("double", "single"): 1.0}
        assert report.both == 1.0
        assert report.agreed == 0.0

    def test_a_metre_only_one_source_carries_lands_in_its_own_column(self) -> None:
        report = Report()
        _tally(
            _cells({(1, kerbside.NEARSIDE): {0: ("double", None), 1: (None, "single")}}),
            1.0,
            {},
            report,
        )
        assert (report.published_only, report.drawing_only) == (1.0, 1.0)
        assert report.both == 0.0
        assert report.coverage == 0.0

    def test_the_same_metre_on_the_other_kerb_is_reported_as_opposite(self) -> None:
        """Both sources restrict this edge and disagree about which side. Not a
        mirrored world — that moves both answers together and this tool cannot
        see it — but one source putting a run on the wrong kerb of one edge."""
        report = Report()
        _tally(
            _cells(
                {
                    (1, kerbside.NEARSIDE): {0: ("double", None)},
                    (1, kerbside.OFFSIDE): {0: (None, "double")},
                }
            ),
            1.0,
            {},
            report,
        )
        assert report.opposite == 1.0

    def test_a_run_the_other_side_also_publishes_is_not_opposite(self) -> None:
        """If the published graph already restricts both kerbs, the drawing's
        run on the far side is agreement, not a side error — counting it would
        make a fully restricted street look like the worst case in the region."""
        report = Report()
        _tally(
            _cells(
                {
                    (1, kerbside.NEARSIDE): {0: ("double", None)},
                    (1, kerbside.OFFSIDE): {0: ("double", "double")},
                }
            ),
            1.0,
            {},
            report,
        )
        assert report.opposite == 0.0

    def test_disagreements_are_attributed_to_a_street(self) -> None:
        """The totals say how much; this says where to go and look."""
        report = Report()
        _tally(
            _cells({(7, kerbside.NEARSIDE): {0: ("double", None), 1: ("double", "single")}}),
            1.0,
            {7: "HENNESSY ROAD"},
            report,
        )
        assert report.by_road["HENNESSY ROAD"] == 2.0

    def test_an_edge_with_no_name_still_gets_a_row(self) -> None:
        """`road_names` omits an unnamed slip road entirely, and a disagreement
        that fell out of the table because of that would be invisible."""
        report = Report()
        _tally(_cells({(9, kerbside.NEARSIDE): {0: ("double", None)}}), 1.0, {}, report)
        assert report.by_road == {"edge 9": 1.0}
