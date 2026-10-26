"""`trees:`.

One of `pipeline.config`'s blocks (`P3-77`, `Q171`), imported through
`pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import (
    Material,
    SourceLayer,
    _fields,
    _MaterialTable,
    _measures,
    _require,
)

# The drawings `pipeline/trees.py` knows. A kind names one of these; the kind's
# name is the library mesh's.
TREE_FORMS = ("crown", "palm", "fan", "cone")

# The roles a publisher's `fields:` may map. `id` is required of every one —
# the jitter is seeded on it — and the other two are what each publisher has.
_PUBLISHER_ROLES = ("id",)
_PUBLISHER_OPTIONAL = ("species", "dbh_mm")


@dataclass(frozen=True)
class TreePublisher:
    """One published inventory: where it is fetched from and what it calls things."""

    id: str
    source: str
    layer: SourceLayer

    @property
    def has_species(self) -> bool:
        return "species" in self.layer.fields

    @property
    def has_dbh(self) -> bool:
        return "dbh_mm" in self.layer.fields


@dataclass(frozen=True)
class TreeKind:
    """One library mesh: a drawing and its authored proportions."""

    form: str
    height_m: float
    trunk_radius_m: float
    # Where the leaves start, as a share of `height_m` — and the top of the
    # trunk collider.
    crown_base: float
    crown_radius_m: float
    crown_material: Material


@dataclass(frozen=True)
class Trees:
    """The published trees, stood by `pipeline/trees.py` (`P3-77`, `Q171`).

    🔴 **Only where one is surveyed.** No fill and no rhythm: the LCSD layer
    excludes the major parks and nothing publishes the roadside trees, so a
    region draws exactly what the two inventories hold and nothing between.

    ⚠️ **Every size is authored.** Neither publisher gives a height or a crown;
    HyD's `DBH` is the one measurement, and `height_per_dbh_m` turning it into
    a height is an authored ratio.
    """

    publishers: tuple[TreePublisher, ...]
    default_kind: str
    # Genus -> kind, flattened from the block's `genera:` lists.
    genera: dict[str, str]
    kinds: dict[str, TreeKind]
    bark_material: Material
    sides: int
    height_jitter: float
    height_per_dbh_m: float
    min_height_m: float
    max_height_m: float
    merge_m: float
    kerb_clear_m: float
    overhead_clear_m: float

    def kind_of(self, species: str | None) -> str:
        """The kind a published scientific name stands as: its genus's, or the default."""
        genus = (species or "").strip().split(" ")[0]
        return self.genera.get(genus, self.default_kind)


_TREE_MEASURES = (
    "height_per_dbh_m",
    "min_height_m",
    "max_height_m",
    "merge_m",
    "kerb_clear_m",
    "overhead_clear_m",
)
_KIND_MEASURES = ("height_m", "trunk_radius_m", "crown_base", "crown_radius_m")


def _publisher(body: Any, where: str) -> TreePublisher:
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    layer = SourceLayer(
        layer=str(_require(body, "layer", where)),
        fields=_fields(body, where, _PUBLISHER_ROLES, optional=_PUBLISHER_OPTIONAL),
    )
    return TreePublisher(
        id=str(_require(body, "id", where)),
        source=str(_require(body, "source", where)),
        layer=layer,
    )


def _kind(body: Any, where: str, table: _MaterialTable) -> TreeKind:
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    form = str(_require(body, "form", where))
    if form not in TREE_FORMS:
        raise ValueError(f"{where}:form {form!r} is not one of {TREE_FORMS}")
    sizes = _measures(body, where, _KIND_MEASURES, positive=True)
    if sizes["crown_base"] >= 1.0:
        # The crown starts at or above the top of the tree: a trunk with no leaves.
        raise ValueError(f"{where}:crown_base {sizes['crown_base']} is not under 1")
    if sizes["trunk_radius_m"] >= sizes["crown_radius_m"]:
        raise ValueError(f"{where}:trunk_radius_m is not under crown_radius_m")
    return TreeKind(
        form=form,
        crown_material=table.get(
            str(_require(body, "crown_material", where)), f"{where}:crown_material"
        ),
        **sizes,
    )


def _trees(body: Any, where: str, table: _MaterialTable) -> Trees | None:
    """The optional `trees:` block. Absent, the region ships no `trees.glb`."""
    if body is None:
        return None
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")

    raw_publishers = _require(body, "publishers", where)
    if not isinstance(raw_publishers, list) or not raw_publishers:
        raise ValueError(f"{where}:publishers must be a non-empty list")
    publishers = tuple(
        _publisher(entry, f"{where}:publishers[{index}]")
        for index, entry in enumerate(raw_publishers)
    )
    if len({publisher.id for publisher in publishers}) != len(publishers):
        raise ValueError(f"{where}:publishers repeats an id")

    raw_kinds = _require(body, "kinds", where)
    if not isinstance(raw_kinds, dict) or not raw_kinds:
        raise ValueError(f"{where}:kinds must be a non-empty mapping")
    kinds = {
        str(name): _kind(entry, f"{where}:kinds.{name}", table) for name, entry in raw_kinds.items()
    }
    default_kind = str(_require(body, "default_kind", where))
    if default_kind not in kinds:
        raise ValueError(f"{where}:default_kind {default_kind!r} is not a declared kind")

    genera: dict[str, str] = {}
    raw_genera = body.get("genera") or {}
    if not isinstance(raw_genera, dict):
        raise ValueError(f"{where}:genera must be a mapping of kind to genus list")
    for kind, names in raw_genera.items():
        if kind not in kinds:
            raise ValueError(f"{where}:genera names kind {kind!r}, which is not declared")
        for genus in names:
            if genus in genera:
                # One genus in two lists is two answers to one question.
                raise ValueError(f"{where}:genera lists {genus!r} under two kinds")
            genera[str(genus)] = str(kind)

    sides = int(_require(body, "sides", where))
    if sides < 3:
        raise ValueError(f"{where}:sides must be at least 3")
    jitter = float(_require(body, "height_jitter", where))
    if not 0.0 <= jitter < 1.0:
        raise ValueError(f"{where}:height_jitter {jitter} must be in [0, 1)")
    lengths = _measures(body, where, _TREE_MEASURES, positive=True)
    if lengths["min_height_m"] >= lengths["max_height_m"]:
        raise ValueError(f"{where}:min_height_m is not under max_height_m")

    return Trees(
        publishers=publishers,
        default_kind=default_kind,
        genera=genera,
        kinds=kinds,
        bark_material=table.get(
            str(_require(body, "bark_material", where)), f"{where}:bark_material"
        ),
        sides=sides,
        height_jitter=jitter,
        **lengths,
    )
