# tariff.tres

Rationale for `game/tuning/tariff.tres`. Each heading is the line the block sat above; `Overview` is the
file as a whole. Why it lives here and not in the file: `Q119`.

## Overview

The urban (red) taxi tariff the 咪錶 runs (`P3-1a`, `Q141`), as Transport Department publishes it
— "Taxi fare of Hong Kong", <https://www.td.gov.hk/en/transport_in_hong_kong/public_transport/taxi/taxi_fare_of_hong_kong/index.html>,
effective **14 July 2024**. These are the government's numbers, not ours: the user's call was that
the meter shows real money, and `FareMeter` (`scripts/core/fare_meter.gd`) applies them to the
metres driven and the seconds waited. The tuning that is ours — radii, dwells, the par speed and
the tip — is `fares.tres`, a separate table, so a tariff revision touches one file.

⚠️ EVERY KEY BELOW IS REQUIRED. `fare_tariff.gd` declares no defaults, so a missing key reads as
zero, and the meter refuses to construct on a zero flagfall, unit or price rather than fall back
to a literal. `verify_fares.gd` reads this file and grades the arithmetic against hand-computed
points (2,001 m → 31.1; 9,000 m → 102.5; 9,200 m → 103.9).

⚠️ In a 1.5 km² region the reading is HK$29 for most fares: the flagfall covers 2 km and the
waiting unit starts only past it. That is the tariff, not a stuck meter; the skill half of a
fare's money is the tip (`fares.md`).

Not fields, recorded for `P3-1b`: the New Territories (green) tariff is 25.5 / 1.9 / 1.4 at
82.5, Lantau (blue) 24 / 1.9 / 1.6 at 195; the cross-harbour tunnels add HK$25 toll plus HK$25
return toll, the return toll waived when the hiring begins at a cross-harbour taxi stand; baggage
HK$6 a piece, animals HK$5, telephone booking HK$5.

## `flagfall_hkd = 29.0`

"First 2 kilometres or any part thereof: $29." What the meter shows the moment the passenger
boards.

## `flagfall_m = 2000.0`

The two kilometres the flagfall covers.

## `step_m = 200.0`

"Every subsequent 200 metres or part thereof." One unit; "or part thereof" is why the meter
charges a unit as it begins, one centimetre past the previous one.

## `step_s = 60.0`

"Or waiting time of 1 minute or part thereof." The same unit priced in time. A distance-time meter
runs both and charges when either is exceeded, so there is no speed at which "waiting" begins to
tune: below 12 kph the minute fills first, above it the 200 m.

## `step_hkd = 2.1`

The unit price until the reading reaches `threshold_hkd`.

## `step_hkd_after = 1.4`

The unit price from `threshold_hkd` on — TD's long-trip taper, unreachable inside one region and
kept because the meter is the tariff, whole.

## `threshold_hkd = 102.5`

"Until the fare reaches $102.5." 29 + 35 × 2.1 lands on it exactly, in cents.
