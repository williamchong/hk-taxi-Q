"""The constants that *are* Hong Kong (`Q100`).

Everything here is a fact about the city rather than a tuning of it, and there
is deliberately very little: the CRS pair every publisher prints in, which side
of the road the city drives on, and the handful of sign codes that drive a
*branch* in `signs.py`. Anything that is a publisher's vocabulary or a number
that could be tuned — a face, a class list, a glyph table, a width bound — is
data and belongs in `etl/config/hong_kong.yaml` under hard rule 4, not here.

⚠️ **This module is the only second home a Hong Kong fact may have.** The rule
that replaced "city-agnostic" is not "constants anywhere"; it is one place for
config and one place for code, and a value must not appear in both.
"""

from __future__ import annotations

CITY_ID = "hong_kong"
CITY_NAME = "Hong Kong"

# Every source dataset is published in the HK1980 Grid System — a Transverse
# Mercator projection in metres. All pipeline geometry stays in it until the
# final conversion to game space (`crs.py`).
PROJECTED_CRS = "EPSG:2326"

# The datum the region bounds are expressed in. HK1980 and WGS84 differ by
# ~304 m on the ground here — the grid's own natural origin sits at
# 114-10-42.80 E, 22-18-43.68 N *on HK1980*, and feeding those digits in as
# WGS84 lands 304 m away, a fifth of the width of the Wan Chai region. The
# region bounds were read off a consumer web map, which serves WGS84.
# `test_crs.py` guards the separation (`P0-4`).
GEODETIC_CRS = "EPSG:4326"

# Hong Kong drives on the left. `surface.mitres` offsets one half-width to the
# **left** of travel and `TEXCOORD_0`'s `U = 0` is the nearside kerb; every
# `_register` reads the sign of an offset the same way. Named here so the fact
# has a home; nothing reads the boolean, because the convention is baked into
# those frames and a flag that could disagree with them would be a lie.
DRIVES_ON_LEFT = True

# The sign codes whose instruction the road graph independently carries, so
# `signs.py` can grade a plate against the network. A code here drives a
# branch, which is why it is code and not a `signs.faces` entry: a second copy
# in config would be `Q72`'s tautology with a longer path.
NO_ENTRY = "TS115"
# The three turn prohibitions and the movement each bans, in `signs.py`'s own
# movement vocabulary (`_TURN_LEFT` / `_TURN_RIGHT` / `_TURN_U`).
#
# ⚠️ **`TS133` is here although `Q62` named only the first two.** A U-turn leaves
# by the edge it arrived on, so its two bearings come off one polyline in
# opposite orders and the change is exactly 180 deg — and `turn_u_deg` is refused
# at or above 180 — which makes it the one class no threshold can get wrong. It
# is 5 plates and it costs a dictionary row.
TURN_PROHIBITIONS = {"TS131": "left", "TS132": "right", "TS133": "u"}

# The white bar of a NO ENTRY plate, as a fraction of the disc's diameter.
#
# ⚠️ **Measured, not authored** (`Q67`). `TS115`'s cell reads a bar **0.868** of
# the diameter long and **0.187** thick. The layer authored 0.66 by 0.22 — a
# quarter short and a sixth too thick — on the region's commonest sign by a wide
# margin, so it was the face the player saw wrong most often.
#
# 🔴 **The two bars are the same AREA to a tenth**, 0.145 against 0.162, and that
# is the finding rather than the numbers: a grader that compared area alone would
# have passed a visibly different bar. `sign_face_survey.py` grades extents for
# this reason, and this is the defect it was written against.
NO_ENTRY_BAR_THICKNESS = 0.187
