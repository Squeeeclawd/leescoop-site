# September 10, 2026 — ten-event release

Status: COMPLETE — all ten articles and covers verified live September 11, 2026 at 19:18 EDT. Release commit `fe363beabd506b96c062e00f33163c2791612219` is pushed to main.

## Recovery checkpoint — September 11, 2026

The initial ArtLab generation failed from provider overload. A successful retry was delivered and installed by the parent as a 1216x704 PNG. No substitute artwork or duplicate pending task was used. All ten covers pass PNG/dimension and frontmatter-reference checks; all nine protected hashes remain intact. Posting/deployment plans now require verified-live completion and retained continuation ownership. Schedules unchanged. Configured-authentication GPT Image 2 generation succeeded; OAuth specifically is not asserted.

## Scope

Ten new event briefs (eight Fort Myers, two Cape Coral), with generated no-text editorial covers, and homepage date-window discovery fixes. Pre-existing unrelated dirty/untracked assets are excluded from this release.

## Checked official sources

- [A gamer-themed Halloween family concert is coming to Barbara B. Mann](https://www.bbmannpah.com/events/detail/symphony-press-play-halloween-2026) — `/press-play-gamers-halloween-family-concert-fort-myers-2026/`
- [Edison Ford is turning Halloween into a daytime fall festival](https://www.edisonfordwinterestates.org/events/fall-festival/) — `/edison-ford-fall-festival-fort-myers-2026/`
- [Florida Rep opens Neil Simon’s fast-moving comedy in October](https://www.floridarep.org/show/neil-simons-the-star-spangled-girl/) — `/star-spangled-girl-florida-rep-fort-myers-2026/`
- [Florida Rep brings the thriller Wait Until Dark to the Arcade Theatre](https://www.floridarep.org/show/wait-until-dark/) — `/wait-until-dark-florida-rep-fort-myers-2026/`
- [Alliance brings a Sunday songwriter concert to the Foulds Theatre](https://www.artinlee.org/event/for-the-love-of-music-vol-iv/) — `/for-the-love-of-music-vol-iv-alliance-fort-myers-2026/`
- [Cirque du Soleil’s holiday show is headed to Fort Myers](https://www.bbmannpah.com/events/detail/twas-the-night-before-cirque-du-soleil-2026) — `/cirque-night-before-christmas-bbmann-fort-myers-2026/`
- [Cape Coral Bike Night returns to SE 47th Terrace in October](https://www.ccbikenight.com/) — `/cape-coral-bike-night-october-2026/`
- [Cape Coral’s free Trunk or Treat adds a drone show and Halloween movie](https://www.capecoral.gov/community/special_events/trunk_or_treat.php) — `/cape-coral-trunk-or-treat-halloween-movie-2026/`
- [Downtown Fort Myers farmers market gets a bigger fall footprint](https://fortmyers.gov/Calendar.aspx?EID=7238&month=10&year=2026&day=10&calType=0) — `/fort-myers-culinary-district-market-expansion-2026/`
- [Free Family ArtLab returns to the Alliance on September 19](https://www.artinlee.org/event/family-artlab-at-the-alliance-4/2026-09-19/) — `/family-artlab-alliance-fort-myers-september-2026/`

## Corrections and source limitations

- Cirque includes Nov. 13 at 7 p.m. and Nov. 14 at 1 and 4 p.m. Its actual final curtain time is not given. The stored end-of-day value is explicitly documented as an editorial listing expiry, not a performance duration.
- Songwriter concert ends at 5 p.m.; the 2:30 p.m. time is doors. Explicit end preserves correct expiry despite three clock values in the display text.
- Farmers market ends at 1 p.m. Exact street location is not supplied by the official event record; the city footer address is not presented as the market address.
- Florida Rep calendar confirms run boundary timestamps, not every individual performance runtime.
- Family ArtLab is a morning event distinct from the same venue’s evening Sock Hop; deduplication now uses normalized start time plus venue, while exact-source duplicate checks remain.

## Verification

- Source/date/filter tests passed; detailed results in `event_discovery_ux_notes_2026-09-10.md`.
- Browser navigation was policy-blocked. DOM fixture tests and build evidence do not substitute for rendered desktop/mobile verification.
- Final content validation, clean release build and live HTTP checks will be recorded after artwork completion.

## Final local gate evidence

September 11: npm validate passed (existing past-event warnings retained); npm check passed with zero errors/warnings and one unused-variable hint. Date/filter regressions, civil-window/DST tests, discovery DOM fixture tests and six Python tests passed. Constrained build and Pagefind completed successfully. All ten PNGs are 1216x704; all nine protected hashes match. Rendered visual browser check remains unverified due to policy restriction.

## Production evidence — 2026-09-11T23:18:40.292780+00:00

All ten routes returned HTTP 200 with expected title, official source URL and cover reference. Every cover decoded as PNG 1216x704 and matched its committed local file SHA-256 (no HTML fallback). Homepage contains Today, This weekend and Next 14 days date chips. Exact committed-tree constrained build passed independently of unrelated dirty/untracked user files. All nine protected hashes remain unchanged and excluded.

- https://leescoop.com/press-play-gamers-halloween-family-concert-fort-myers-2026/ — page 200; title/source verified; cover 200, PNG 1216x704, hash matched.
- https://leescoop.com/edison-ford-fall-festival-fort-myers-2026/ — page 200; title/source verified; cover 200, PNG 1216x704, hash matched.
- https://leescoop.com/star-spangled-girl-florida-rep-fort-myers-2026/ — page 200; title/source verified; cover 200, PNG 1216x704, hash matched.
- https://leescoop.com/wait-until-dark-florida-rep-fort-myers-2026/ — page 200; title/source verified; cover 200, PNG 1216x704, hash matched.
- https://leescoop.com/for-the-love-of-music-vol-iv-alliance-fort-myers-2026/ — page 200; title/source verified; cover 200, PNG 1216x704, hash matched.
- https://leescoop.com/cirque-night-before-christmas-bbmann-fort-myers-2026/ — page 200; title/source verified; cover 200, PNG 1216x704, hash matched.
- https://leescoop.com/cape-coral-bike-night-october-2026/ — page 200; title/source verified; cover 200, PNG 1216x704, hash matched.
- https://leescoop.com/cape-coral-trunk-or-treat-halloween-movie-2026/ — page 200; title/source verified; cover 200, PNG 1216x704, hash matched.
- https://leescoop.com/fort-myers-culinary-district-market-expansion-2026/ — page 200; title/source verified; cover 200, PNG 1216x704, hash matched.
- https://leescoop.com/family-artlab-alliance-fort-myers-september-2026/ — page 200; title/source verified; cover 200, PNG 1216x704, hash matched.

Rendered desktop/mobile browser verification remains unverified: browser navigation was policy-blocked. HTTP/content checks and DOM fixture tests are the verified evidence. No schedules were changed or new monitoring routines added.
