# Event discovery UX notes — 2026-09-10

Focused implementation scope: homepage discovery only, with no article or cover edits.

## Evidence checked

- Live `https://leescoop.com/` showed search, Events/Local News, and area filters, but no date-window controls.
- Live static page still listed expired September 4 and September 5 event cards on September 10, so date filters must not rely only on build-time filtering.
- Existing event discovery docs prioritize actionable near-term windows, including `0-14 days`, and the user called out today/this-weekend stale logic.

## Implemented

- Added runtime date-window filters on the homepage: Today, This weekend, Next 14 days.
- Date-window counts recompute with the existing search, type, and area filters.
- Event cards include Lee County date keys and event active-until cutoffs for client-side expiry checks.
- The homepage script hides expired event cards at runtime before applying counts/filters, reducing stale static-build fallout.
- Date formatting and date keys use `America/New_York` explicitly.
- `src/lib/content.ts` now supports `LEESCOOP_NOW` for deterministic build/check runs while remaining compatible with existing `filter(isPublished)` call sites.

## Suggestion cards / out of scope for this focused pass

1. **Deploy freshness monitor:** add a scheduled deploy/cache health check that flags when live homepage events are past their archive cutoff. This is the real fix for stale static builds.
2. **Dedicated events archive/calendar page:** homepage chips are useful, but a full calendar view should be a separate small feature, not crammed into the hero/feed.
3. **Hero stale fallback:** runtime hiding prevents an expired featured event from staying prominent, but a future pass could promote the next non-expired tile client-side if stale deploys keep happening.


## Implementer verification — September 10, 2026

Working model: `openai/gpt-6-astra`. Sole implementer; no subagents. Memory search unavailable due quota (request-provided limitation); used this saved note, `tmp/events-2026-09-10-status.md`, git diff/status, schema and local source instead. Earlier live-site observations above are prior saved evidence, not a new live browser verification.

### Reviewed and fixed

- Preserved existing uncommitted discovery UI, Python start-time duplicate identity, and optional `eventEndDate` writer changes; Python regressions verify equivalent offsets, distinct same-venue times, same-source protection, and end-date output.
- Explicit `eventEndDate` is now the exact archive cutoff, not rounded to 23:59. Existing strict `< now` boundary retained: active at cutoff, archived one millisecond later.
- Inferred range end validates 1–12 hours and 0–59 minutes; malformed clocks fall back to day-end. Doors/show descriptions are not mistaken for ranges.
- Homepage interval end keys use the archive cutoff, fixing overnight carryover into Today/weekend/next14.
- Today means Lee County civil day; weekend is Saturday–Sunday (on Sunday includes current weekend); next14 is today plus 13 civil days. Ongoing runs overlap these windows; expired runs do not.
- Each filter refresh uses one clock snapshot, eliminating counts/window inconsistency at midnight. Date counts no longer temporarily mutate filter state. Empty datasets initialize controls instead of returning early.
- Date chips select Events; selecting Local News clears the date window. Search, area, and runtime expiry remain combined. Counts reflect the resulting facet choice.
- Preserved scoped `[hidden] { display: none !important }` safeguards, added visible keyboard focus to date chips, timezone/window help text, grouped date controls and empty-state status semantics. Reset also handles nested click targets.
- Cached the library civil-date formatter instead of repeatedly constructing ICU formatters during sorting/static-route generation.

### Exact regression/check commands

Run from `/home/shmee/Desktop/leescoop`:

```sh
for zone in UTC Pacific/Honolulu Asia/Tokyo; do
  TZ="$zone" node scripts/test_event_dates.mjs &&
  TZ="$zone" node scripts/test_event_discovery.mjs || exit
done
PYTHONDONTWRITEBYTECODE=1 python3 scripts/test_event_posts.py
git diff --check
NODE_OPTIONS=--max-old-space-size=2048 npm run check
PYTHONDONTWRITEBYTECODE=1 npm run validate
MALLOC_ARENA_MAX=2 UV_THREADPOOL_SIZE=2 NODE_OPTIONS=--max-old-space-size=2048 npm run build
```

Results: all JS regressions passed in all three host timezones, including exact ends, DST, overnight ranges, invalid clocks, array callback compatibility, actual homepage inline-script execution against deterministic DOM/clock fixtures, facet counts, news switching, search/reset, expiry refresh, Sunday/midnight, and six civil window boundary assertions including year rollover. Six Python tests passed. `git diff --check` passed. Astro check: 55 files, zero errors, zero warnings, one existing unused `searchTargetId` hint in out-of-scope `Header.astro`.

First constrained build succeeded: 1,074 static pages in 28.59 seconds; Pagefind indexed 740 pages / 4,740 words; process exit 0. No killed/OOM result. Final build rerun after the keyboard-focus CSS addition is recorded below.

### Browser result and remaining limitations

Read browser-automation skill first. Browser status reported running/CDP/page ready on port 18800; tabs showed one about:blank tab. Attempted `browser.open` for task label `leescoop-event-verification` at `http://127.0.0.1:4329/`, served by task-owned `python3 -m http.server 4329 --bind 127.0.0.1 --directory dist`. Browser tool rejected navigation: **browser navigation blocked by policy**. No bypass, browser restart, port collision fix, or unrelated service intervention attempted. Consequently real rendered desktop/mobile layout, computed hidden styles, and browser click verification remain unverified. DOM-fixture regressions are not represented as browser proof.

Validation inspected 371 articles and exited 1 for eight parent-owned missing covers (plus existing stale-event warnings): cape-coral-bike-night-october-2026, cape-coral-trunk-or-treat-halloween-movie-2026, cirque-night-before-christmas-bbmann-fort-myers-2026, family-artlab-alliance-fort-myers-september-2026, for-the-love-of-music-vol-iv-alliance-fort-myers-2026, fort-myers-culinary-district-market-expansion-2026, star-spangled-girl-florida-rep-fort-myers-2026, wait-until-dark-florida-rep-fort-myers-2026. Parent should finish covers and rerun validate before publication. Build success does not mean cover validation passed.

Schema coerces event dates to Date, so date-only versus timestamp intent cannot be recovered here: explicit ends are exact instants, and publishers should supply offset-bearing timestamps. Events without an explicit end or clear range retain Lee County day-end fallback. Multi-day runs represent continuous date overlap, not individual performance schedules. Runtime refresh is every 60 seconds / visibility return, not a precise end-time timer. Hero hides on expiry but does not promote a replacement. Header/ticker freshness and newly published content still need a new static build; no deployment was performed.

### Protected-file evidence

SHA-256 comparison against read-only `tmp/events-2026-09-10-protected.json`: **9/9 MATCH**. No protected file restored or modified. Hashes observed:

- `public/covers/bash-on-the-bay-fort-myers-beach-2026.png`: `2486599f44cf5a2b89b0f7b056ecf057c6887d9e9d48f71ad3fd0856ec370b20` — MATCH
- `public/covers/summerween-fort-myers-brewing-2026.png`: `685571558824297c1d76c4594490f0c91926336519ee901f12fdcb622a09358b` — MATCH
- `public/covers/the-shark-is-broken-broadway-palm-fort-myers-2026.png`: `88aed8ef2a187365e30e8f5b1e78a653e7eca47ef9e11a7aaf94317910c0c37e` — MATCH
- `public/covers/dayshift-nostalgia-dance-party-ranch-fort-myers-2026.png`: `f03314a544d73ac91a2fe27f30e61fede107b6d46a57aeeb9ef38be8876b8a15` — MATCH
- `public/covers/october-gallery-opening-alliance-fort-myers-2026.png`: `8cff06133794e1847d6309b98973fbe6dc13de0d9d4221e8e5eede68a7e0c536` — MATCH
- `public/covers/vintage-market-days-north-fort-myers-2026.png`: `a1102d405d5c65fca8e27772498c3451f74eb422c3c19e8a3028777788bbb7cd` — MATCH
- `src/content/articles/dayshift-nostalgia-dance-party-ranch-fort-myers-2026.md`: `3831d27e50dbfaf635e7b3cdc71d9c261fdd29d1982a5daba09412af6335e2e2` — MATCH
- `src/content/articles/october-gallery-opening-alliance-fort-myers-2026.md`: `76e3f30ec66f29465410615457a4c47ed77d80b10b3fb7d4c5cab3cf5ea53c8c` — MATCH
- `src/content/articles/vintage-market-days-north-fort-myers-2026.md`: `45ec663d4d439b0bbd58a4049ac6da8b48910b332a3c3839b58682cfe1cbf3e5` — MATCH

No article/cover edits, commits, pushes, deployments, gateway configuration changes, broad cleanup, or unrelated service stops performed. Existing dirty/untracked parent work was preserved. Only owned source/tests/notes were edited; normal requested Astro build outputs were generated.

### Final verification result

Final-source rerun: `set -o pipefail; NODE_OPTIONS=--max-old-space-size=2048 npm run check && MALLOC_ARENA_MAX=2 UV_THREADPOOL_SIZE=2 NODE_OPTIONS=--max-old-space-size=2048 npm run build | tail -35` exited **0**. Astro checked 56 files with zero errors/warnings and the same one Header hint. Final Pagefind output: 1,074 HTML files found, 740 pages indexed, 4,740 words, finished in 0.695 seconds. The task-owned verification server was terminated via its process handle; no unrelated service was stopped.

Final protected recheck: all nine SHA-256 values still match the manifest.
