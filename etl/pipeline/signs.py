"""Published traffic signs, drawn as their own mesh (`P3-16`).

This is the sign half of the dTAD estate, landing in `Q58`/`Q59`'s pattern: one
primitive, one draw call, no collider, an optional `city.json` key, and counters
the stage publishes about itself. Two measurements taken before any of it was
written are the reason it does not look like the task `P3-16` originally
described, and both belong at the top of the file:

⚠️ **`DTAD_TS_ABV_PT` is not where a sign is.** The publisher's own fgdb
specification calls it *"Traffic sign **abbreviation** point"* and calls
`DTAD_TS_POLE_PT` *"Traffic sign pole point"*. Measured across this region:
**zero** of 3,276 abbreviation points sit on a pole; the nearest pole is p50
2.63 m away, p90 8.25 m, max 115.5 m; and the direction of that offset is
uncorrelated with `ANGLE` — 48% within 20 degrees of perpendicular, which is
what noise looks like. The abbreviation point is where a draughtsman put the
label so the drawing stayed legible. It says *which* sign; it does not say
where.

So the published point is read as **data and never as geometry** — `Q54`'s rule,
and the same move `arrows.py` makes when it registers a symbol into the lane the
ribbon actually has rather than drawing it at its published easting. The
difference is that an arrow's registration *moves* it and this one *replaces*
it: the pole is a surveyed object in its own right, so `pole_offset_m` is
published as the finding it is rather than as a shift this stage chose.

⚠️ **`GG_NAME` is the join, and it is the only one there is.** The specification
calls it *"Graphical group Name"*. It resolves 3,032 of the region's 3,276 signs
(92.6%) to exactly one pole, 24 to more than one, and leaves 220 with none.
Signs group 1 to 7 per `GG_NAME`, which is a pole carrying a stack of plates —
exactly the real object. The 244 that do not resolve to exactly one pole are
refused and counted, never dragged onto the nearest pole; `DTAD_TS_ABV_PT`
carries no other key, and nearest-pole would be a second join in `Q56`'s sense.

🔴 **`ANGLE` IS NOT A FACING, AND THE PUBLISHER SAYS SO.** The fgdb
specification's own row reads *"Angle (For carto-rep feature, same as **Ustn**
angle)"* — the MicroStation symbol-cell rotation of the drawing's label, not a
compass bearing for the sign. `DTAD_TS_ABV_PT` being an *abbreviation* layer
already implied it; the spec states it.

⚠️ **This was established before, in `hk-traffic-sign-map`, and reversed there at
some cost.** That project fed `ANGLE` to `icon-rotate`, found that **59% of
same-code signs within 30 m share an `ANGLE`** — so the two carriageways of a
divided road render identically — and reverted it (`fde0258`, reverted by
`42c343a`). Its `CLAUDE.md` carries the rule as an invariant. Re-measured here
before that was known, over this region and in the frame `arrows.py` validated
to p50 0.9 degrees: the angle sits **flat** against the road, p50 44.2 degrees
from the road axis, **19.2%** within 20 degrees of along it and **18.1%** within
20 degrees of across, against 22.2% for a uniform distribution. `TS115` NO ENTRY,
which must face its traffic, reads 19.0% and 19.5%. The pole layer's `ANGLE` is
the same (26.4%, 17.6%), and `DTAD_TS_PLATE_LINE` is not a plate outline but
83,880 cartographic ticks of median length **0.06 m**.

⚠️ **One reading of that measurement is wrong in a reproducible way.** Comparing
`ANGLE` against a road bearing taken as a *grid* angle rather than a game heading
appears to show 76.3% of plates lying square across the road, which is enough to
design a stage around. It is an artefact: Wan Chai's grid has a strong preferred
direction, so reflecting the angle variable moves a flat distribution onto
"across" and manufactures a mode. Recorded because it was believed for a while.

So `ANGLE` is read, published as `axis_residual_deg`, and **consumed by
nothing** — `arrows.py`'s `symbol_size` pattern, so the claim stays answerable
from a shipped artefact rather than from a scratch script (`Q37`).

🔴 **The whitelist refuses lettering on the NO-TEXTURE CONTRACT, not on `Q42`.**
An earlier draft of this module cited `Q42` and hard rule 8 for it and both
citations were wrong. Hard rule 8 is about the phrase "Crazy Taxi", a SEGA
trademark. `Q42`'s "never rendered text" is about the facade survey reading real
*company* marks — SHUI ON GROUP, REVENUE TOWER, FWD — and its reason is trademark
exposure. A traffic sign's 讓 is a government traffic-control glyph out of the
same TD index plan `arrows.py` transcribes its `RM` codes from, and no rule here
forbids it. What refuses it is the **no-texture contract**: `mesh_contract.gd` walks every
shader uniform and fails the bundle on any that holds a `Texture`, which
`road_markings.gdshader` records as the thing it deliberately did not amend. So
lettering would have to be geometry, and a 24-stroke character on a 0.68 m plate
seen from a moving car is a few pixels of smudge.

⚠️ **That contract is being amended, and 讓 is owed rather than refused** — see
`P3-20`, the sign texture atlas. This whitelist is the shape-faced subset that
ships before it lands, not the final scope of the layer.

⚠️ **What is derived, and where the rule comes from.** Identity and position are
read: the code from the publisher, the position from a surveyed pole. Only the
**facing** is derived — and the derivation is not new here. It is
`hk-traffic-sign-map`'s `compute-bearings.mjs`: take the road tangent at the
sign, and flip by 180 degrees according to which side of the line it falls, so
opposite carriageways come out opposed. That project reports ~76% coverage of
178k signs with it.

✅ **This pipeline can make that rule *absolute*, and that project could not.**
Its own comment records the limit — *"we don't know which way TD's marking
chainage runs along the road, so left versus right is arbitrary"* — leaving it
with the relative invariant only. Here the host is the road graph rather than a
marking line: `Snap.heading_deg` is a **directed** heading off
`TRAVEL_DIRECTION`, and the sign of `Snap.offset_m` is asserted against
`surface.mitres` itself in `tests/test_fares.py` rather than reasoned about. With
a directed edge and a known kerb, drive-on-left fixes the absolute facing rather
than a 180-degree pair. ⚠️ **It is still ungraded** — unlike
`boxjunctions.py`'s hatch angle there is no published subset to check it against.

⚠️ **Which is why the one-way diff is worth more than it was.** `P3-16` owes a
report-only diff of sign meaning against the graph's one-ways (`Q56`'s
second-source pattern). Since the facing comes from the kerb side and never from
the graph, that diff is an **independent check on the derivation** rather than a
tautology — it is the only one there is, and it is still a finding to go and
look at rather than a bar to retune.
"""

from __future__ import annotations

import argparse
import logging
import math
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from pipeline import gdb

# ⚠️ **Three imports from sibling stages rather than three copies.** `AT_GRADE`
# is the source's own encoding of "no structure" and is not config; `facing_away`
# asks whether winding agrees with the given normal, which is the question a
# *vertical* surface needs and `surface.downward_facing` cannot answer; and
# `ccw`, `axis_residual_deg` and `ArrowReport.measured` are the canonical
# statements of conventions this stage shares with the arrows.
from pipeline.arrows import (
    ArrowReport,
    Ribbon,
    axis_residual_deg,
    ccw,
    directed_residual_deg,
    nearside,
    ribbons,
)
from pipeline.config import (
    SIGN_ARROW_BENT_LEFT,
    SIGN_ARROW_BENT_RIGHT,
    SIGN_ARROW_DOUBLE,
    SIGN_ARROW_DOWN_LEFT,
    SIGN_ARROW_DOWN_RIGHT,
    SIGN_ARROW_LEFT,
    SIGN_ARROW_RIGHT,
    SIGN_ARROW_U,
    SIGN_ARROW_UP,
    SIGN_BACK_COLOUR,
    SIGN_BACKSLASH,
    SIGN_BAR,
    SIGN_BOARD_TALL,
    SIGN_BOARD_WIDE,
    SIGN_CHEVRONS,
    SIGN_DISC,
    SIGN_OCTAGON,
    SIGN_RANK_SUPPLEMENTARY,
    SIGN_RECT,
    SIGN_RECT_INFO,
    SIGN_RECT_WIDE,
    SIGN_SLASH,
    SIGN_TEE,
    SIGN_TEE_BAR,
    SIGN_TEXT,
    SIGN_TRIANGLE_DOWN,
    CityConfig,
    GameTransform,
    SignFace,
    Signs,
    load_city,
)
from pipeline.documents import read_document, write_document
from pipeline.fares import Segments, Snap
from pipeline.fetch import cached_source, source_reads
from pipeline.gltf import MeshData, Texture, write_glb
from pipeline.mesh import select_triangles
from pipeline.railings import AT_GRADE, facing_away
from pipeline.roads import ROADGRAPH_NAME, plan_lengths, read_graph
from pipeline.sign_text import TextAtlas, build_atlas
from pipeline.surface import SURFACE_MANIFEST_NAME, SURFACE_MANIFEST_SCHEMA

log = logging.getLogger(__name__)

SIGNS_NAME = "signs.glb"
SIGNS_MANIFEST_NAME = "signs.json"
# 2 since `Q70`: the manifest names `text_atlas`, the sign lettering's own PNG,
# because the atlas now ships *beside* `signs.glb` instead of inside it. The
# bump is what stops `export.py` reading a v1 document and publishing a
# `city.json` that names no atlas for a bundle that has one — which is the
# swept-file failure this whole change is about, one level up.
# 3 since `Q72`: `no_entry_with_flow` is gone and `no_entry_against_flow` is
# its inverse, joined by `plates_turned`. The rename is the point of the bump —
# a reader keeping the old key's meaning would read a 0 that now means the
# opposite thing, which is the silent wrong answer a schema version is for.
# 4 since `Q78`: `shift_m` changed population rather than name. It used to
# describe every post reaching registration, all of which moved; it now carries
# a real 0.0 for the posts left where they were surveyed, so a reader keeping
# the old interpretation would read the distribution as moves that all happened
# and would be **wrong about what it describes** — hard rule 5's test, met by a
# key whose bytes still parse. `posts_kept_as_surveyed` is the new key.
SIGNS_MANIFEST_SCHEMA = 4

# ⚠️ **No `-col` suffix**, the same call `arrows.glb` and `railings.glb` both
# make and for a reason this layer states more strongly than either: 728 poles
# is 728 collision bodies, and `P2-6` has not yet measured a frame on the device
# floor. A car passing through a sign post is the recorded cost. Breakaway poles
# are the genre's answer and they are an effect, so they belong in `B3`.
SIGNS_MESH_NAME = "signs"

# glTF material name, the contract channel `SURFACE_MATERIAL`, `TRAMWAY_MATERIAL`
# and `ARROWS_MATERIAL` all use: `tools/generated_scene_import.gd` maps this
# string onto `tuning/signs.tres` and nothing else.
SIGNS_MATERIAL = "signs"

# 🔴 **The lettering's own primitive, and it is separate for a reason that is
# not aesthetic** (`P3-20`, `Q65`). `mesh.py` refuses to merge a mesh that has
# UVs with one that does not, so putting `TEXCOORD_0` on the sign asset would
# cost all 36,616 of its vertices a channel — 292,928 B raw, ~143 KB of PCK —
# paid by 746 plates and 572 posts to serve the handful that carry words. Two
# primitives in one `.glb` keeps the untextured majority byte-identical and
# scopes the texture declaration to one surface, the shape `railings.glb`
# already ships three of. Cost: one draw call.
SIGNS_TEXT_MESH_NAME = "signs_text"
SIGNS_TEXT_MATERIAL = "signs_text"

# 🔴 **The atlas ships beside the `.glb`, not inside it, and Godot is the whole
# reason** (`Q70`). Embedded, the importer's `gltf/embedded_image_handling`
# default *extracts* it to `signs_0.png` in the same directory — a file
# `city.json` does not name, in a directory where the manifest names everything
# else, so `sync_generated.sh`'s stale sweep deleted it on every run and
# `verify_signs.gd` failed until someone forced a re-import by hand. Named here
# and shipped like any other asset, nothing is extracted and nothing is swept.
#
# ⚠️ **Not `signs_0.png`.** That is the name the importer would choose, and
# colliding with it would put this file back in the path of whatever wrote it.
SIGNS_TEXT_ATLAS_NAME = "signs_text.png"

# Below this, twice a triangle's area means it has collapsed. The bar
# `surface.py`, `tramway.py` and `arrows.py` all set.
_MIN_TWICE_AREA_M2 = 1e-6

# The prohibition bar's thickness as a fraction of a disc's diameter — on a disc
# `half_height_m` *is* the radius, so this coefficient is that fraction directly.
#
# ⚠️ **The one sign dimension here that is *measured* rather than authored.**
# Every other number in this layer carries `Q60`'s NOT-TO-SCALE debt, but a
# *proportion* survives a sheet with no scale, and TD prints one standard bar:
# `TS131` 0.097, `TS133` 0.097, `TS183` 0.098, read off the three cells' pixels.
# It shipped at **0.13** until 2026-08-23 — 34% too thick on every face that has
# one, which is what authoring a proportion by eye costs. `Q64`.
#
# ⚠️ **`SIGN_BAR` is measured too since `Q67`**, and this comment used to say the
# opposite — that its 0.22 stayed inline because it was authored where this is
# not. `sign_face_survey.py` measured it off the same cells: see
# `_NO_ENTRY_BAR_THICKNESS`.
_SLASH_THICKNESS = 0.097

# The white bar of a NO ENTRY plate, as a fraction of the disc's diameter — the
# same "on a disc `half_height_m` is the radius" identity `_SLASH_THICKNESS`
# uses, so this coefficient is the diameter fraction directly.
#
# ⚠️ **Measured, not authored** (`Q67`). `TS115`'s cell reads a bar **0.868** of
# the diameter long and **0.187** thick. This layer authored 0.66 by 0.22 — a
# quarter short and a sixth too thick — on the region's commonest sign by a wide
# margin, so it is the face the player sees wrong most often.
#
# 🔴 **The two bars are the same AREA to a tenth**, 0.145 against 0.162, and that
# is the finding rather than the numbers: a grader that compared area alone would
# have passed a visibly different bar. `sign_face_survey.py` grades extents for
# this reason, and this is the defect it was written against.
_NO_ENTRY_BAR_THICKNESS = 0.187


@dataclass
class SignReport:
    """What the stage read, joined, resolved and drew.

    ⚠️ **The counters are what can see this stage fail, because none of its
    failures look like anything in a frame** — `Q58`'s lesson, restated here
    because signs are worse than arrows for it. A NO ENTRY disc turned 180
    degrees is a perfectly drawn NO ENTRY disc. A sign on the wrong street is a
    perfectly drawn sign. A face table off by one code paints TURN LEFT
    everywhere and renders beautifully.

    The partitions:

        signs == not_whitelisted + on_structure + empty_geometry + candidates
        candidates == drawn + no_pole + ambiguous_pole + pole_too_far + too_far
                      + no_ribbon + over_shift + in_carriageway
                      + orphan_supplementary

    And a third, over the turn prohibitions alone:

        turn_sign_agreed + turn_sign_disagreed + turn_sign_unmatched
            == sum(by_code[code] for code in _TURN_PROHIBITIONS)
    """

    signs: int = 0
    not_whitelisted: int = 0
    on_structure: int = 0
    empty_geometry: int = 0
    candidates: int = 0

    drawn: int = 0
    no_pole: int = 0
    ambiguous_pole: int = 0
    # The sign's group named a pole, but too far away to be the same assembly.
    pole_too_far: int = 0
    too_far: int = 0
    # ⚠️ **These three are PLATES, like every other member of the partition** —
    # a post refuses all of its plates at once. The post-level counts are
    # `posts_over_shift` and `posts_in_carriageway` below.
    # Plates on posts whose move onto the drawn kerb exceeded `max_shift_m`.
    over_shift: int = 0
    # Plates on posts with no drawn ribbon on their host edge, so no kerb to
    # register to.
    no_ribbon: int = 0
    # 🔴 Plates on posts still standing in the drawn carriageway after
    # registration, where several widened ribbons overlap and no footway survives.
    in_carriageway: int = 0
    # 🔴 **Supplementary plates left with nothing to qualify.** A post whose only
    # surviving faces are `supplementary` rank draws none of them: the arrow says
    # which way the sign above it applies, and `Q65` put most of those signs out
    # of scope. ⚠️ **This one counts a decision this pipeline made, not a defect
    # in the source** — the assemblies are real and complete on the street, and
    # what is incomplete is the whitelist. So a *rise* here is the expected
    # consequence of narrowing scope, and a fall is what shipping more faces
    # looks like; neither is a bar. See `build_region`.
    orphan_supplementary: int = 0

    # ---- the lettering (`P3-20`) ----
    # 🔴 **Every one of these exists because a broken atlas renders as the plate
    # it was already rendering.** A cell cropped from empty paper bakes a blank
    # square; a quad wound backwards draws nothing; a texture that never arrives
    # samples white. None of the three is visible in a frame and none of them
    # moves `drawn`, `facing_away` or `triangles`. `Q58`'s rule, on an image.
    #
    # Plates that got a lettering quad. A face carrying a `text` layer that draws
    # zero of these is a face whose atlas cell went missing.
    text_plates: int = 0
    # Must be **0**: `signs_text.gdshader` is `cull_back` like its sibling, so
    # winding decides visibility and the normal attribute does not.
    text_facing_away: int = 0
    # What `mesh_contract.gd`'s declared budget is measured against, published so
    # `PROGRESS.md`'s `Texture memory` is a figure off a shipped artefact rather
    # than a claim (`Q37`).
    text_atlas_px: int = 0
    # The atlas file itself: what it is called, and how big it is on disk. Both
    # are new with `Q70`, which moved the image out of the `.glb`. ⚠️ **`bytes`
    # below no longer accounts for it** — it is `signs.glb`'s own size and the
    # atlas is not in there any more, so a bundle figure that used to be one
    # number is two.
    text_atlas_bytes: int = 0
    # 🔴 **The ink fraction of each baked cell, and the only thing that can see a
    # blank one.** A cell that crops the wrong region of the sheet bakes paper,
    # and a plate carrying a blank square on its face is the blank plate this
    # task set out to fix. Near zero here is that failure announcing itself.
    text_coverage: dict[str, float] = field(default_factory=dict)

    poles_drawn: int = 0
    # Published poles that were merged into another because they stand on the
    # same physical post. 🔴 The layer really does publish coincident poles.
    poles_merged: int = 0
    # Posts folded together *after* registration pushed them onto one point —
    # a different population from `poles_merged`, which is the publisher's own
    # coincident poles. See `_merge_placements`.
    posts_merged_after_shift: int = 0
    # ⚠️ **Post-level refusals, so `shift_m`'s `n` can be decomposed.**
    # `len(shift_m) == poles_drawn + posts_over_shift + posts_in_carriageway
    #  + posts_merged_after_shift` — without these a reader cannot tell whether
    # the excess over `poles_drawn` came from the bar or from somewhere else.
    posts_over_shift: int = 0
    posts_in_carriageway: int = 0
    # Posts left standing where TD surveyed them, because they were already clear
    # of the drawn kerb and `outset_m` and so the registration's reason did not
    # reach them (`Q78`). ⚠️ **They append a 0.0 to `shift_m` rather than being
    # skipped**, so the identity above still closes, and this is the only thing
    # that says how many of them there are. It is data-sensitive: it moves with
    # the survey and with `widen_default`, so unlike a config-and-code ratchet it
    # can be read rather than mutated.
    # ⚠️ **They are not the ONLY zeros in `shift_m`, so do not recover this
    # number by counting them.** The threshold is a strict `>`, so a post
    # surveyed *exactly* on `half_width_m + outset_m` takes the push branch and
    # its move is 0.0 as well. Two populations, one value — which is the same
    # confusion between a number and what it describes that `Q78` is about.
    posts_kept_as_surveyed: int = 0
    # ⚠️ **How far each post moved sideways onto the drawn kerb**, recorded over
    # every registered post **including the ones `max_shift_m` then refused**, so
    # `n` exceeding `poles_drawn` is the proof it can read outside its own bar
    # (`Q58`). This is the price of the decision at the top of this module, and
    # `Q60` is the precedent for publishing it rather than asserting it is small.
    # ⚠️ **It is the price over the posts that needed a registration, with a real
    # 0.0 for those that did not** (`Q78`), so it is no longer a distribution of
    # moves that all happened — read it with `posts_kept_as_surveyed`.
    # 🔴 **And it is an absolute value, which is exactly what hid `Q78`**: a
    # directional correction measured with `abs()` cannot report its own
    # direction. `railings.py` and `signals.py` compute theirs the same way.
    shift_m: list[float] = field(default_factory=list)
    # How far inside the drawn carriageway each post was surveyed. The
    # measurement that forced the registration: 0 means it was already outside.
    inside_ribbon_m: list[float] = field(default_factory=list)
    # Drawn plates by publisher code. Publishes the face table's *effect* rather
    # than the table: a code that silently stopped matching shows up here as a
    # row that draws nothing.
    by_code: dict[str, int] = field(default_factory=dict)

    # 🔴 **Published, unread — and its flatness is the whole point.** How far
    # each plate's `ANGLE` axis sits from its host edge's axis, in `[0, 90]`
    # where 0 is along the road and 90 is across it. Nothing consumes it,
    # because it carries no signal: see the module docstring for the three
    # measurements. It is republished on every run so that claim is answerable
    # from a shipped artefact rather than from a scratch script (`Q37`), and so
    # that a publisher who starts populating `ANGLE` properly shows up as this
    # distribution developing a mode. ⚠️ **Recorded over every candidate**, not
    # only the drawn ones — a distribution taken after a filter is confined to
    # that filter (`Q58`'s `drawn_gauge_m` trap).
    axis_residual_deg: list[float] = field(default_factory=list)
    # How far each drawn pole sat from the level-0 centreline it matched. What
    # `max_offset_m` is set against, published so the config comment is
    # checkable against a shipped artefact rather than a scratch script (`Q37`).
    offset_m: list[float] = field(default_factory=list)
    # ⚠️ **How far the sign moved from its published point onto its pole.** The
    # residue of the decision at the top of this module, and the number that
    # says how much of the placement the abbreviation point was never carrying.
    # Not a shift this stage chose: both endpoints are surveyed.
    pole_offset_m: list[float] = field(default_factory=list)

    # ⚠️ **Report-only, and never a bar.** A sign whose instruction contradicts
    # its edge is a finding about one of them — `Q56`'s second-source pattern,
    # the same shape `kerbside_source_audit.py` takes. These are counted and
    # drawn, because refusing them would be asserting the graph is right.
    no_entry_on_two_way: int = 0
    # 🔴 **Inverted by `Q72`, and the inversion is the finding.** This was
    # `no_entry_with_flow`, a self-check its own docstring called "a tautology by
    # design": `facing_from_side` turned every one-way sign to face the traffic,
    # so a NO ENTRY could never come out facing with the flow, and 0 was
    # unreachable proof that the rule had run. But **facing with the flow is the
    # correct state for a NO ENTRY** — it addresses the driver who would enter
    # against it — so 0 was success reported for exactly the configuration that
    # was wrong. It reads the other way now and must still be 0.
    no_entry_against_flow: int = 0
    # Plates turned 180 degrees off their own post because their face addresses
    # traffic coming the other way (`Q72`). The counter that makes `Q72`'s turn
    # visible in the manifest rather than only in a frame.
    #
    # ⚠️ **"The NO ENTRY family" means a different set here than in
    # `no_entry_against_flow` above.** This counts every face carrying
    # `faces_against_traffic` — `TS115` and `TS116` — where `_NO_ENTRY`, the
    # second-source axis, is `TS115` alone. `turned_plates_agree` asserts the
    # identity against `by_code` so it is computed rather than claimed.
    plates_turned: int = 0

    # 🔴 **The turn-restriction diff `Q62` named — and it does NOT grade the
    # facing, which is the finding.** Every drawn `TS131`/`TS132`/`TS133` against
    # the graph's 217 published banned movements, matched through the junction
    # the sign's own traffic reaches. It was built expecting a side flip to
    # collapse `agreed`; on this region it moved **29 to 30**, because
    # `facing_from_side` does not consult the side on a one-way host and
    # `turn_sign_on_one_way` is **62 of 68**. `Q62` stays open on the facing and
    # records this as the reason.
    #
    # ✅ **What it does grade is real and is not the facing**: whether the plate
    # standing here names the movement the graph bans at the junction ahead —
    # `Q64`'s failure class rather than `Q62`'s, and 14 live disagreements to go
    # and look at.
    #
    # ⚠️ **The three are different in strength and must not be summed.**
    # `agreed` and `disagreed` are the graded pair — the graph bans something at
    # this approach, and it either is or is not the movement the plate names.
    # `unmatched` is *not* a failure: the graph carries 34 left prohibitions
    # against 38 drawn `TS131`, so it plainly does not publish every signed one.
    #
    # ⚠️ **Report-only, never a bar**, for `Q56`'s reason and the one
    # `kerbside_source_audit.py` states about itself: a disagreement is a finding
    # about one of two sources and this stage has no standing to say which. It is
    # sharpened here by what the graph drops — `P1-3` reads `EXC_VEH_TYPE`,
    # `PART_TIME_REST` and `EFF_ALL_DAYS` and emits none of them, and one
    # restriction in this region excludes taxis, so a part-time restriction meets
    # a permanent plate as a disagreement between what two publishers chose to
    # say.
    #
    # 🔴 **How much of the population above can say anything about the kerb
    # side, inverted.** `facing_from_side` turns *both* kerbs of a one-way to
    # face its only traffic, so on a one-way host the facing never reads the
    # side and a mirrored city produces the identical match. This is the number
    # that says so — 62 of 68 here — and it is why the mirror moved `agreed` by
    # one plate rather than collapsing it.
    #
    # ⚠️ **Published because a second city is the business case** (hard rule 3):
    # a region whose prohibition signs stand on two-way streets would read this
    # low, and there the same diff *would* grade the side.
    turn_sign_on_one_way: int = 0
    turn_sign_agreed: int = 0
    turn_sign_disagreed: int = 0
    turn_sign_unmatched: int = 0
    # How far each prohibition plate stands from the junction it was matched to.
    # ⚠️ **Recorded over all three outcomes, and there is deliberately no bar on
    # it.** A bound would confine the distribution to itself — `Q58`'s
    # `drawn_gauge_m` trap — and this is the number that would say whether one is
    # worth having: edges run to 763 m, so a plate matched from the far end of
    # one is a match this cannot otherwise see.
    turn_sign_to_junction_m: list[float] = field(default_factory=list)

    # Triangles whose winding disagrees with the normal they were given.
    # ⚠️ **Must be 0.** `signs.gdshader` is `cull_back`, so winding decides
    # visibility: the tramway shipped 5,111 of 5,112 triangles facing the ground
    # with everything else correct, and the city simply had no tramway in it.
    facing_away: int = 0
    # 🔴 **How many boards had their glyphs mirrored to face the carriageway**,
    # over the boards that can be. The one derived orientation in the layer, so
    # it is published rather than assumed: a number at either extreme means the
    # kerb side stopped being read (`Q66`).
    #
    # ⚠️ Named for the *board*, not the chevron: `mirror_by_side` is a property
    # of the face, so a mirrored face that carries no chevrons would make a
    # `chevrons_` field a lie.
    boards_mirrorable: int = 0
    boards_mirrored: int = 0
    triangles: int = 0
    vertices: int = 0
    bytes: int = 0
    aabb: list[list[float]] = field(default_factory=list)

    # Reused rather than restated, the line `railings.py` and `boxjunctions.py`
    # both carry: p90/p99/max beside the median is `arrows.py`'s choice and its
    # reason — every distribution here is a residual whose **tail** is the
    # finding, and a median near zero is also what a wholly broken join looks
    # like.
    measured = staticmethod(ArrowReport.measured)


@dataclass(frozen=True)
class Sign:
    """One published sign, already joined to the pole that carries it.

    `x`/`z` are the **pole's** position in game plan space. `published_x`/`_z`
    are the abbreviation point's, kept only so `pole_offset_m` can be measured
    and published — nothing draws from them.
    """

    code: str
    group: str
    x: float
    z: float
    published_x: float
    published_z: float
    # `(90 - ANGLE)` as a game heading, converted once on the way in.
    # 🔴 **Read, published, and consumed by nothing.** It is the abbreviation
    # label's rotation on the drawing and it carries no relation to the street —
    # measured three ways in the module docstring. It survives only as
    # `axis_residual_deg`, so the claim stays checkable against a shipped
    # artefact.
    axis_deg: float


# --------------------------------------------------------------------------
# The read
# --------------------------------------------------------------------------


def read_signs(
    city: CityConfig,
    spec: Signs,
    region_id: str,
    transform: GameTransform,
    report: SignReport,
    *,
    sources_root: Path | None,
) -> list[Sign]:
    """Every whitelisted sign in the region, standing on the pole that carries it.

    Everything refused here is refused on what the *publisher* says — a code
    outside the face table, a sign on a structure, an empty geometry, a group
    that does not resolve to one pole — and each refusal is counted rather than
    logged, because the counts are what `Q58` says has to be able to see this
    stage fail.
    """
    reads = source_reads(city, spec, region_id, root=sources_root)
    bbox = city.projected_bounds(region_id).bbox

    signs: list[Sign] = []
    for path, member in reads:
        poles = _read_poles(path, member, city, spec, bbox, transform)

        layer = gdb.read_layer(
            path,
            spec.layer.layer,
            columns=spec.layer.columns,
            bbox=bbox,
            zip_member=member,
            expect_crs=city.projected_crs,
        )
        codes = layer.column(spec.layer.field("code"))
        bearings = layer.column(spec.layer.field("bearing"))
        levels = layer.column(spec.layer.field("level"))
        groups = layer.column(spec.layer.field("group"))
        owners, plan = gdb.points(layer)
        if len(owners) == 0:
            continue
        game_x, _, game_z = transform.to_game(plan[:, 0], plan[:, 1])

        for row, owner in enumerate(owners):
            report.signs += 1
            code = str(codes[owner])
            if code not in spec.faces:
                # The whitelist doing its work. ~2,360 of the region's signs land
                # here, and that is the decision rather than a shortfall: their
                # meaning is their text (the no-texture contract, `mesh_contract.gd`).
                report.not_whitelisted += 1
                continue
            if str(levels[owner]).strip().lower() not in AT_GRADE:
                # On a structure. `Q13` keeps the elevated network closed to
                # driving, so the sign is unreachable and the nearest level-0
                # edge to it is the street underneath.
                report.on_structure += 1
                continue
            published_x = float(game_x[row])
            published_z = float(game_z[row])
            bearing = float(bearings[owner]) if bearings[owner] is not None else float("nan")
            if not (math.isfinite(published_x) and math.isfinite(published_z)):
                # `POINT EMPTY` is spelled NaN in WKB and `gdb.points` passes it
                # through by design. Refused here, where the meaning is known.
                report.empty_geometry += 1
                continue
            # ⚠️ **A null `ANGLE` is not a refusal**, and that is a consequence of
            # the finding above rather than a leniency. `ANGLE` is null on 171 of
            # the region's signs, 80 of them whitelisted — and since nothing
            # consumes it, refusing those would be discarding 80 perfectly
            # locatable signs over a field the stage does not use.

            report.candidates += 1
            group = str(groups[owner] or "")
            carrying = poles.get(group, ())
            if not carrying:
                report.no_pole += 1
                continue
            if len(carrying) > 1:
                # ⚠️ Refused rather than resolved by distance. Nearest-pole would
                # be a second join with no memory of the group, and `Q56`'s rule
                # is that two implementations disagreeing tells you one is wrong
                # and never which.
                report.ambiguous_pole += 1
                continue

            pole_x, pole_z = carrying[0]
            span_m = math.hypot(pole_x - published_x, pole_z - published_z)
            if span_m > spec.max_pole_span_m:
                # ⚠️ **`GG_NAME` is reused across signs kilometres apart** — the
                # hazard `hk-traffic-sign-map` caps at the same 15 m. Refused
                # rather than drawn, because a sign teleported onto a pole two
                # streets away is a perfectly drawn sign on the wrong road.
                report.pole_too_far += 1
                continue
            signs.append(
                Sign(
                    code=code,
                    group=group,
                    x=pole_x,
                    z=pole_z,
                    published_x=published_x,
                    published_z=published_z,
                    axis_deg=(90.0 - bearing) % 360.0,
                )
            )
    return signs


def _read_poles(
    path: Path,
    member: str | None,
    city: CityConfig,
    spec: Signs,
    bbox: tuple[float, float, float, float],
    transform: GameTransform,
) -> dict[str, list[tuple[float, float]]]:
    """Every at-grade pole in the region, keyed by its graphical group.

    A group with more than one pole is kept as a list rather than collapsed: the
    caller refuses it, and collapsing here would hide how often it happens.
    """
    layer = gdb.read_layer(
        path,
        spec.poles.layer,
        columns=spec.poles.columns,
        bbox=bbox,
        zip_member=member,
        expect_crs=city.projected_crs,
    )
    groups = layer.column(spec.poles.field("group"))
    levels = layer.column(spec.poles.field("level"))
    owners, plan = gdb.points(layer)
    if len(owners) == 0:
        return {}
    game_x, _, game_z = transform.to_game(plan[:, 0], plan[:, 1])

    carried: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for row, owner in enumerate(owners):
        group = str(groups[owner] or "")
        if not group:
            continue
        if str(levels[owner]).strip().lower() not in AT_GRADE:
            continue
        x, z = float(game_x[row]), float(game_z[row])
        if not (math.isfinite(x) and math.isfinite(z)):
            continue
        carried[group].append((x, z))
    return dict(carried)


# --------------------------------------------------------------------------
# The face
# --------------------------------------------------------------------------
#
# Every shape below is returned as convex polygons in the plate's own frame:
# `(u, v)` in metres, `+u` to the **viewer's** right and `+v` up. Polygons are
# wound counter-clockwise in that frame, which `_place` maps to a normal along
# the plate's outward direction — see `plate_frame` for why that holds.


# Every rectangular plate is just its two authored lengths, and `plate_extent_m`
# and `layer_polygons` both need the same set. A table rather than two parallel
# chains — `_ARROW_TURNS` is the file's own precedent — because the two sites had
# already drifted apart once by the time `P3-22` added three plates to both.
#
# ⚠️ **`disc` and `triangle_down` are deliberately NOT here**: each *derives* a
# width from one authored number rather than reading two, so a lookup would have
# to lie about what is authored.
_PLATE_RECTS: dict[str, Callable[[Signs], tuple[float, float]]] = {
    SIGN_RECT: lambda spec: (spec.rect_width_m, spec.rect_height_m),
    SIGN_RECT_WIDE: lambda spec: (spec.rect_wide_width_m, spec.rect_wide_height_m),
    SIGN_RECT_INFO: lambda spec: (spec.rect_info_width_m, spec.rect_info_height_m),
    SIGN_BOARD_WIDE: lambda spec: (spec.board_wide_width_m, spec.board_wide_height_m),
    SIGN_BOARD_TALL: lambda spec: (spec.board_tall_width_m, spec.board_tall_height_m),
}


def plate_extent_m(spec: Signs, plate: str) -> tuple[float, float]:
    """Half-width and half-height of one plate outline, in metres.

    ⚠️ Every number this reads is **authored**. The TS index sheets are stamped
    "NOT TO SCALE" and refer dimensions out to working drawings the published
    `dataspec` bundle does not contain, so there is nothing to transcribe. This
    is the debt `Q60` recorded for railing height, restated.
    """
    if plate == SIGN_DISC:
        radius = 0.5 * spec.disc_diameter_m
        return radius, radius
    if plate == SIGN_TRIANGLE_DOWN:
        # An equilateral triangle standing on its point: the width that goes with
        # a given height, so one authored number sizes it.
        half_height = 0.5 * spec.triangle_height_m
        return half_height / math.sqrt(3.0) * 2.0, half_height
    if plate == SIGN_OCTAGON:
        # A regular octagon is as wide as it is tall, so `octagon_height_m` —
        # measured across the flats, which is how a STOP plate is specified —
        # gives both extents. ⚠️ **That squareness is checkable against the
        # publisher**: `Q68`'s corrected plate box reads TD's own `TS101` cell at
        # 269 x 269 px, which is why the box correction had to land first.
        half = 0.5 * spec.octagon_height_m
        return half, half
    if plate in _PLATE_RECTS:
        width_m, height_m = _PLATE_RECTS[plate](spec)
        return 0.5 * width_m, 0.5 * height_m
    raise ValueError(f"no extent for plate {plate!r}")


def layer_polygons(
    spec: Signs, draw: str, size: float, half_width_m: float, half_height_m: float
) -> list[np.ndarray]:
    """One face layer as convex polygons in the plate frame.

    `size` is a fraction of the plate's own extent, so a 600 mm disc and a 900 mm
    disc scale together — `ArrowGlyph.length_m`'s reason for keeping proportions
    off absolute numbers.
    """
    half_w = size * half_width_m
    half_h = size * half_height_m

    if draw == SIGN_DISC:
        return [disc(min(half_w, half_h), spec.disc_segments)]
    if draw == SIGN_BAR:
        # The white bar of a NO ENTRY plate. Its height is a proportion of the
        # plate rather than of `size`, so widening the bar does not thicken it.
        return [_rect(half_w, _NO_ENTRY_BAR_THICKNESS * half_height_m)]
    if draw in _PLATE_RECTS:
        return [_rect(half_w, half_h)]
    if draw == SIGN_TRIANGLE_DOWN:
        return [ccw([(-half_w, half_h), (half_w, half_h), (0.0, -half_h)])]
    if draw == SIGN_OCTAGON:
        return [_octagon(min(half_w, half_h))]
    if draw in (SIGN_SLASH, SIGN_BACKSLASH):
        # The prohibition bar at 45 degrees: `slash` upper-left to lower-right,
        # `backslash` mirrored. Thickness is `_SLASH_THICKNESS` of the diameter —
        # see the constant for why that number and not another.
        #
        # ⚠️ **`backslash` exists so a saltire is authored as TWO LAYERS** rather
        # than as one `cross` word returning both bars. A word returning two
        # polygons draws them at one `layer_lift_m`, so they would be coplanar
        # where they cross, and the config's record of the 4 mm NO ENTRY bar says
        # what coplanar layers on a sign plate look like. Two layers get two
        # lifts and the question does not arise.
        #
        # ⚠️ **Defined for square-extent plates only.** Every face using either
        # word is a `disc`, where `min()` is a no-op — but on a `rect_wide` a bar
        # has to *span*, and both numbers here would be wrong: `min()` confines
        # it to the inscribed square, and the plate's diagonal is
        # `atan2(half_h, half_w)` rather than 45 degrees. Nothing validates a
        # draw word against a plate, so a config could reach this.
        bar = _rect(min(half_w, half_h), _SLASH_THICKNESS * half_height_m)
        return _rotate([bar], -45.0 if draw == SIGN_SLASH else 45.0)
    if draw == SIGN_CHEVRONS:
        return _chevrons(half_w, half_h)
    if draw == SIGN_TEE:
        return _tee(half_w, half_h)
    if draw == SIGN_TEE_BAR:
        return _tee_bar(half_w, half_h)
    if draw == SIGN_ARROW_DOUBLE:
        return _arrow_double(half_w, half_h)
    if draw in _ARROW_TURNS:
        turn = _ARROW_TURNS[draw]
        # ⚠️ **A rotated arrow runs along the plate's *other* axis**, so the box
        # it is sized in has to be transposed with it. Sizing every glyph inside
        # `min(half_w, half_h)` confines it to the plate's square, which is
        # invisible on a disc and guts the wide ones: on a 0.60 x 0.25 m `TS733`
        # arrow plate it drew a **0.18 m** arrow with 0.21 m of white either
        # side. Diagonals keep the square, which is what they want.
        reach, cross = (half_h, half_w) if turn % 180.0 == 0.0 else (half_w, half_h)
        if turn % 90.0 != 0.0:
            reach = cross = min(half_w, half_h)
        return _rotate(_straight_arrow(reach, cross), turn)
    if draw in (SIGN_ARROW_BENT_LEFT, SIGN_ARROW_BENT_RIGHT):
        return _bent_arrow(half_w, half_h, -1.0 if draw == SIGN_ARROW_BENT_LEFT else 1.0)
    if draw == SIGN_ARROW_U:
        return _u_turn_arrow(half_w, half_h)
    if draw == SIGN_TEXT:
        # 🔴 **`text` has no polygons and must never quietly get some.** It is a
        # textured quad placed from `sign_text.TextCell.plate_rect`, and the only
        # code that may draw it is `_draw_plate`. Returning the plate outline
        # here — the obvious "reasonable default" — would paint a blank white
        # rectangle over the face and render as the wordless plate this whole
        # task exists to replace.
        raise ValueError(
            "sign layer 'text' is drawn from the atlas by _draw_plate, not from polygons"
        )
    raise ValueError(f"no geometry for sign layer {draw!r}")


# How far each straight arrow is turned from pointing up. `KEEP LEFT` and `KEEP
# RIGHT` are the diagonals; the index sheet draws them at 45 degrees below the
# horizontal, pointing down and out.
_ARROW_TURNS = {
    SIGN_ARROW_UP: 0.0,
    SIGN_ARROW_LEFT: 90.0,
    SIGN_ARROW_RIGHT: -90.0,
    SIGN_ARROW_DOWN_LEFT: 135.0,
    SIGN_ARROW_DOWN_RIGHT: -135.0,
}


def _straight_arrow(reach: float, cross: float) -> list[np.ndarray]:
    """A plain arrow pointing `+v`, `reach` long and at most `cross` half-wide.

    ⚠️ **Two lengths, not a box.** `reach` runs along the arrow and `cross`
    limits it across, so a glyph rotated onto a wide plate can use the plate's
    long axis. On a square plate the two are equal and the head is the 0.52 of
    `reach` it has always been, so discs are untouched.
    """
    stem_half = 0.20 * reach
    head_half = min(0.52 * reach, cross)
    head_base = reach - 1.05 * head_half
    return [
        _rect_between(-stem_half, stem_half, -reach, head_base),
        ccw([(-head_half, head_base), (head_half, head_base), (0.0, reach)]),
    ]


def _chevrons(half_w: float, half_h: float) -> list[np.ndarray]:
    """A deviation board's chevrons, pointing `-u`, filling the plate.

    ⚠️ **The count is derived from the plate's own aspect, not authored.** TD
    draws `TS414` with three solid chevrons and two outlined ones — the outline
    is the sheet saying "repeat as required" — so a chevron count is a property
    of how wide the board is rather than a number to transcribe. One chevron per
    plate-height of width, at least one, which gives `TS414`'s wide board three
    and `TS589`'s portrait board one, matching both cells.

    🔴 **Which way they point is NOT published, and the caller decides.** These
    are built pointing `-u` and `_draw_plate` mirrors them per instance — see
    `SignFace.mirror_by_side` and `Q66`. TD publishes no left/right code pair for a
    deviation board the way it does for `TS615`/`TS616`/`TS617`, so the sheet's
    drawing is indicative and the installed board is oriented physically.
    """
    span = 2.0 * half_h
    count = max(1, round(2.0 * half_w / span))
    pitch = 2.0 * half_w / count
    # Half the pitch is the barb's reach along `u`; the notch is what makes a
    # chevron read as an arrowhead rather than a triangle.
    barb = 0.62 * pitch
    notch = 0.30 * pitch
    # ⚠️ **Centred, because the row is narrower than the plate.** The drawn
    # extent is `(count - 1) * pitch + barb + notch`, which is short of the
    # board by `0.08 * pitch`; laying the first tip on the left edge put all of
    # that slack on the right and threw `TS589`'s single chevron 8% of the board
    # off-centre — small, visible, and invisible to every counter.
    out: list[np.ndarray] = []
    first = -0.5 * ((count - 1) * pitch + barb + notch)
    for index in range(count):
        tip = first + index * pitch
        # ⚠️ **Two quads, not one six-point outline, because a chevron is
        # CONCAVE.** `_Builder.polygon` fans from vertex 0 and says it takes a
        # convex polygon; fanning the notched outline emits triangles outside
        # the shape, half of them wound backwards. It cost `facing_away` **21**
        # on the first build — loudly, which is the one mercy: `signs.gdshader`
        # is `cull_back`, so the bad half would have gone missing rather than
        # drawn wrong. `_tee` splits for the same reason.
        for rise in (half_h, -half_h):
            out.append(
                ccw(
                    [
                        (tip, 0.0),
                        (tip + notch, 0.0),
                        (tip + barb + notch, rise),
                        (tip + barb, rise),
                    ]
                )
            )
    return out


# The T's crossbar, shared by `_tee` and the red bar `_tee_bar` lays over it.
# ⚠️ **Held here because the two were coupled only by coincidence**: the bar was
# inset against numbers `_tee` owned privately, so a nudge to the T would have
# left a red bar floating on white and nothing would have said so.
_TEE_BAR_HALF = 0.42
_TEE_BAR_BOTTOM = 0.34
_TEE_BAR_TOP = 0.66


def _tee(half_w: float, half_h: float) -> list[np.ndarray]:
    """The T of a NO THROUGH ROAD plate: a stem rising into a crossbar.

    Returned as two rectangles rather than one outline because the pipeline's
    builder fans convex polygons, and a T is not convex.
    """
    stem_half = 0.11 * half_w
    stem_bottom = -0.74 * half_h
    bar_half = _TEE_BAR_HALF * half_w
    bar_bottom = _TEE_BAR_BOTTOM * half_h
    bar_top = _TEE_BAR_TOP * half_h
    return [
        _rect_between(-stem_half, stem_half, stem_bottom, bar_bottom),
        _rect_between(-bar_half, bar_half, bar_bottom, bar_top),
    ]


def _tee_bar(half_w: float, half_h: float) -> list[np.ndarray]:
    """The red bar a NO THROUGH ROAD plate lays over the T's crossbar.

    Inset inside `_tee`'s crossbar on every side, so the white reads as a border
    around it exactly as the cell draws it — which is also why this is its own
    word: it is a second colour at a position no centred layer can reach.
    """
    inset_u = 0.80 * _TEE_BAR_HALF * half_w
    inset_v = 0.06 * half_h
    return [
        _rect_between(
            -inset_u,
            inset_u,
            _TEE_BAR_BOTTOM * half_h + inset_v,
            _TEE_BAR_TOP * half_h - inset_v,
        )
    ]


def _arrow_double(half_w: float, half_h: float) -> list[np.ndarray]:
    """`TS735`'s two arrows, pointing out from a shared gap at the centre.

    Built from two `_straight_arrow` glyphs rather than one bar with two heads,
    so the head proportions stay the ones every other arrow plate on the post
    uses and a stack reads as one family.
    """
    # ⚠️ **The gap is real and was missing.** `reach = 0.5 * half_w` put both
    # stem tails at exactly `u = 0`, so the two arrows abutted and drew as one
    # bar with two heads — which is what this docstring claimed it deliberately
    # was not. Found in review by measuring the shipped layer, not by looking.
    gap = 0.12 * half_w
    # ⚠️ `_straight_arrow` spans **±reach**, so an arrow occupying `gap..half_w`
    # is half that long. Setting `reach = half_w - gap` ran both arrows clean off
    # the plate, which the flat render showed instantly and no counter could.
    reach = 0.5 * (half_w - gap)
    cross = 0.62 * half_h
    out: list[np.ndarray] = []
    for turn, shift in ((-90.0, gap + reach), (90.0, -(gap + reach))):
        for polygon in _rotate(_straight_arrow(reach, cross), turn):
            moved = polygon.copy()
            moved[:, 0] += shift
            out.append(moved)
    return out


def _bent_arrow(half_w: float, half_h: float, side: float) -> list[np.ndarray]:
    """An arrow rising then turning to `side` (`-1` left, `+1` right).

    The TURN LEFT AHEAD / NO LEFT TURN shape: a stem up from the bottom of the
    plate, an elbow, and a head pointing across. Drawn from the same proportions
    as `_straight_arrow` so the two read as one family.
    """
    reach = min(half_w, half_h)
    stem_half = 0.20 * reach
    head_half = 0.46 * reach
    elbow = 0.15 * reach
    tip = side * reach
    head_base = tip - side * 1.05 * head_half
    return [
        _rect_between(-stem_half, stem_half, -reach, elbow + stem_half),
        _rect_between(
            min(0.0, head_base), max(0.0, head_base), elbow - stem_half, elbow + stem_half
        ),
        ccw(
            [
                (head_base, elbow - head_half),
                (head_base, elbow + head_half),
                (tip, elbow),
            ]
        ),
    ]


def _u_turn_arrow(half_w: float, half_h: float) -> list[np.ndarray]:
    """The NO U-TURNS glyph: up one side, over the top, and back down into a head.

    The top is a squared arch rather than a drawn semicircle. At 600 mm across,
    seen from a car, the two are the same picture and one of them is a ring of
    triangles per sign on 22 signs.
    """
    reach = min(half_w, half_h)
    stem_half = 0.16 * reach
    span = 0.52 * reach
    head_half = 0.40 * reach
    top = reach - stem_half
    head_tip = -reach
    head_base = head_tip + 1.05 * head_half
    return [
        _rect_between(-span - stem_half, -span + stem_half, -0.35 * reach, top + stem_half),
        _rect_between(-span - stem_half, span + stem_half, top - stem_half, top + stem_half),
        _rect_between(span - stem_half, span + stem_half, head_base, top + stem_half),
        ccw(
            [
                (span - head_half, head_base),
                (span + head_half, head_base),
                (span, head_tip),
            ]
        ),
    ]


def disc(radius: float, segments: int) -> np.ndarray:
    """A closed ring of `segments` points, counter-clockwise in `(u, v)`.

    ⚠️ **Public since `P3-17`, on `arrows.nearside`'s terms**: a second consumer
    is what makes a helper public here rather than copied. `pipeline/signals.py`
    draws its lenses and its post from this, and a second generator would be a
    second phase convention — see `_octagon` below for what that costs.
    """
    angles = np.linspace(0.0, 2.0 * math.pi, segments, endpoint=False)
    return np.column_stack([radius * np.cos(angles), radius * np.sin(angles)])


def _octagon(half: float) -> np.ndarray:
    """A regular octagon `2 * half` across the flats, flat side up.

    ⚠️ **Offset half a step, and that is the whole shape.** Vertices at
    `k * 45` degrees give a corner at the top and read as a rotated square from
    a car; a STOP plate has a *flat* top, a flat bottom and flat sides with the
    corners cut off. So the vertices sit at `22.5 + k * 45`, and the radius is
    the circumscribed one that puts each flat at `half`.

    ⚠️ **`disc(half, 8)` is the trap** — the segment count is right and the
    phase is not, and the two differ by a 22.5 degree turn that renders
    perfectly as the wrong sign. So it is `disc` *turned*, which says that in
    the code rather than only in this paragraph, and keeps one generator.
    """
    return _rotate([disc(half / math.cos(math.radians(22.5)), 8)], 22.5)[0]


def _rect(half_w: float, half_h: float) -> np.ndarray:
    return _rect_between(-half_w, half_w, -half_h, half_h)


def _rect_between(u0: float, u1: float, v0: float, v1: float) -> np.ndarray:
    return ccw([(u0, v0), (u1, v0), (u1, v1), (u0, v1)])


def _rotate(polygons: list[np.ndarray], degrees: float) -> list[np.ndarray]:
    """Every polygon turned about the plate's centre. Winding is preserved."""
    angle = math.radians(degrees)
    cos, sin = math.cos(angle), math.sin(angle)
    turn = np.array([[cos, sin], [-sin, cos]])
    return [polygon @ turn for polygon in polygons]


# --------------------------------------------------------------------------
# Placing it in the world
# --------------------------------------------------------------------------


def plate_frame(facing_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """The plate's outward normal and its `+u` axis, for a facing heading.

    ⚠️ **Public since `P3-17`**, on `arrows.nearside`'s terms — `pipeline/
    signals.py` frames its heads with it. The winding guarantee below is the
    reason it must not be written a second time.

    Headings are clockwise from north and north is `-Z`, so a plate facing
    `facing_deg` has outward normal `n = (sin f, 0, -cos f)`. `+u` is the right
    hand of somebody **looking at** the sign, which is `cross(-n, up)` —
    `(-cos f, 0, -sin f)`, the negation of the road frame's own right.

    ⚠️ **The sign of `u` is what makes a TURN LEFT disc point left**, and it is
    the one thing here that renders perfectly when wrong: a mirrored plate is a
    plausible sign that instructs the opposite. `tests/test_signs.py` pins it
    against a camera placed in front of a known face rather than against this
    comment.

    The pair also fixes the winding: `u x up == n`, so a polygon wound
    counter-clockwise in `(u, v)` comes out with its normal along `+n`.
    """
    facing = math.radians(facing_deg)
    normal = np.array([math.sin(facing), 0.0, -math.cos(facing)])
    right = np.array([-math.cos(facing), 0.0, -math.sin(facing)])
    return normal, right


def facing_from_side(snap_heading_deg: float, side: float, one_way: bool) -> float:
    """Which way a sign on this kerb faces, in game headings.

    🔴 **Public since `P3-17`, and this is the one that most needed it.**
    `pipeline/signals.py` derives a signal head's facing from exactly this rule,
    because a head addresses the traffic approaching its stop line — the traffic
    already legally proceeding, which is the case a regulatory plate is in. A
    second copy of this function is a second city, mirrored, and nothing in
    either would render as wrong (`Q56`).

    ⚠️ **Derived, because nothing publishes it** — the module docstring carries
    the publisher's own wording and the prior art. This is
    `hk-traffic-sign-map`'s `compute-bearings.mjs` rule with a better host: road
    tangent, flipped by which side of it the sign falls on.

    A sign addresses the traffic that passes it, and `side` is positive on the
    **nearside**. ⚠️ **It is the side the post was actually placed on, not
    `Snap.offset_m` directly** — the two disagree at `-0.0`, which
    `Segments.nearest` returns for a point on the centreline, and the post would
    then be placed one side and turned to face the other.

    On a two-way edge each kerb serves a different direction: traffic running
    along the edge keeps the nearside on its left under drive-on-left, so a
    nearside sign faces back along the edge and an offside sign faces along it.

    ⚠️ **A one-way edge is not that case, and getting it wrong was measurable.**
    Both its kerbs serve the *same* traffic, so both signs face back along the
    edge. Without this branch the offside signs came out reversed, and the NO
    ENTRY diff below caught it: **117 of 253** NO ENTRY plates faced with their
    own one-way flow, which is the coin-toss a broken rule produces. It is the
    one place the graph's direction is allowed to decide a facing, and it costs
    what `_record_semantics` records.

    ⚠️ **Drive-on-left is the one traffic-code fact hard-coded here**, and a
    right-hand-drive city needs this function changed rather than a number
    tuned. It is not config because it is not a preference: it decides which of
    two opposite instructions the city asserts, and a city file quietly carrying
    the wrong one would render perfectly.

    ✅ The result is an **absolute** facing rather than `compute-bearings.mjs`'s
    relative one, because `Snap.heading_deg` is directed off `TRAVEL_DIRECTION`
    where a marking line's chainage direction is unknown.

    🔴 **This is the facing of the POST, which is the facing of every plate that
    addresses the traffic already legally there — and that is not all of them.**
    A NO ENTRY addresses a driver who would come in the wrong way and faces the
    opposite direction; `_plate_facing_deg` turns it. Before `Q72` there was no
    such step, so a post's NO ENTRY was drawn staring back down a road the
    traffic was legally on. See `SignFace.faces_against_traffic`.
    """
    if one_way or side > 0.0:
        return (snap_heading_deg + 180.0) % 360.0
    return snap_heading_deg % 360.0


def _plate_facing_deg(post_facing_deg: float, face: SignFace) -> float:
    """Which way this particular plate faces on a post that faces `post_facing_deg`.

    🔴 **The one place a facing is a property of the plate rather than the pole**
    (`Q72`). `facing_from_side` derives where the *post* looks — at the traffic
    it addresses — and almost every face agrees with it. A NO ENTRY does not: it
    stands at the mouth a driver must not enter by, so it addresses traffic
    coming the other way and is turned 180 degrees from its own post.

    ⚠️ **Without this, back-to-back plates are unrepresentable**, which was the
    defect: 82 of the region's 499 posts carry a NO ENTRY beside a GIVE WAY, a
    mandatory movement disc or a ONE WAY plate, and on the street those face
    opposite ways. Drawn from the pole alone all 84 NO ENTRY plates on those
    posts faced the wrong traffic, and every one of them rendered perfectly.

    ⚠️ **Applied whatever the host's direction, including a two-way one.** The
    class of the sign is what decides this, not the graph — a NO ENTRY on a
    street the graph calls two-way is `no_entry_on_two_way`'s second-source
    disagreement (`Q56`), a finding to go and look at, and it is not this
    function's business to resolve it by declining to turn the plate.
    """
    if not face.faces_against_traffic:
        return post_facing_deg
    return (post_facing_deg + 180.0) % 360.0


def expected_turned(spec: Signs, report: SignReport) -> int:
    """Drawn plates whose face is turned, counted from `by_code` (`Q72`).

    The other half of `plates_turned`'s identity, derived from a different
    tally so the two can disagree. Public because `test_signs.py` asserts it
    against a built report as well.
    """
    return sum(
        count for code, count in report.by_code.items() if spec.faces[code].faces_against_traffic
    )


def turned_plates_agree(spec: Signs, report: SignReport) -> bool:
    """Whether `plates_turned` and `by_code` tell the same story."""
    return report.plates_turned == expected_turned(spec, report)


class _Builder:
    """Accumulates flat convex polygons, each with its own colour and normal.

    Two things separate this from `arrows.py`'s builder, and both come from the
    plate being **vertical and coloured** where an arrow is horizontal and one
    paint:

    - ⚠️ **`COLOR_0` ships, and it is read.** A plate is up to four colours and
      the whole layer is one draw call, so the colour has to travel on the
      vertex; `signs.gdshader` takes it straight to `ALBEDO`. `arrows.py` records
      the opposite decision for the opposite reason, and `Q54`'s bar is the same
      in both directions: a channel earns its place when something reads it.
    - **The normal is per polygon**, because a sign faces sideways and every
      plate faces a different sideways. `arrows.py` can tile one up-vector
      because every arrow is on the ground.
    """

    def __init__(self) -> None:
        self._positions: list[np.ndarray] = []
        self._normals: list[np.ndarray] = []
        self._colours: list[np.ndarray] = []
        self._triangles: list[np.ndarray] = []
        self._count = 0

    def polygon(self, points: np.ndarray, normal: np.ndarray, colour: tuple[int, int, int]) -> None:
        """One convex polygon in world space, already wound to face `normal`."""
        span = len(points)
        if span < 3:
            return
        base = self._count
        fan = np.arange(1, span - 1)
        self._triangles.append(
            np.column_stack([np.zeros(len(fan), dtype=np.int64), fan, fan + 1]) + base
        )
        self._positions.append(points)
        self._normals.append(np.tile(normal.astype(np.float32), (span, 1)))
        self._colours.append(np.tile(np.array([*colour, 255], dtype=np.uint8), (span, 1)))
        self._count += span

    def build(self, name: str) -> MeshData | None:
        if not self._triangles:
            return None
        mesh = MeshData(
            name=name,
            positions=np.vstack(self._positions),
            normals=np.vstack(self._normals),
            triangles=np.vstack(self._triangles).astype(np.uint32),
            colours=np.vstack(self._colours),
            material=SIGNS_MATERIAL,
        )
        twice_area = np.linalg.norm(mesh.triangle_cross(), axis=1)
        return select_triangles(mesh, twice_area > _MIN_TWICE_AREA_M2)


class _TextBuilder:
    """Accumulates the lettering quads: positions, normals, UVs, one colour.

    ⚠️ **A second builder rather than a flag on the first**, because the two
    meshes have different vertex layouts and `mesh.py` will not merge them. The
    split is the whole reason the atlas costs 143 KB less than it might — see
    `SIGNS_TEXT_MESH_NAME`.

    ⚠️ **It ships `COLOR_0` too, and the colour is white.** The atlas already
    carries the glyph's colour baked over the plate's field, so nothing needs a
    tint — but `check_surface` demands vertex colour on this bundle's meshes by
    default, and a surface that opts out has to say so at its call site. White is
    the identity under the shader's multiply, so the channel is honest rather
    than decorative: turn the texture off and the quad is the field colour it
    sits on, which is the failure mode `Q63` wanted visible.
    """

    def __init__(self) -> None:
        self._positions: list[np.ndarray] = []
        self._normals: list[np.ndarray] = []
        self._uvs: list[np.ndarray] = []
        self._triangles: list[np.ndarray] = []
        self._count = 0

    def quad(self, corners: np.ndarray, normal: np.ndarray, uvs: np.ndarray) -> None:
        """One four-corner quad, wound to face `normal`, with `uvs` to match."""
        base = self._count
        self._triangles.append(np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64) + base)
        self._positions.append(corners)
        self._normals.append(np.tile(normal.astype(np.float32), (4, 1)))
        self._uvs.append(uvs.astype(np.float32))
        self._count += 4

    def build(self, name: str, atlas: TextAtlas) -> MeshData | None:
        if not self._triangles:
            return None
        count = self._count
        mesh = MeshData(
            name=name,
            positions=np.vstack(self._positions),
            normals=np.vstack(self._normals),
            triangles=np.vstack(self._triangles).astype(np.uint32),
            colours=np.tile(np.array([255, 255, 255, 255], dtype=np.uint8), (count, 1)),
            uvs=np.vstack(self._uvs),
            # ⚠️ **`uri` set, so the atlas ships beside the `.glb`** — see
            # `SIGNS_TEXT_ATLAS_NAME` for why. `data` is what `write_glb` writes
            # there, so the one object carries both the name and the bytes and
            # nothing else has to know the pairing.
            texture=Texture(data=atlas.png, mime_type="image/png", uri=SIGNS_TEXT_ATLAS_NAME),
            material=SIGNS_TEXT_MATERIAL,
        )
        # The same collapsed-triangle filter every other builder in the pipeline
        # ends on. A zero-extent `plate_rect` would emit a degenerate quad, and
        # `select_triangles` carries `uvs`, `texture` and `material` through, so
        # the textured mesh is no exception to the rule.
        twice_area = np.linalg.norm(mesh.triangle_cross(), axis=1)
        return select_triangles(mesh, twice_area > _MIN_TWICE_AREA_M2)


def orphaned_supplementary(spec: Signs, codes: Sequence[str]) -> bool:
    """Whether a post carries supplementary plates and nothing to qualify.

    🔴 **A supplementary plate is not a sign, and on its own it is not even a
    claim.** `TS733`/`TS734` are captioned ARROW (RIGHT) and ARROW (LEFT) on
    CT174/51-3(2)D, and the Road Users' Code says what they do: *"Direction in
    which the prohibition or restriction applies (symbol may be reversed)"*.
    `TS735` is *"Prohibition or restriction applies in both directions"*. All
    three are a preposition attached to the **sentence on the plate above them**
    — and `Q65` struck most of those sentences out, because the time, parking,
    zone and vehicle-class plates they qualify are out of scope as content.

    What shipped instead was a post carrying a bare black arrow pointing along
    the kerb at nothing. It reads as a driving instruction and it is not one,
    which is `GAME_DESIGN.md`'s standing price the wrong way round: a missing
    sign costs nothing against a sign that instructs the player wrongly.

    ⚠️ **The test is "nothing here outranks supplementary", not "no regulatory
    sign here".** An arrow under a `TS414` deviation board or a `TS615` NO
    THROUGH ROAD is a legitimate assembly, and neither of those is `regulatory`.

    ⚠️ **It is a scope refusal, not a data refusal**, which is why the counter it
    feeds is a finding rather than a bar: the assembly is complete on the street,
    and the incomplete thing is this pipeline's face table. Shipping the parent
    faces would empty it, and narrowing scope again would fill it.
    """
    if not codes:
        return False
    return all(spec.faces[code].rank == SIGN_RANK_SUPPLEMENTARY for code in codes)


def _mirrors(face: SignFace, side: float) -> bool:
    """Whether this face's glyphs are flipped to face the carriageway (`Q66`).

    ⚠️ **One function because two callers must agree.** `_draw_plate` decides
    what is drawn and `build_region` counts what was decided; computed twice,
    the published `boards_mirrored` could drift from the mesh and nothing would
    say so — and that counter is the *only* evidence `Q66`'s assumption is being
    applied at all.
    """
    return face.mirror_by_side and side > 0.0


def _draw_plate(
    builder: _Builder,
    spec: Signs,
    face: SignFace,
    centre: np.ndarray,
    facing_deg: float,
    side: float,
    *,
    code: str = "",
    text: TextAtlas | None = None,
    text_builder: _TextBuilder | None = None,
) -> None:
    """One sign plate: its front layers, and the grey back it needs to be solid.

    ⚠️ **The back is why `signs.gdshader` is `cull_back` and not
    `cull_disabled`.** A railing is one quad thick and has no back, so `Q61` made
    that mesh the only `cull_disabled` one in the bundle. A sign does have a
    back, it is grey, and drawing it means winding stays the thing that decides
    visibility — which `facing_away` can then hold to 0.
    """
    normal, right = plate_frame(facing_deg)
    up = np.array([0.0, 1.0, 0.0])
    half_w, half_h = plate_extent_m(spec, face.plate)
    # ⚠️ **Stood off the front of the post, not centred on it.** `centre` is the
    # pole's own axis, and a plate is `layer_lift_m` thin — so a plate drawn at
    # the axis leaves **20 mm of a 64 mm post standing through the face of every
    # sign in the city**, worst on the 0.25 m supplementary plates where it is a
    # quarter of the plate height. Nothing in the stage could see it: the mesh is
    # correct, `facing_away` is 0 and `verify_signs.gd` passes. Found in review.
    face_centre = centre + spec.pole_radius_m * normal

    def place(polygon: np.ndarray, lift: float, outward: np.ndarray) -> np.ndarray:
        return face_centre + polygon[:, :1] * right + polygon[:, 1:2] * up + lift * outward

    # 🔴 **The one face property that is derived rather than read** (`Q66`). A
    # deviation board's chevrons point the way traffic must go, TD publishes no
    # left/right code pair for one, and the sheet draws `TS414` pointing left
    # while `TS588`/`TS589` point right — so the drawing is indicative and the
    # installed board is turned physically. The assumption is that the board
    # points **away from the kerb it stands on, into the carriageway**, which is
    # what an island nose or the outside of a bend does.
    #
    # `+u` is the viewer's right, and under drive-on-left a nearside board has
    # the carriageway on the driver's right — so `side > 0` is the mirrored case
    # and the glyphs are authored for the offside.
    #
    # ⚠️ **Negating `u` reverses winding, and that is not cosmetic.** A
    # clockwise polygon is deleted outright by `signs.gdshader`'s `cull_back`,
    # so without `[::-1]` a mirrored board would go *missing* rather than draw
    # backwards. `facing_away` would still read 0, because the normal is right.
    mirrored = _mirrors(face, side)

    def oriented(polygon: np.ndarray) -> np.ndarray:
        if not mirrored:
            return polygon
        flipped = polygon.copy()
        flipped[:, 0] = -flipped[:, 0]
        # `ccw` rather than a bare `[::-1]`: the goal is to *restore* the winding
        # the mirror destroyed, and `arrows.py` already owns that — its docstring
        # is about this exact case, a mirrored glyph rendering as nothing under
        # `cull_back` rather than as anything a frame would show.
        return ccw(flipped)

    # The back, wound the other way so its normal is `-n`. Drawn from the plate
    # outline itself rather than from a box, so a triangular sign has a
    # triangular back.
    # ⚠️ **The back is mirrored too, and that is latent rather than cosmetic.**
    # Every plate in `SIGN_PLATES` is symmetric about `u` today, so this is a
    # no-op — but a face layer that redraws the plate outline *is* mirrored, so
    # an asymmetric plate would give a front and a back that disagree. Mirrored
    # first, then reversed for `-n`.
    for polygon in layer_polygons(spec, face.plate, 1.0, half_w, half_h):
        builder.polygon(
            place(oriented(polygon)[::-1], -spec.layer_lift_m, normal),
            -normal,
            spec.colours[SIGN_BACK_COLOUR],
        )

    for depth, layer in enumerate(face.layers):
        lift = depth * spec.layer_lift_m
        if layer.draw == SIGN_TEXT:
            # 🔴 **The lettering is placed by the publisher, not by this file.**
            # `cell.plate_rect` is where TD's own drawing puts the words on the
            # plate, in `-1..1` of its bounding box, so nothing here chooses an
            # offset — which is what let the face schema stay `(draw, colour,
            # size)` instead of growing a per-layer displacement.
            #
            # ⚠️ **Never `oriented()`.** A mirrored face writes its words
            # backwards, and `config.py` refuses the combination on the way in
            # rather than trusting this comment.
            cell = None if text is None else text.cells.get(code)
            if cell is None or text_builder is None:
                continue
            u0, v0, u1, v1 = cell.plate_rect
            corners = np.array(
                [
                    [u0 * half_w, v0 * half_h],
                    [u1 * half_w, v0 * half_h],
                    [u1 * half_w, v1 * half_h],
                    [u0 * half_w, v1 * half_h],
                ]
            )
            s0, t0, s1, t1 = cell.uv_rect
            # ⚠️ **`v` runs up and `t` runs down**, so the two vertical pairs are
            # crossed here. Getting it wrong prints the words upside down on a
            # plate whose only job is to be read, and `verify_signs.gd` cannot
            # see it — the mesh is correct and `facing_away` stays 0.
            uvs = np.array([[s0, t1], [s1, t1], [s1, t0], [s0, t0]])
            text_builder.quad(place(corners, lift, normal), normal, uvs)
            continue
        for polygon in layer_polygons(spec, layer.draw, layer.size, half_w, half_h):
            builder.polygon(
                place(oriented(polygon), lift, normal), normal, spec.colours[layer.colour]
            )


def _draw_pole(
    builder: _Builder, spec: Signs, x: float, z: float, base_y: float, top_y: float
) -> None:
    """The post, as a closed prism with a cap.

    No collider, and no bottom cap: the pole meets the footway and nothing sees
    under it.
    """
    # ⚠️ **Reversed, and the reversal is the whole correctness of this function.**
    # `disc` winds counter-clockwise in `(u, v)`, which is what a *plate* wants
    # once `plate_frame` maps it — but here `u` and `v` become world `X` and
    # `Z`, and a ring counter-clockwise in `(X, Z)` has its side quads wound
    # inward and its cap wound at the ground. The first build shipped exactly
    # that: 3,200 triangles, every pole triangle in the region, facing away with
    # everything else correct — `Q58`'s tramway defect in miniature, and caught
    # by `facing_away` rather than by looking at it.
    ring = disc(spec.pole_radius_m, spec.pole_sides)[::-1]
    grey = spec.colours[SIGN_BACK_COLOUR]
    centre = np.array([x, 0.0, z])
    for index in range(spec.pole_sides):
        u0 = ring[index]
        u1 = ring[(index + 1) % spec.pole_sides]
        a = centre + np.array([u0[0], base_y, u0[1]])
        b = centre + np.array([u1[0], base_y, u1[1]])
        c = centre + np.array([u1[0], top_y, u1[1]])
        d = centre + np.array([u0[0], top_y, u0[1]])
        outward = np.array([u0[0] + u1[0], 0.0, u0[1] + u1[1]])
        length = float(np.linalg.norm(outward))
        if length <= 0.0:
            continue
        builder.polygon(np.vstack([a, b, c, d]), outward / length, grey)
    cap = np.vstack([centre + np.array([u[0], top_y, u[1]]) for u in ring])
    builder.polygon(cap, np.array([0.0, 1.0, 0.0]), grey)


# --------------------------------------------------------------------------
# The region
# --------------------------------------------------------------------------


@dataclass
class _Placed:
    """One post after registration, before anything is drawn.

    Held so the placed points can be deduped before the mesh is built — see
    `_merge_placements`.
    """

    x: float
    z: float
    y: float
    facing_deg: float
    # Which kerb this post stands on: `+1` nearside. Kept because a deviation
    # board's chevrons point away from it, and `facing_from_side` has already
    # consumed the same number to decide where the plate looks (`Q66`).
    side: float
    one_way: bool
    snap: Snap
    plates: list[Sign]


def _register(
    spec: Signs, snap: Snap, ribbon: Ribbon, published: np.ndarray, report: SignReport
) -> tuple[np.ndarray, float] | None:
    """Push a post out to the kerb the ribbon actually drew, or leave it, or refuse.

    ⚠️ **The registration.** The post keeps its along-edge position and its side
    and moves only across, out to `outset_m` past the kerb the ribbon actually
    drew. `Q60`'s move, at a second layer and for its reason: **85.5%** of the
    posts reaching here are surveyed inside the drawn kerb plus `outset_m`, a
    median 1.93 m short of it, so drawn where published most of the city's signs
    stand in the road.

    🔴 **And it is clamped to that one direction since `Q78`.** The reason to
    move a post at all is that `widen_default` draws the ribbon 1.6x the real
    carriageway, so a pole standing on the real kerb lands in the drawn lane.
    That argument runs **outward only**. Assigning the target unconditionally
    also *pulled* the posts already standing clear back toward the road — 95 of
    654 in this region, 36 of them by more than a metre and 6 by more than three
    — and no counter could see it, because `shift_m` is an absolute value and an
    inward pull and an outward push are the same number. A post already clear
    keeps the position TD surveyed.

    Returns the placed point and the kerb side, or `None` where `max_shift_m`
    refuses the move. The caller owns the plate-level counter.
    """
    half_width_m = ribbon.half_width_at(snap.t)
    # A post exactly on the centreline has no side to keep; the nearside is the
    # one a left-driving city's traffic passes closest to.
    side = 1.0 if snap.offset_m >= 0.0 else -1.0
    target_m = side * (half_width_m + spec.outset_m)
    report.inside_ribbon_m.append(max(0.0, half_width_m - abs(snap.offset_m)))

    if abs(snap.offset_m) > half_width_m + spec.outset_m:
        # ⚠️ **The published point, never a reconstruction.** The trap below
        # applies here with nothing to catch it: `snap.offset_m` is the distance
        # to the *clamped* projection, so rebuilding this position from the foot
        # and the offset would move a post past an edge's end and then report
        # the move it made as 0.0.
        #
        # A real zero rather than a skipped append, so the identity over
        # `len(shift_m)` still closes; `posts_kept_as_surveyed` is how a reader
        # tells how many of the distribution's zeros are these.
        report.shift_m.append(0.0)
        report.posts_kept_as_surveyed += 1
        return published, side

    shift_m = abs(target_m - snap.offset_m)
    # Recorded **before** the refusal, so the distribution can read outside its
    # own bar (`Q58`); `posts_over_shift` and `posts_in_carriageway` are what let
    # a reader decompose `n`.
    report.shift_m.append(shift_m)
    if shift_m > spec.max_shift_m:
        report.posts_over_shift += 1
        return None

    # ⚠️ **The foot comes off the polyline, never from
    # `point - offset_m * nearside`.** `Snap.offset_m` is `±distance_m` to the
    # *clamped* projection, so a post past an edge's end has an along-edge
    # component in that vector and the subtraction lands off the centreline.
    # Measured: a post 5 m beyond an edge's end and dead on its axis
    # reconstructs to 5 m off the road, and the 10.6 m move it then makes is
    # published as 0.6 m — under `max_shift_m`, invisible to every counter.
    # `Ribbon.foot_at` reads it instead.
    return ribbon.foot_at(snap.t) + target_m * nearside(snap.heading_deg), side


def _merge_placements(
    placements: list[_Placed], merge_m: float, report: SignReport
) -> list[_Placed]:
    """Posts that registration pushed onto the same point, as one post.

    ⚠️ **A second merge, and it is not the same one as `_merge_posts`.** That one
    removes poles the *publisher* put at one point. This one removes poles the
    *registration* put there: every post on the same edge, side and `t` is moved
    to the same offset, so two poles a metre apart before the move can be one
    after it. Without this they draw as two coincident posts, each restarting its
    stack at `mount_height_m` — the interpenetration the first merge was added to
    fix, re-created one step later.
    """
    merged: list[_Placed] = []
    for post in placements:
        for kept in merged:
            if math.hypot(post.x - kept.x, post.z - kept.z) <= merge_m:
                kept.plates.extend(post.plates)
                report.posts_merged_after_shift += 1
                break
        else:
            merged.append(post)
    return merged


def _merge_posts(
    stacks: dict[tuple[str, float, float], list[Sign]],
    merge_m: float,
    report: SignReport,
) -> list[tuple[float, float, list[Sign]]]:
    """Groups whose poles stand on the same physical post, as one post.

    🔴 **The layer publishes outright coincident poles.** Nearest-other-pole
    across this region's drawn set reads **0.00 m** at both p10 and p25, and
    **232 of 699** posts (33.1%) have a neighbour inside 0.6 m, because several
    `GG_NAME` groups hang off one real post. Drawn as separate posts their plates
    interpenetrate and neither is readable — which is what a screenshot of the
    first build shows. `~/hk-traffic-sign-map` meets the same thing and collapses
    an assembly onto its primary's anchor.

    ⚠️ **Greedy, over a deterministically sorted input**, so two builds of the
    same data merge the same way. Quadratic, and measured at **24 ms** over this
    region's ~700 posts, which is 0.2% of the run.

    ⚠️ **It does not scale, and the reason to leave it is arithmetic rather than
    principle.** Held density, it measures 0.015 s at 700 posts, **1.50 s at
    7,000** and 160 s at 70,000 — so a region ten times this one spends most of
    the stage's budget here. A uniform grid at cell size `merge_m` with a 3x3
    neighbour scan is the fix and it is **exact**, not approximate: a pair within
    `merge_m` cannot fall outside the nine cells. An earlier version of this
    comment claimed a grid would miss poles at a cell boundary, which is only
    true of a single-cell lookup, and it is corrected here because it is the
    recorded reason a later fix would have to argue against.
    """
    # ⚠️ **Sorted by position, not by `GG_NAME`.** A greedy pass is decided by the
    # order it walks, and sorting on the group string walks the region in
    # alphabetical order — so which pole absorbs which was spatially arbitrary,
    # and the drawn post stood on the alphabetically-first member. The group is
    # kept as the last key only to break exact positional ties, so the result
    # stays reproducible.
    ordered = sorted(stacks.items(), key=lambda item: (item[0][1], item[0][2], item[0][0]))
    clusters: list[list[tuple[float, float, list[Sign]]]] = []
    for (_group, pole_x, pole_z), carried in ordered:
        for cluster in clusters:
            if math.hypot(pole_x - cluster[0][0], pole_z - cluster[0][1]) <= merge_m:
                cluster.append((pole_x, pole_z, list(carried)))
                report.poles_merged += 1
                break
        else:
            clusters.append([(pole_x, pole_z, list(carried))])

    merged: list[tuple[float, float, list[Sign]]] = []
    for cluster in clusters:
        # The **centroid**, not the first member: when several groups collapse the
        # post should stand among them rather than on whichever one the walk
        # happened to reach first.
        x = sum(item[0] for item in cluster) / len(cluster)
        z = sum(item[1] for item in cluster) / len(cluster)
        plates: list[Sign] = []
        for item in cluster:
            plates.extend(item[2])
        merged.append((x, z, plates))
    return merged


def build_region(
    city: CityConfig,
    region_id: str,
    *,
    sources_root: Path | None = None,
    out_root: Path | None = None,
) -> SignReport:
    """Read the region's published traffic signs and write its `signs.glb`."""
    spec = city.signs
    report = SignReport()
    out_dir = city.out_dir(region_id, out_root)
    if spec is None:
        # Not an error, and the shape `tramway`, `arrows`, `boxjunctions` and
        # `railings` all take: a city whose estate publishes no sign layer ships
        # none rather than putting a NO ENTRY at every one-way mouth.
        log.info("city '%s' declares no signs block; nothing to draw", city.id)
        _write_manifest(out_dir, city, region_id, report)
        return report

    transform = city.game_transform(region_id)
    signs = read_signs(city, spec, region_id, transform, report, sources_root=sources_root)

    graph = read_graph(out_dir / ROADGRAPH_NAME, city.id, region_id)
    edges = [edge for edge in graph["edges"] if int(edge["elevation_level"]) == 0]
    # Level 0 only, the restriction `kerbside.py`, `tramway.py` and `arrows.py`
    # all make: for 7% of the kerbside samples the nearest edge of *any* level
    # was elevated, and the street the feature is actually on was a median 4 m
    # away.
    segments = Segments.of(edges)
    # ⚠️ **`graph["edges"]` whole, not the level-0 list above.** A restriction's
    # `from_edge` is level-0 by construction — it is the sign's own host — but
    # its `to_edge` is wherever the banned turn leads, and a turn barred onto a
    # ramp is exactly the one that would go missing.
    by_edge = {int(edge["id"]): edge for edge in graph["edges"]}
    turns = _turn_classes(graph.get("turn_restrictions", []), by_edge, spec)

    surface = read_document(
        out_dir / SURFACE_MANIFEST_NAME,
        SURFACE_MANIFEST_SCHEMA,
        f"python -m pipeline.surface --city {city.id} --region {region_id}",
    )
    drawn = ribbons(graph, surface)

    # Grouped so a pole is drawn once and its plates stack on it. Sorted by code
    # so the stack order is the source's, not the read order's — a mesh that
    # changes shape between two builds of the same data is not reproducible.
    stacks: dict[tuple[str, float, float], list[Sign]] = defaultdict(list)
    for sign in signs:
        stacks[(sign.group, sign.x, sign.z)].append(sign)

    posts = _merge_posts(stacks, spec.pole_merge_m, report)
    builder = _Builder()
    # ⚠️ **Baked before anything is drawn, and only for faces that ask.** A city
    # whose whitelist carries no `text` layer bakes nothing, ships no texture and
    # keeps `Texture memory` at 0 — the default `Q63` insisted stay the default.
    lettered = sorted(code for code, face in spec.faces.items() if face.lettered)
    text: TextAtlas | None = None
    if lettered:
        assert spec.text_source is not None  # config refuses the pair otherwise
        text = build_atlas(
            spec,
            lettered,
            cached_source(city, spec.text_source, root=sources_root),
            cell_px=spec.text_cell_px,
        )
    text_builder = _TextBuilder()
    # ---- place, then draw ----
    # ⚠️ **Two phases, because registration can re-create what the merge
    # removed.** Every post on the same edge, side and `t` is pushed to the
    # *same* offset, so two poles a metre apart — legitimately distinct where
    # they were surveyed — land on one point. A merge over surveyed positions
    # cannot see that, so the placements are deduped before anything is built:
    # drawing first would put two posts and two plate stacks in one place, each
    # starting again at `mount_height_m`.
    placements: list[_Placed] = []
    for pole_x, pole_z, carried in posts:
        snap = segments.nearest(pole_x, pole_z)
        keep: list[Sign] = []
        # ⚠️ **Bottom to top, supplementary first.** The stack is built upward
        # from `mount_height_m`, so the *last* face placed is the highest — and a
        # main sign belongs on top with its plate hanging under it. Sorting by
        # `SIGNID` alone put `TS733` above `TS115` and hung every NO ENTRY off the
        # bottom of its own arrow plate, which renders as a perfectly built
        # signpost assembled upside down. The rank is the publisher's sheet class;
        # `hk-traffic-sign-map`'s `compute-stacks.mjs` encodes the same order.
        for sign in sorted(carried, key=lambda item: (-spec.faces[item.code].rank, item.code)):
            if math.isfinite(sign.axis_deg):
                # ⚠️ **Recorded over every candidate, before any refusal.** A
                # distribution taken after its own filter is confined to that
                # filter and can say nothing — `Q58`'s `drawn_gauge_m` trap.
                # Nothing reads this; its flatness is the finding.
                report.axis_residual_deg.append(axis_residual_deg(sign.axis_deg, snap.heading_deg))
            if snap.distance_m > spec.max_offset_m:
                # No level-0 street near enough to say which traffic this sign
                # addresses. Refused rather than guessed at: without a host edge
                # there is no kerb side, and without a kerb side there is no
                # facing at all.
                report.too_far += 1
                continue
            keep.append(sign)

        if orphaned_supplementary(spec, [sign.code for sign in keep]):
            report.orphan_supplementary += len(keep)
            keep = []

        if not keep:
            continue

        report.offset_m.append(abs(snap.offset_m))

        ribbon = drawn.get(snap.edge)
        if ribbon is None:
            # No drawn carriageway on the host edge, so no kerb to stand on.
            report.no_ribbon += len(keep)
            continue

        registered = _register(spec, snap, ribbon, np.array([pole_x, pole_z]), report)
        if registered is None:
            report.over_shift += len(keep)
            continue
        placed, side = registered

        # ⚠️ **Clear of its host's kerb and still in the road**, because the post
        # landed inside a *different* edge's ribbon — junction mouths and
        # dual carriageways, where several 1.6x ribbons overlap and the drawn city
        # has no footway left at all. That is `Q19`'s territory rather than this
        # stage's, and it is **refused rather than pushed again**: iterating the
        # push was measured and is worse, plateauing at 9.7% while taking the
        # worst shift from 5.52 m to **16.77 m** — which is a post on the wrong
        # street. `GAME_DESIGN.md` prices a missing sign at nothing against a
        # misplaced one, the reason `arrows.py` gives for the same call.
        # ⚠️ **It runs on a post kept as surveyed too, and must** — standing clear
        # of its own host's kerb says nothing about an overlapping ribbon, so
        # skipping the check for that branch would let one through (`Q78`).
        settled = segments.nearest(float(placed[0]), float(placed[1]))
        settled_ribbon = drawn.get(settled.edge)
        if settled_ribbon is not None and abs(settled.offset_m) < settled_ribbon.half_width_at(
            settled.t
        ):
            report.in_carriageway += len(keep)
            report.posts_in_carriageway += 1
            continue

        placements.append(
            _Placed(
                x=float(placed[0]),
                z=float(placed[1]),
                y=snap.y,
                # ⚠️ **`side`, not `snap.offset_m`.** The two disagree at `-0.0`,
                # which `Segments.nearest` really returns for a post on the
                # centreline — `-0.0 >= 0.0` is true and `-0.0 > 0.0` is false —
                # so the post would be placed on the nearside and turned to face
                # the offside. A perfectly drawn NO ENTRY facing the wrong way,
                # which is this module's whole failure class.
                facing_deg=facing_from_side(snap.heading_deg, side, ribbon.one_way),
                side=side,
                one_way=ribbon.one_way,
                snap=snap,
                plates=keep,
            )
        )

    for post in _merge_placements(placements, spec.pole_merge_m, report):
        height = spec.mount_height_m
        for sign in post.plates:
            face = spec.faces[sign.code]
            _, half_h = plate_extent_m(spec, face.plate)
            centre = np.array([post.x, post.y + height + half_h, post.z])
            if face.mirror_by_side:
                report.boards_mirrorable += 1
                report.boards_mirrored += int(_mirrors(face, post.side))
            # ⚠️ **Per plate, not per post** (`Q72`) — a NO ENTRY is turned to
            # face the traffic it addresses, which is the opposite of what the
            # rest of its post addresses. `report.plates_turned` is what makes
            # the turn visible in the manifest.
            plate_facing_deg = _plate_facing_deg(post.facing_deg, face)
            report.plates_turned += int(plate_facing_deg != post.facing_deg)
            _draw_plate(
                builder,
                spec,
                face,
                centre,
                plate_facing_deg,
                post.side,
                code=sign.code,
                text=text,
                text_builder=text_builder,
            )
            height += 2.0 * half_h + spec.stack_gap_m

            report.drawn += 1
            report.by_code[sign.code] = report.by_code.get(sign.code, 0) + 1
            report.pole_offset_m.append(
                math.hypot(sign.x - sign.published_x, sign.z - sign.published_z)
            )
            _record_semantics(report, sign, post, face, turns, by_edge[post.snap.edge])

        _draw_pole(
            builder,
            spec,
            post.x,
            post.z,
            post.y,
            post.y + height - spec.stack_gap_m + spec.pole_headroom_m,
        )
        report.poles_drawn += 1

    # ⚠️ **Computed, not claimed** — `plates_turned` is exactly the drawn plates
    # whose face carries `faces_against_traffic`, and both agents that reviewed
    # `Q72` noted the identity lived only in prose. A turn that silently stops
    # happening renders as a perfectly drawn sign giving the opposite
    # instruction, so it is asserted where it is cheap.
    if not turned_plates_agree(spec, report):
        raise ValueError(
            f"plates_turned is {report.plates_turned}, but the drawn faces carrying "
            f"faces_against_traffic total {expected_turned(spec, report)} — the turn and "
            f"the per-code counts disagree, so one of them is not counting what it says"
        )

    mesh = builder.build(SIGNS_MESH_NAME)
    if mesh is not None:
        report.facing_away = facing_away(mesh)
        report.triangles = mesh.triangle_count
        report.vertices = len(mesh.positions)
        low, high = mesh.aabb()
        report.aabb = [list(low), list(high)]
        meshes = [mesh]
        text_mesh = None if text is None else text_builder.build(SIGNS_TEXT_MESH_NAME, text)
        if text_mesh is not None:
            # ⚠️ **`facing_away` is asked of this one too.** It is a second mesh
            # under the same `cull_back` rule, and a quad wound the wrong way is
            # not a backwards word — it is no word at all, which is exactly the
            # failure this stage cannot see in a frame (`Q58`).
            report.text_facing_away = facing_away(text_mesh)
            report.text_plates = text_mesh.triangle_count // 2
            report.text_atlas_px = text.pixels
            report.text_coverage = {code: cell.coverage for code, cell in text.cells.items()}
            meshes.append(text_mesh)
            # ⚠️ **`write_glb` writes the atlas beside the `.glb`** — the mesh
            # names `SIGNS_TEXT_ATLAS_NAME` as its texture's `uri` and `gltf.py`
            # owns both halves of that reference (`Q70`). Only its size is
            # recorded here, from the bytes rather than from a `stat` of a file
            # this module no longer writes.
            report.text_atlas_bytes = len(text.png)
        report.bytes = write_glb(out_dir / SIGNS_NAME, meshes)

    _write_manifest(out_dir, city, region_id, report)
    return report


# The codes whose instruction the road graph independently carries. Kept small
# and explicit: this is a **diff**, not a validator, so a code is here only when
# the graph really does publish the same claim.
_NO_ENTRY = "TS115"

# The three turn prohibitions, and the movement each one bans. Same rule as
# `_NO_ENTRY` and the same short list — the graph publishes 217 banned movements
# and these are the signs that say the same thing on a post.
#
# ⚠️ **`TS133` is here although `Q62` named only the first two.** A U-turn leaves
# by the edge it arrived on, so its two bearings come off one polyline in
# opposite orders and the change is exactly 180 deg — and `turn_u_deg` is refused
# at or above 180 — which makes it the one class no threshold can get wrong. It
# is 5 plates and it costs a dictionary row.
_TURN_LEFT = "left"
_TURN_RIGHT = "right"
_TURN_U = "u"
# A banned movement that is neither: straight through a junction, or a turn this
# stage could not classify. Never claimed by a sign, so a plate meeting only this
# reads as a disagreement — which is what it is. The graph bans *something*
# there and it is not what the plate names.
_TURN_OTHER = "other"
_TURN_PROHIBITIONS = {"TS131": _TURN_LEFT, "TS132": _TURN_RIGHT, "TS133": _TURN_U}


def _heading_deg(start: Sequence[float], end: Sequence[float]) -> float:
    """Plan heading from `start` to `end`, degrees clockwise from north (`-Z`).

    ⚠️ **The same expression `Snap.heading_deg` is built from**, and it is a
    second copy rather than a first: `fares.py` computes it inline and scalar on
    the segment a snap landed on. By the rule `arrows.directed_residual_deg`
    states, that puts its home beside `Snap.heading_deg` in `fares.py`, where the
    convention is documented, with both callers importing it. Left here because
    moving it edits `Segments.nearest`, which every stage in the pipeline snaps
    through, and that is not this task's to touch.
    """
    return math.degrees(math.atan2(end[0] - start[0], -(end[2] - start[2]))) % 360.0


def _at_node(edge: dict[str, Any], node: int, *, leaving: bool) -> float | None:
    """Heading of the edge's own end at `node`, arriving at it or leaving it.

    `None` where the node is neither end of the edge, which the graph's own
    referential check (`export.py`) says cannot happen — kept because the
    alternative is an `IndexError` in a stage that is only counting.
    """
    points = edge["polyline"]
    if int(edge["from"]) == node:
        end, inward = points[0], points[1]
    elif int(edge["to"]) == node:
        end, inward = points[-1], points[-2]
    else:
        return None
    return _heading_deg(end, inward) if leaving else _heading_deg(inward, end)


def _turn_class(arrive_deg: float | None, leave_deg: float | None, spec: Signs) -> str:
    """Which movement a banned turn is, read off its own geometry.

    🔴 **Read rather than looked up, because the graph publishes no restriction
    type.** The source's `TURN` layer carries `OTHER_REST_TYPE` and `P1-3` reads
    it and never emits it, so `roadgraph.json` says only *from here, through
    here, to there*. Turning left decreases a heading clockwise from north, so
    the signed change across the junction is the whole classification.

    ⚠️ **A U-turn falls out of this rather than being branched for.** A movement
    that leaves by the edge it arrived on reads its two bearings off one
    polyline in opposite orders, so the change is exactly 180 deg — and
    `turn_u_deg` is refused at or above 180, so it lands here. 60 of the
    region's 217 restrictions are that shape.
    """
    if arrive_deg is None or leave_deg is None:
        return _TURN_OTHER
    change = (leave_deg - arrive_deg + 180.0) % 360.0 - 180.0
    if abs(change) >= spec.turn_u_deg:
        return _TURN_U
    if abs(change) <= spec.turn_straight_deg:
        return _TURN_OTHER
    return _TURN_LEFT if change < 0.0 else _TURN_RIGHT


def _turn_classes(
    restrictions: Sequence[dict[str, Any]],
    by_edge: dict[int, dict[str, Any]],
    spec: Signs,
) -> dict[tuple[int, int], set[str]]:
    """Every published turn restriction, keyed by the approach it bans a turn out of.

    ⚠️ **Keyed on `(from_edge, via_node)` because that pair *is* an approach** —
    one edge arriving at one junction — which is exactly what a sign standing on
    that edge addresses. Several restrictions can share the pair, so the value is
    the set of movements banned there.
    """
    classes: dict[tuple[int, int], set[str]] = defaultdict(set)
    for turn in restrictions:
        from_edge, via_node = int(turn["from_edge"]), int(turn["via_node"])
        to_edge = int(turn["to_edge"])
        host, onto = by_edge.get(from_edge), by_edge.get(to_edge)
        if host is None or onto is None:
            continue
        # ⚠️ **A same-edge movement needs no special case, and one was written
        # and then removed.** `_at_node` reads the two ends of a polyline in
        # opposite orders, so leaving by the edge you arrived on is a change of
        # exactly 180 deg and `turn_u_deg` is refused at or above 180 — the
        # geometry below already answers `_TURN_U` for all 60 of the region's.
        # The branch was dead: no mutation of it could change a number.
        classes[(from_edge, via_node)].add(
            _turn_class(
                _at_node(host, via_node, leaving=False),
                _at_node(onto, via_node, leaving=True),
                spec,
            )
        )
    return dict(classes)


def _downstream_node(host: dict[str, Any], post: _Placed) -> tuple[int, float]:
    """The junction this sign's own traffic reaches next, and how far off it is.

    🔴 **Derived from `facing_deg`, not from the side directly, and that is the
    point.** A sign faces the traffic it addresses, so that traffic runs at
    `facing_deg + 180`; `facing_from_side` returns the edge heading turned
    around exactly when the post is nearside-or-one-way, so the comparison below
    is exact rather than tolerant. Reading the facing back out is what couples
    this counter to the expression it grades: flip the side test and every plate
    is matched to the *far* end of its edge.

    `Snap.t` is normalised over the whole edge — 0 at `from`, 1 at `to` — so the
    distance falls out of it, and `roads.py` has already reversed every
    `backward` edge, so polyline order is `from` to `to`.
    """
    # `plan_lengths` rather than a fourth copy of the arithmetic — its own
    # docstring is that argument — and `Ribbon.length_m` is this same value from
    # the same call, so `Snap.t` and this are normalised over one number by
    # construction rather than by coincidence.
    length_m = float(plan_lengths(np.asarray(host["polyline"], dtype=np.float64))[-1])
    if directed_residual_deg(post.facing_deg + 180.0, post.snap.heading_deg) < 90.0:
        return int(host["to"]), (1.0 - post.snap.t) * length_m
    return int(host["from"]), post.snap.t * length_m


def _record_semantics(
    report: SignReport,
    sign: Sign,
    post: _Placed,
    face: SignFace,
    turns: dict[tuple[int, int], set[str]],
    host: dict[str, Any],
) -> None:
    """Diff what a sign says against what the graph says, and count the gaps.

    ⚠️ **The counters here are different in kind, and conflating them would lose
    the useful ones.**

    🔴 **`no_entry_against_flow` is a self-check that must be 0, and it is the
    INVERSE of what stood here until `Q72`.** That one — `no_entry_with_flow` —
    was described in this docstring as *"a tautology by design"*, and it was:
    `facing_from_side` turned every one-way sign to face its traffic, so a NO
    ENTRY could not come out facing with the flow whatever the data said, and 0
    was unreachable proof that the rule had run rather than evidence it was
    right. 🔴 **And the state it certified was the wrong one.** A NO ENTRY stands
    at the mouth a driver must not enter by; it addresses traffic coming the
    other way, so it faces **with** the flow. Reported from the driving seat: a
    NO ENTRY staring back down a one-way the car was legally on, with this
    counter reading 0.

    ⚠️ **It is still not data-sensitive, and saying otherwise would repeat the
    mistake it was written about.** On a one-way host `facing_from_side` returns
    `heading + 180` and `_plate_facing_deg` adds another 180, so a flagged plate's
    facing is identically `heading` and this residual is identically 0. **No input
    the pipeline can read moves it.** What it catches is `faces_against_traffic`
    being dropped from a face, or the turn being removed from `_plate_facing_deg`
    — a config-and-code ratchet, in the family of `facing_away`, and no more.

    🟡 **A check that could disagree would have to read something
    `facing_from_side` did not produce** — `_downstream_node` is the obvious
    candidate, asserting a one-way's NO ENTRY sits at the mouth traffic enters by
    rather than the one it leaves by. That is a real second opinion, it is not
    built, and `Q62` is where the debt lives.

    `no_entry_on_two_way` is a genuine second-source diff (`Q56`): a NO ENTRY
    standing on a street the graph calls two-way is a disagreement between two
    independently digitised sources, and it is **report-only** — a finding to go
    and look at, never a bar to retune against. Refusing on it would be asserting
    the graph is right, and this stage has no standing to do that.

    🔴 **`turn_sign_*` is the half `P3-16` owed and `Q62` named, and building it
    refuted the claim it was built on.** 68 prohibition plates run against the
    graph's 217 banned movements, matched sign → junction → movement, with the
    junction taken from the facing itself (`_downstream_node`) so that a facing
    derived onto the wrong kerb would send a plate to the opposite end of its
    edge. It does not: mirroring the whole region moves `agreed` **29 to 30**,
    because `facing_from_side` ignores the side on a one-way host and
    `turn_sign_on_one_way` is **62 of 68**. The gradeable population for the side
    is 6 plates, which is not a population worth the name. `Q62` stays open.

    ✅ **It grades something else, and that is worth having**: of the 43 plates
    whose approach the graph bans anything at, 29 name the movement it bans and
    **14 do not**. Two independently digitised sources disagreeing about
    which movement is barred at one junction is `Q64`'s failure class — a code
    read off the wrong row renders perfectly — and this is the only thing that
    looks at it.

    ⚠️ **Report-only, never a bar**, and `unmatched` least of all: the graph
    publishes 34 banned lefts against 38 drawn `TS131`, so silence there is its
    coverage and not this stage's error.
    """
    # 🔴 **Two axes that overlap on one code and are not the same set.**
    # `_NO_ENTRY` is the *second-source* axis — the codes whose instruction the
    # road graph independently carries — and `TS116` is deliberately not in it,
    # because ALL VEHICLES PROHIBITED BOTH DIRECTIONS makes no one-way claim for
    # a two-way host to disagree with. `faces_against_traffic` is the *facing*
    # axis and covers both. Keying the facing check on the flag rather than on
    # `_NO_ENTRY` is what stops a flagged face being turned but graded by
    # nothing: `TS116` was, on 18 of the 197 turned plates.
    if sign.code == _NO_ENTRY and not post.one_way:
        report.no_entry_on_two_way += 1
        return
    # 🔴 **The UNION, and gating on the flag alone was wrong.** Grading only
    # flagged faces covers `TS116` but makes the check vanish exactly when the
    # flag is dropped — the one regression it exists to catch — and a mutation
    # test caught it doing nothing. `_NO_ENTRY` is this module's own independent
    # claim that `TS115` is a NO ENTRY, so it grades that code whatever the
    # config says, while the flag brings in every other turned face.
    #
    # ⚠️ **The residual gap, stated rather than hidden**: the flag being dropped
    # from a face that is *not* `_NO_ENTRY` — `TS116` today — is undetectable
    # here, because config is the only thing claiming that face should turn and a
    # check cannot grade its own source of truth. `plates_turned` against
    # `by_code` covers the count; nothing covers the intent.
    if face.faces_against_traffic or sign.code == _NO_ENTRY:
        # ⚠️ **The plate's facing, recomputed rather than passed in.** This
        # function needs the face for the branch above anyway and `post` carries
        # its own facing, so taking both would be two routes to one fact.
        if post.one_way and (
            directed_residual_deg(_plate_facing_deg(post.facing_deg, face), post.snap.heading_deg)
            > 90.0
        ):
            report.no_entry_against_flow += 1
        return

    claimed = _TURN_PROHIBITIONS.get(sign.code)
    if claimed is None:
        return
    report.turn_sign_on_one_way += int(post.one_way)
    node, to_junction_m = _downstream_node(host, post)
    report.turn_sign_to_junction_m.append(to_junction_m)
    published = turns.get((post.snap.edge, node))
    if published is None:
        # The graph bans nothing out of this approach. ⚠️ **Not a failure** — it
        # publishes 34 left prohibitions against 38 drawn `TS131`, so it does not
        # carry every signed one, and this is the bucket that says so.
        report.turn_sign_unmatched += 1
    elif claimed in published:
        report.turn_sign_agreed += 1
    else:
        report.turn_sign_disagreed += 1


def _write_manifest(out_dir: Path, city: CityConfig, region_id: str, report: SignReport) -> int:
    document = {
        "schema_version": SIGNS_MANIFEST_SCHEMA,
        "city_id": city.id,
        "region_id": region_id,
        # Gated on what was written, for the reason `tramway.json` records: a
        # manifest naming an asset the bundle does not hold is what `CITY_SCHEMA`
        # 11 was bumped over.
        "asset": SIGNS_NAME if report.drawn else None,
        # The read, as four disjoint parts of `signs`.
        "signs": report.signs,
        # ⚠️ **The big number here is the decision, not a shortfall.** Every sign
        # whose meaning is its text lands in it (the no-texture contract, `mesh_contract.gd`).
        "not_whitelisted": report.not_whitelisted,
        "on_structure": report.on_structure,
        "empty_geometry": report.empty_geometry,
        "candidates": report.candidates,
        # The join and the registration, as disjoint parts of `candidates`.
        "drawn": report.drawn,
        # ⚠️ **`GG_NAME` is the only join this layer has.** These two are what it
        # costs: a sign whose graphical group names no at-grade pole, and one
        # whose group names several. Neither is resolved by distance — see
        # `read_signs`.
        "no_pole": report.no_pole,
        "ambiguous_pole": report.ambiguous_pole,
        # ⚠️ Taken at `hk-traffic-sign-map`'s 15 m rather than re-derived; see
        # `max_pole_span_m` in the city file, and `pole_offset_m` below for the
        # distribution it cuts.
        "pole_too_far": report.pole_too_far,
        "too_far": report.too_far,
        # ⚠️ The registration's two refusals — see `build_region`.
        "no_ribbon": report.no_ribbon,
        "over_shift": report.over_shift,
        # 🔴 **Refused because registration could not get them out of the road** —
        # junction mouths where the widened ribbons overlap and the drawn city has
        # no footway. A finding about `Q19`'s widening, not about this stage.
        "in_carriageway": report.in_carriageway,
        # 🔴 **Supplementary plates with nothing above them to qualify** — a bare
        # ARROW (LEFT) pointing along a kerb, which reads as an instruction and is
        # not one. ⚠️ **A count of this pipeline's own scope, not of the
        # source's**: the assembly is complete on the street, and `Q65` is what
        # removed the sign the arrow belongs to. It rises when scope narrows and
        # falls when more faces ship, so it is a finding rather than a bar.
        "orphan_supplementary": report.orphan_supplementary,
        # ---- the lettering, and the three ways it fails to nothing ----
        "text_plates": report.text_plates,
        # ⚠️ Must be 0. A backwards quad is not a backwards word, it is no word.
        "text_facing_away": report.text_facing_away,
        # The number `PROGRESS.md`'s `Texture memory` is, and what
        # `generated_signs.gd` declares room for. Moving it is a budget change.
        "text_atlas_px": report.text_atlas_px,
        # 🔴 **The atlas as a shipped file** (`Q70`), `null` where this region
        # baked no lettering. `export.py` copies it into `city.json` and
        # `shipped()` carries it, which is the whole point: an image the manifest
        # names is an image `sync_generated.sh` keeps. ⚠️ **The constant gated on
        # a counter, exactly as `asset` above is** — a region that baked nothing
        # must not be contradicted by a constant, and `text_plates` is the counter
        # that says whether it did. Carrying the name through the report as well
        # would be a second route to one fact.
        "text_atlas": SIGNS_TEXT_ATLAS_NAME if report.text_plates else None,
        # ⚠️ **`bytes` is `signs.glb` alone and no longer covers the image.**
        # Published separately so the two halves of what this stage writes can be
        # added up on purpose rather than by assuming one contains the other.
        "text_atlas_bytes": report.text_atlas_bytes,
        # 🔴 Ink fraction per baked cell. Near zero is a cell cropped off the
        # lettering, which bakes paper and renders as the blank plate `P3-20`
        # exists to replace.
        "text_coverage": dict(sorted(report.text_coverage.items())),
        "poles_drawn": report.poles_drawn,
        # 🔴 Published poles folded into another because they stand on the same
        # physical post. The layer really does publish coincident poles.
        "poles_merged": report.poles_merged,
        # ⚠️ Registration pushes every post on one edge, side and `t` to the same
        # offset, so it can re-create coincident posts the first merge removed.
        "posts_merged_after_shift": report.posts_merged_after_shift,
        # Post-level counterparts of `over_shift` and `in_carriageway`, which are
        # plates. These are what make `shift_m`'s `n` decomposable.
        "posts_over_shift": report.posts_over_shift,
        "posts_in_carriageway": report.posts_in_carriageway,
        # 🔴 **Posts standing where TD surveyed them** — already clear of the
        # drawn kerb and `outset_m`, so the registration's outward argument never
        # reached them (`Q78`). They contribute a real 0.0 to `shift_m` below, and
        # this is the only thing that says how many of its zeros are theirs.
        "posts_kept_as_surveyed": report.posts_kept_as_surveyed,
        # ⚠️ **How far each post moved sideways onto the drawn kerb**, over every
        # registered post including the ones `max_shift_m` refused — `n` past
        # `poles_drawn` is the proof it reads outside its own bar (`Q58`). This is
        # the price of registering rather than reading, and `Q60` is the
        # precedent for publishing it rather than asserting it is small.
        # ⚠️ **Read it with `posts_kept_as_surveyed`** — since `Q78` it is the
        # price over the posts that needed a registration, with a real 0.0 for
        # those that did not, so it is not a distribution of moves that happened.
        "shift_m": report.measured(report.shift_m),
        # How far inside the drawn carriageway each post was **surveyed**, 0 where
        # it was already outside. The measurement that forced the registration.
        "inside_ribbon_m": report.measured(report.inside_ribbon_m),
        "by_code": dict(sorted(report.by_code.items())),
        # 🔴 **Published, unread, and flat — which is the finding.** How far each
        # plate's `ANGLE` sits from its host edge's axis: 0 along the road, 90
        # across it. p50 near 45 with the tails even means the publisher's angle
        # says nothing about the street, which is what forced the facing to be
        # derived (see `pipeline/signs.py`'s docstring). Republished every run so
        # the claim is answerable from a shipped artefact rather than a scratch
        # script (`Q37`) — and so a publisher who starts populating it properly
        # shows up here as a mode appearing.
        "axis_residual_deg": report.measured(report.axis_residual_deg),
        # What `max_offset_m` is set against, published so the config's comment is
        # checkable against a shipped artefact rather than a scratch script.
        "offset_m": report.measured(report.offset_m),
        # ⚠️ **Published point to *surveyed* pole — not to where it is drawn.**
        # The measurement the whole stage rests on: the abbreviation point is a
        # drawing label and this is how far it sits from the object it names. The
        # drawn displacement is larger and is this plus the merge offset plus
        # `shift_m`. A collapse
        # toward zero would mean the publisher had changed what the layer means.
        "pole_offset_m": report.measured(report.pole_offset_m),
        # ⚠️ **Report-only, and a genuine second-source diff** (`Q56`): a NO ENTRY
        # standing on a street the graph calls two-way is a disagreement between
        # two independently digitised sources — a finding to go and look at,
        # never a bar to retune against.
        "no_entry_on_two_way": report.no_entry_on_two_way,
        # ⚠️ **Must be 0**, and unlike the line above this is a self-check rather
        # than a finding — see `_record_semantics`. It read 117 of 253 while
        # `facing_from_side` was missing its one-way branch.
        # 🔴 Must be 0, and it is the INVERSE of the counter that stood here
        # until `Q72` — see `_record_semantics` for why 0 on the old one was
        # success reported for the wrong configuration.
        "no_entry_against_flow": report.no_entry_against_flow,
        # Plates turned 180 degrees off their own post because their face
        # addresses traffic coming the other way (`Q72`). Tracks the drawn NO
        # ENTRY family exactly; a fall to 0 means the turn stopped happening.
        "plates_turned": report.plates_turned,
        # 🔴 **The diff `Q62` named, over `TS131`/`TS132`/`TS133`.** The three
        # below close over those codes in `by_code`, and they are report-only for
        # the reason above. ⚠️ **Read `agreed` against `disagreed` and leave
        # `unmatched` out of the ratio** — the graph does not publish every
        # signed prohibition, so `unmatched` measures its coverage and not this
        # stage's join.
        #
        # 🔴 **Read `turn_sign_on_one_way` first, because it bounds what the
        # three below can mean.** At 62 of 68 the facing on almost every one of
        # these plates never consulted the kerb side, so this diff cannot grade
        # that side — measured, not assumed: the mirrored region reads 30.
        "turn_sign_on_one_way": report.turn_sign_on_one_way,
        "turn_sign_agreed": report.turn_sign_agreed,
        "turn_sign_disagreed": report.turn_sign_disagreed,
        "turn_sign_unmatched": report.turn_sign_unmatched,
        # Recorded over all three outcomes, with no bar on it (`Q58`'s trap).
        "turn_sign_to_junction_m": report.measured(report.turn_sign_to_junction_m),
        # ⚠️ **Must be 0.** `signs.gdshader` is `cull_back`, so winding decides
        # visibility and the normal attribute does not. The tramway shipped 5,111
        # of 5,112 triangles facing the ground with everything else correct.
        "facing_away": report.facing_away,
        "boards_mirrorable": report.boards_mirrorable,
        "boards_mirrored": report.boards_mirrored,
        "triangles": report.triangles,
        "vertices": report.vertices,
        "bytes": report.bytes,
        "aabb": report.aabb,
    }
    return write_document(out_dir / SIGNS_MANIFEST_NAME, document)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--sources-root", type=Path, default=None)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    city = load_city(args.city)
    report = build_region(city, args.region, sources_root=args.sources_root, out_root=args.out_root)
    log.info(
        "signs: %d signs -> %d plates on %d poles (%d unlisted, %d no pole, %d off-group), "
        "%d triangles, %d facing away",
        report.signs,
        report.drawn,
        report.poles_drawn,
        report.not_whitelisted,
        report.no_pole,
        report.pole_too_far,
        report.triangles,
        report.facing_away,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
