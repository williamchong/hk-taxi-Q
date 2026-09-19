"""`fares:`.

One of `pipeline.config`'s blocks (`P3-35f`, `Q133`) — moved whole, and imported
through `pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pipeline.config_blocks.base import _field, _fields, _require

# Fare-node kinds in the data contract. `poi` is listed because the contract
# lists it; no dataset produces one yet, and a city that adds hotels or malls
# adds a group rather than a code path.
TAXI_STAND = "taxi_stand"


PUDO = "pudo"


POI = "poi"


FARE_KINDS = (TAXI_STAND, PUDO, POI)


# What a fare group must name in the publisher's schema, in roles the pipeline
# owns. Same indirection as `_ROAD_LAYER_ROLES` and for the same reason.
#
# ⚠️ **Only `category` is required, and the two names are deliberately not**
# (`P3-14`). TD's Tram Stop Location publishes an `OBJECTID`, a `STOP_ID` and a
# revision date, and no name in either language — 117 features, none named. The
# alternatives were both worse than an absent role: pointing `name_en` at a
# column that does not exist makes the config assert something untrue, and
# pointing it at `STOP_ID` ships "99101" as a place name.
#
# `fares.py` already treats an unnamed node as a state rather than an error — it
# counts them in `FareReport.unnamed` and warns — so a null name reaches the
# contract intact and says what the source says.
_FARE_ROLES = ("category",)


_FARE_OPTIONAL_ROLES = ("name_en", "name_zh")


@dataclass(frozen=True)
class FareCategory:
    """One rule turning a publisher's category text into a contract slug.

    `match` is a substring rather than an exact value, because the categories
    are free text with an operating-time note glued on: Hong Kong publishes a
    stand as `Cross Harbour Taxi Stand\\n(1200-0600 daily)`. Sixteen distinct
    strings collapse to five categories that way.

    Rules are tried in order and the first hit wins, so a city file orders them
    most specific first — `load_config` refuses a table where a later rule could
    never be reached.
    """

    match: str
    id: str
    # Whether a fare may be hailed here, and whether one may be delivered here.
    # Not every legal drop-off point is a legal pick-up point: a quarter of
    # Hong Kong's published points are drop-off only, and a game that let a
    # player hail at one would be wrong in a way a local would notice.
    pickup: bool
    dropoff: bool


@dataclass(frozen=True)
class FareGroup:
    """One published point dataset, and what kind of fare node it produces."""

    # A `kind` in the data contract. The pipeline owns this vocabulary.
    kind: str
    # Which `sources:` entry holds the dataset.
    source: str
    # Datum the dataset's coordinates are on, which need not be the region's.
    # GeoJSON with no `crs` member is CRS84 per RFC 7946 — state that here
    # rather than let a reader assume it.
    crs: str
    fields: dict[str, str]
    categories: tuple[FareCategory, ...]

    def field(self, role: str) -> str:
        return _field(self.fields, role, f"fare group '{self.kind}'")

    def optional_field(self, role: str) -> str | None:
        """The publisher's column for a role it need not publish at all.

        `None` where the source has no such column, which is a fact about the
        source rather than a hole in the config — see `_FARE_OPTIONAL_ROLES`.
        Separate from `field` so a *required* role still fails loudly: silently
        returning `None` for `category` would file every feature under nothing.
        """
        if role not in _FARE_OPTIONAL_ROLES:
            raise KeyError(
                f"fare group '{self.kind}': {role!r} is a required role, "
                f"use `field` — optional roles are {', '.join(_FARE_OPTIONAL_ROLES)}"
            )
        return self.fields.get(role)

    def categorise(self, text: str) -> FareCategory:
        """The first rule whose `match` appears in `text`.

        An unmatched category raises rather than defaulting. These datasets are
        republished twice a year, and a new category appearing in one should
        stop the build — silently filing it under the fallback would ship a
        premium cross-harbour stand as an ordinary one.
        """
        folded = text.casefold()
        for rule in self.categories:
            if rule.match.casefold() in folded:
                return rule
        known = ", ".join(repr(rule.match) for rule in self.categories)
        raise KeyError(
            f"fare group '{self.kind}' has a feature categorised {text!r}, which matches no "
            f"rule. Rules: {known}"
        )


@dataclass(frozen=True)
class Fares:
    """How `P1-5` turns published point datasets into fare nodes."""

    groups: tuple[FareGroup, ...]
    # Furthest a source point may sit from a road edge and still be attached to
    # it. Beyond this the node is dropped: a fare node whose `nearest_edge`
    # names a road it has no relationship with is worse than no fare node.
    max_snap_m: float
    # Strings that mean "no value" in a text field, as in `RoadNetwork`.
    null_values: tuple[str, ...]


def _fares(body: dict[str, Any], where: str) -> Fares:
    groups = tuple(
        _fare_group(entry, f"{where}:groups[{index}]")
        for index, entry in enumerate(_require(body, "groups", where))
    )
    if not groups:
        raise ValueError(f"{where}:groups is empty")

    max_snap_m = float(_require(body, "max_snap_m", where))
    if max_snap_m <= 0.0:
        # Zero would require a source point to lie exactly on a centreline.
        # Every real one is a kerbside position half a carriageway away.
        raise ValueError(f"{where}:max_snap_m must be positive, got {max_snap_m}")

    return Fares(
        groups=groups,
        max_snap_m=max_snap_m,
        null_values=tuple(str(value) for value in (body.get("null_values") or ())),
    )


def _fare_group(body: dict[str, Any], where: str) -> FareGroup:
    kind = str(_require(body, "kind", where))
    if kind not in FARE_KINDS:
        raise ValueError(f"{where}:kind is {kind!r}, expected one of {', '.join(FARE_KINDS)}")

    categories = tuple(
        FareCategory(
            match=str(_require(rule, "match", f"{where}:categories")),
            id=str(_require(rule, "id", f"{where}:categories")),
            # A stand is both by default; only a source that distinguishes them
            # has to say so.
            pickup=bool(rule.get("pickup", True)),
            dropoff=bool(rule.get("dropoff", True)),
        )
        for rule in _require(body, "categories", where)
    )
    if not categories:
        raise ValueError(f"{where}:categories is empty")
    _check_categories_are_reachable(categories, where)

    return FareGroup(
        kind=kind,
        source=str(_require(body, "source", where)),
        crs=str(_require(body, "crs", where)),
        fields=_fields(body, where, _FARE_ROLES, optional=_FARE_OPTIONAL_ROLES),
        categories=categories,
    )


def _check_categories_are_reachable(categories: tuple[FareCategory, ...], where: str) -> None:
    """Refuse a rule an earlier one always shadows.

    Matching is first-hit-wins over substrings, so `"DF"` before `"PU/DF"`
    makes the second rule dead and files every pick-up point as drop-off only.
    That loads cleanly, produces a full `fares.json`, and is wrong — the
    failure mode this whole module is written to avoid.
    """
    for later, rule in enumerate(categories):
        for earlier in categories[:later]:
            if earlier.match.casefold() in rule.match.casefold():
                raise ValueError(
                    f"{where}:categories[{later}] matches {rule.match!r}, which contains the "
                    f"earlier {earlier.match!r} and can therefore never be reached. Order "
                    f"rules most specific first."
                )
