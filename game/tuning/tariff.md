# tariff.tres

The urban (red) taxi tariff the meter runs (`P3-1a`, `Q141`), as Transport Department publishes it:
"Taxi fare of Hong Kong",
<https://www.td.gov.hk/en/transport_in_hong_kong/public_transport/taxi/taxi_fare_of_hong_kong/index.html>,
effective 14 July 2024. The government's numbers, applied by `FareMeter`
(`scripts/core/fare_meter.gd`). Our own fare tuning is `fares.tres`.

Every key is required: `fare_tariff.gd` declares no defaults and the meter refuses a zero flagfall,
unit or price. `verify_fares.gd` grades the arithmetic against hand-computed points (2,001 m →
31.1; 9,000 m → 102.5; 9,200 m → 103.9).

- `flagfall_hkd = 29.0`, `flagfall_m = 2000.0`: "First 2 kilometres or any part thereof: $29." In
  a 1.5 km² region most fares read HK$29; that is the tariff, not a stuck meter.
- `step_m = 200.0`: "Every subsequent 200 metres or part thereof", charged as the unit begins.
- `step_s = 60.0`: "or waiting time of 1 minute or part thereof". Both run and either charges, so
  under 12 kph the minute fills first.
- `step_hkd = 2.1`: the unit price until the reading reaches `threshold_hkd`.
- `step_hkd_after = 1.4`: the unit price from there on. Unreachable inside one region; kept
  because the meter is the whole tariff.
- `threshold_hkd = 102.5`: "Until the fare reaches $102.5." 29 + 35 × 2.1 lands on it exactly.

Not fields, for `P3-1b`: New Territories (green) 25.5 / 1.9 / 1.4 at 82.5; Lantau (blue) 24 / 1.9 /
1.6 at 195; cross-harbour tunnels add HK$25 toll plus HK$25 return toll (return waived from a
cross-harbour taxi stand); baggage HK$6 a piece, animals HK$5, telephone booking HK$5.
