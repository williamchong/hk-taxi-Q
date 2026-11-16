# rev_limiter.tres

A real engine's cut-out, on the driven wheels' rim speed (`P3-53`, `Q153`).

- `overspeed_share = 0.5`: how far past top speed a driven rim may spin before the drive stops, as
  a share of it. At 0 a countersteered slide at 86 kph meets the limiter mid-slide (`hold`
  1.40 s); 0.25 does not carry 86 kph either (1.62 s). The user's call after driving the pad. Not
  re-swept since the drive was sized on the rim's own speed (`Q153`).
