"""`pipeline/trees.py` — the published trees (`P3-77`, `Q171`).

What is asserted is what nothing downstream can see: which publisher's record
wins a shared tree, that a tree stands the same every build, how a height is
got, and that every kind is drawn wound outward with its foot on the ground.
The no-trunk-in-the-road invariant is the stage's own `min_kerb_clearance_m`,
pasted before and after per `.claude/rules/trees.md`.
"""

from __future__ import annotations

import copy
from typing import Any

import numpy as np
import pytest
import yaml

from pipeline.config import CONFIG_PATH, _materials, _MaterialTable
from pipeline.config_blocks.trees import _trees
from pipeline.railings import facing_away
from pipeline.trees import (
    TREES_MATERIAL,
    Tree,
    _rng,
    draw_kind,
    height_of,
    merge,
    tint_of,
    trunks,
)


def _tree(publisher: str, ident: str, x: float, z: float, **kwargs: Any) -> Tree:
    return Tree(
        publisher=publisher,
        ident=ident,
        x=x,
        z=z,
        species=kwargs.get("species"),
        dbh_mm=kwargs.get("dbh_mm"),
    )


# --------------------------------------------------------------------------
# The block
# --------------------------------------------------------------------------


def test_shipped_block_reads_both_publishers_in_precedence_order(hong_kong) -> None:
    spec = hong_kong.trees
    assert spec is not None
    # LCSD first: it names the species, HyD names none.
    assert [publisher.id for publisher in spec.publishers] == ["lcsd", "hyd"]
    assert spec.publishers[0].has_species and not spec.publishers[0].has_dbh
    assert spec.publishers[1].has_dbh and not spec.publishers[1].has_species
    assert spec.default_kind in spec.kinds


@pytest.mark.parametrize(
    ("species", "kind"),
    [
        ("Roystonea regia", "palm"),
        ("Livistona chinensis", "fan_palm"),
        ("Casuarina equisetifolia", "conifer"),
        ("Ficus microcarpa", "broadleaf"),
        (None, "broadleaf"),
        ("  ", "broadleaf"),
    ],
)
def test_kind_is_read_off_the_genus(hong_kong, species: str | None, kind: str) -> None:
    assert hong_kong.trees.kind_of(species) == kind


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda b: b.update(default_kind="oak"), "default_kind"),
        (lambda b: b["genera"]["palm"].append("Livistona"), "two kinds"),
        (lambda b: b["genera"].update(shrub=["Ixora"]), "not declared"),
        (lambda b: b["kinds"]["palm"].update(form="bush"), "form"),
        (lambda b: b["kinds"]["palm"].update(crown_base=1.0), "crown_base"),
        (lambda b: b["kinds"]["palm"].update(trunk_radius_m=3.0), "trunk_radius_m"),
        (lambda b: b.update(min_height_m=20.0), "min_height_m"),
        (lambda b: b.update(height_jitter=1.0), "height_jitter"),
        (lambda b: b.update(width_jitter=-0.1), "width_jitter"),
        (lambda b: b.update(tint_darken=1.0), "tint_darken"),
        (lambda b: b["publishers"].append(dict(b["publishers"][0])), "repeats an id"),
    ],
)
def test_block_refuses(mutate, message: str) -> None:
    # The shipped block with one thing broken, so each refusal is the only fault.
    document = yaml.safe_load(CONFIG_PATH.read_text())
    table = _MaterialTable(_materials(document["materials"], "materials"))
    body = copy.deepcopy(document["trees"])
    mutate(body)
    with pytest.raises(ValueError, match=message):
        _trees(body, "trees", table)


# --------------------------------------------------------------------------
# Merge, seed and height
# --------------------------------------------------------------------------


def test_merge_keeps_the_first_publishers_record() -> None:
    trees = [
        _tree("lcsd", "1", 10.0, 10.0, species="Ficus microcarpa"),
        _tree("hyd", "A", 10.3, 10.0, dbh_mm=300.0),
        _tree("hyd", "B", 11.0, 10.0, dbh_mm=300.0),
    ]
    kept, merged = merge(trees, 0.5)
    assert merged == 1
    assert [(tree.publisher, tree.ident) for tree in kept] == [("lcsd", "1"), ("hyd", "B")]


def test_merge_looks_across_a_cell_edge() -> None:
    # 0.49 and 0.51 sit in neighbouring 0.5 m cells, 0.02 m apart.
    kept, merged = merge([_tree("a", "1", 0.49, 0.0), _tree("b", "2", 0.51, 0.0)], 0.5)
    assert merged == 1 and len(kept) == 1


def test_seed_is_the_trees_identity() -> None:
    one = _tree("hyd", "T1", 1.0, 2.0)
    moved = _tree("hyd", "T1", 99.0, 2.0)
    other = _tree("hyd", "T2", 1.0, 2.0)
    assert _rng(one).uniform() == _rng(moved).uniform()
    assert _rng(one).uniform() != _rng(other).uniform()


def test_height_comes_off_the_trunk_clamped(hong_kong) -> None:
    spec = hong_kong.trees
    kind = spec.kinds["broadleaf"]
    middle = (spec.min_height_m + spec.max_height_m) / 2.0
    dbh = middle / spec.height_per_dbh_m
    height, by_dbh = height_of(spec, _tree("hyd", "1", 0, 0, dbh_mm=dbh), kind, 1.0)
    assert by_dbh and height == pytest.approx(middle)
    huge, _ = height_of(spec, _tree("hyd", "2", 0, 0, dbh_mm=1e6), kind, 0.0)
    tiny, _ = height_of(spec, _tree("hyd", "3", 0, 0, dbh_mm=1.0), kind, 0.0)
    assert (huge, tiny) == (spec.max_height_m, spec.min_height_m)


def test_height_without_a_trunk_is_the_kinds_jittered(hong_kong) -> None:
    spec = hong_kong.trees
    kind = spec.kinds["palm"]
    low, by_dbh = height_of(spec, _tree("lcsd", "1", 0, 0), kind, -1.0)
    high, _ = height_of(spec, _tree("lcsd", "1", 0, 0), kind, 1.0)
    assert not by_dbh
    assert low == pytest.approx(kind.height_m * (1.0 - spec.height_jitter))
    assert high == pytest.approx(kind.height_m * (1.0 + spec.height_jitter))


# --------------------------------------------------------------------------
# The library
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["broadleaf", "palm", "fan_palm", "conifer"])
def test_every_kind_is_wound_outward_and_stands_on_its_foot(hong_kong, name: str) -> None:
    spec = hong_kong.trees
    kind = spec.kinds[name]
    mesh = draw_kind(spec, name, kind)
    assert mesh is not None and mesh.material == TREES_MATERIAL
    assert facing_away(mesh) == 0
    low, high = mesh.positions.min(axis=0), mesh.positions.max(axis=0)
    assert low[1] == pytest.approx(0.0)
    # Drawn at its kind's height; a palm's fronds arch a little over the head
    # before they droop, which the scaled stand absorbs.
    assert kind.height_m - 1e-6 <= high[1] <= kind.height_m + 0.5
    # The crown is centred on the trunk, so the yaw turns the tree in place.
    centre = (low + high) / 2.0
    assert np.hypot(centre[0], centre[2]) < 0.5 * kind.crown_radius_m


def test_trunk_collider_is_the_bare_trunk(hong_kong) -> None:
    spec = hong_kong.trees
    table = trunks(spec)
    assert set(table) == set(spec.kinds)
    for name, kind in spec.kinds.items():
        assert table[name]["radius_m"] == kind.trunk_radius_m
        assert table[name]["height_m"] == pytest.approx(kind.crown_base * kind.height_m, abs=1e-4)


# --------------------------------------------------------------------------
# Variation
# --------------------------------------------------------------------------


@pytest.mark.parametrize("darken", [0.0, 0.5, 1.0])
@pytest.mark.parametrize("warmth", [-1.0, 0.0, 1.0])
def test_tint_only_darkens(hong_kong, darken: float, warmth: float) -> None:
    # No channel over 1: no tree lighter than the colour `Q33` grades.
    spec = hong_kong.trees
    red, green, blue = tint_of(spec, darken, warmth)
    assert max(red, green, blue) <= 1.0
    assert green == pytest.approx(1.0 - spec.tint_darken * darken, abs=1e-3)
    # Warm takes blue, cool takes red; never both.
    assert (red < green) == (warmth < 0.0)
    assert (blue < green) == (warmth > 0.0)


def test_untinted_at_rest(hong_kong) -> None:
    assert tint_of(hong_kong.trees, 0.0, 0.0) == (1.0, 1.0, 1.0)
