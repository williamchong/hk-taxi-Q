# Licensing

Three kinds of thing live in this repository, under three different licences, because they have three
different owners.

| What | Where | Licence |
|---|---|---|
| **Code** — pipeline, engine scripts, tools, config, tuning | `etl/`, `game/scripts/`, `game/tools/`, `game/tuning/`, `tools/` | **GPL-3.0-or-later** — [`LICENSE`](LICENSE) |
| **Hand-authored assets** — hero buildings, vehicles, UI, shaders | `game/assets/authored/` | **CC BY-SA 4.0** |
| **Generated city data** — tiles, road surface, road graph, fare nodes | `game/assets/generated/`, `etl/out/` — *gitignored* | **Not licensed by this project.** Governed by the DATA.GOV.HK and CSDI Portal Terms of Use |

> **Not legal advice.** This file records the project's position. Hard rule 6 requires a Hong Kong IP
> lawyer to review before launch; the open questions at the end belong in that brief.

---

## Code — GPL-3.0-or-later

Full text in [`LICENSE`](LICENSE), the unmodified gnu.org text.

Godot is MIT and the Python dependencies are BSD/MIT-family, so no dependency constrains this choice.

### Store builds need a separate grant

GPLv3 §6 forbids imposing further restrictions. App Store terms impose them — per-device limits, no
redistribution — so **a GPLv3 build cannot be distributed through the App Store.**

The resolution is dual licensing: a copyright holder is not bound by their own licence, so this
repository can be GPL-3.0-or-later while store builds ship under a separate proprietary grant.

⚠️ **This works only while one party owns the entire copyright.** A patch accepted from an outside
contributor is GPL-only, and the whole can no longer be relicensed for the store. **A CLA or
copyright assignment is therefore required before the first outside contribution**, and there is no
way to obtain the right retroactively if a contributor declines.

### Corresponding source

For a distributed build, the source corresponding to the generated city assets is the ETL, the city
config, and the public government sources — all either in this repository or freely downloadable.
The build is reproducible from them by a single documented command.

---

## Hand-authored assets — CC BY-SA 4.0

`game/assets/authored/` holds original creative work: hero building models, the vehicle roster, UI
and shaders. These are **not** derived from government data — the ETL excludes the source geometry
each hero building replaces, via `replaces_source_ids` — so they are ours to license.

CC BY-SA 4.0 is one-way compatible with GPL-3.0-or-later, which is what allows these assets to
combine into the GPLv3 game. Store builds carry the separate grant described above.

⚠️ A licence is not a depiction right. These models depict real, identifiable Hong Kong landmarks;
CC BY-SA governs only our copyright in the model.

---

## Generated city data — government terms, not ours

`game/assets/generated/` and `etl/out/` are derived from the Lands Department's 3D Visualisation Map
and the Transport Department's Road Network v2, obtained via DATA.GOV.HK and the CSDI Portal.

**Both directories are gitignored. This repository redistributes no government data.** A clone
contains none of it until the pipeline is run, at which point the data is fetched from the government
endpoints and the fetcher accepts those terms directly.

### The governing terms

Both portals grant the same six acts. Quoted from
`data.gov.hk/en/terms-and-conditions` and `portal.csdi.gov.hk/csdi-webpage/doc/TNC`, read
2026-08-02:

> *You are allowed to **browse, download, distribute, reproduce, hyperlink to, and print** the Data
> for both commercial and non-commercial purposes on a free-of-charge basis on condition that:-*
>
> - *you shall identify clearly the source of the Data and acknowledge the Government and the
>   Relevant Organisations' ownership of the intellectual property rights in the Data and in all
>   copies thereof…*
> - *you shall indemnify the Government and the Relevant Organisations against any allegations or
>   claims of infringement of the rights of any person and all costs, losses, damages and
>   liabilities…*

- Commercial use is explicit.
- **No usage limit, quota, volume cap or rate limit** appears in either document.
- The indemnity is broad and runs against **any** allegation of infringement of **any** person's
  rights.
- **Sub-licensing is not addressed.** Silence is not permission.
- CSDI requires acknowledging **the CSDI Portal** as source; DATA.GOV.HK requires acknowledging
  **DATA.GOV.HK**. A build using both must credit both.

### Why the generated data is not relicensed

1. **The indemnity runs one way.** We indemnify the Government against any infringement claim, and
   nobody indemnifies us. Restamping the data under a permissive licence would tell downstream
   recipients they may freely redistribute and adapt it, and any resulting exposure returns to us.
2. **Permission to distribute is not authority to relicense**, and sub-licensing is unaddressed.
3. **The attribution obligation would not survive.** CC requires attributing *us*; the government
   terms require identifying the source and acknowledging the Government's ownership of the IP
   rights. A recipient following a CC notice alone would satisfy CC and breach the terms.

**So the data is regenerated rather than redistributed.** Anyone who wants it runs the pipeline,
which takes about three seconds and accepts the terms at the source.

### What a shipped game contains

An exported build **does** ship the derived data — tiles, road surface, road graph and fare nodes are
all in the bundle. That is permitted, and it is what makes the credits screen mandatory rather than
optional. A bundle is therefore a multi-licence artefact:

| Part | Terms |
|---|---|
| Engine | MIT (Godot) |
| Game code | GPL-3.0-or-later, or the store grant |
| Authored assets | CC BY-SA 4.0, or the store grant |
| Generated city data | DATA.GOV.HK / CSDI Portal Terms of Use, with attribution |

**Player count does not consume any government allowance.** The game makes no runtime network calls
(hard rule 2); the ETL runs once per developer at build time. Distribution is governed by the re-use
grant above, which sets no volume limit.

---

## Open questions for legal review

1. **Landmark depiction.** Trade dress and trademark in the hero buildings, independent of copyright.
   The one question here with a plausible adverse answer.
2. **The credits text**, against the attribution wording quoted above — it must acknowledge
   *ownership of the intellectual property rights*, not merely name the source, and must name both
   portals.
3. **The CLA**, before any outside contribution, if store distribution is still intended.
4. **Confirm in passing that "reproduce" covers deriving new geometry.** The grant enumerates
   browsing, downloading, distributing, reproducing, hyperlinking and printing, and neither portal
   mentions adaptation or derived works — while the pipeline clips, decimates, re-colours, merges and
   derives a road graph that exists in no source file.

   **This is expected to be a non-issue and is listed for completeness.** "Adaptation" is a term of
   art: under the Copyright Ordinance, as under the UK Act it follows, the adaptation right attaches
   to literary, dramatic and musical works — translation, dramatisation, musical arrangement. **There
   is no adaptation right for artistic works;** the restricted act is *copying*, which expressly
   includes making a copy in three dimensions of a two-dimensional work and vice versa. For 3D
   models, maps and data compilations, transformation is therefore copying — i.e. *reproduce*, which
   is granted. The word's absence reflects the category of work, not a reservation of rights.

   Corroborating: the Government publishes 3D models for visualisation, CSDI's definition of Spatial
   Data reaches compilations, metadata and APIs, and a grant excluding derived works would prohibit
   most applications built on the portal.

The government terms are revisable by the publisher. Re-read them before launch and before adding a
second city.
