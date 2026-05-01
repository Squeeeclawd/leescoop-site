# LeeScoop Daily Autopost Workflow

Goal: one daily assisted run that prepares **10 total LeeScoop posts** for Anthony to review:

- 5 event posts
- 5 major local news posts

The run must create local files only, run the build gate, and wait for Anthony before commit/push.

## Model target

- Intended cron model: GPT-5.4 mini through OAuth.
- Keep the model task narrow: collect candidates and return structured JSON. Do not ask the model to directly edit files freestyle.
- If the OAuth mini route errors, stop and report the model/provider error instead of silently switching models.

## High-level run order

1. Check event and news sources.
2. Select candidates:
   - 5 top events.
   - 5 major local news items.
3. Return candidates as strict JSON using `prompts/leescoop_daily_gpt54mini.md`.
4. Run duplicate/safety check with `scripts/leescoop_posts.py`.
5. Create markdown posts only for non-duplicates.
6. Handle images according to content type.
7. Run `npm run build`.
8. Report:
   - created files
   - skipped duplicates with reason
   - image results
   - build result
9. Wait for Anthony approval before any commit/push.

## Event selection rules

Use official event pages/calendars first. Pick the top 5 only.

Do not select five events from the same source unless there are no other valid options. Prefer variety across:

- city
- venue
- date
- event type
- source

Preferred sources:

- Visit Fort Myers events
- Lee County Government events
- City of Fort Myers calendar
- Cape Coral city calendar / special events
- Bonita Springs city calendar
- Village of Estero events
- Fort Myers Beach calendars
- Sanibel city calendar
- Lee County Library events
- Local chambers
- Caloosa Sound Amphitheater
- Hertz Arena
- Barbara B. Mann
- Alliance for the Arts
- Sidney & Berne Davis Art Center
- Edison and Ford Winter Estates
- Broadway Palm
- Players Circle Theater
- Eventbrite
- Meetup
- Fun 4 Fort Myers Kids
- Welcome to Lee County calendar
- Reddit: r/FortMyers and r/CapeCoral
- Facebook event groups/pages as leads only

Treat Facebook, Reddit, Meetup, and Eventbrite as leads unless the event source is clear.

## News selection rules

Pick the top 5 major local news items only. Avoid minor filler.

Freshness rules:

- Prefer items published in the last 7 days.
- Reject news older than 21 days unless Anthony explicitly asks for a catch-up item.
- Reject items with expired deadlines, expired claim windows, or stale event-dependent information.

Lead sources:

- WINK News
- Gulf Coast News / WBBH-WZVN
- Gulf Coast ABC / WZVN-TV
- Cape Coral Breeze
- Fort Myers Beach Observer / Beach Bulletin
- The News-Press
- WGCU
- Florida Weekly Fort Myers
- Beach Talk Radio News

Verify with official/public-record sources when possible:

- Lee County Government news releases
- Lee County Sheriff’s Office
- LCSO Public Information Office
- School District of Lee County
- Lee County Clerk press releases
- Florida Department of Health in Lee County
- FHP traffic/crash reports
- FL511
- FDOT Lee County RoadWatch
- Lee County Elections

## Duplicate prevention

Before writing a post, check `src/content/articles/*.md` for:

- same normalized title
- same source URL
- same slug / filename
- same event date + venue for events

If a duplicate is found:

- skip it
- choose another item if the run still needs quota
- never overwrite existing posts

Use:

```bash
python3 scripts/leescoop_posts.py check --input tmp/candidates.json
```

## Markdown creation

Use:

```bash
python3 scripts/leescoop_posts.py write --input tmp/candidates.json
```

The writer creates short LeeScoop briefs under:

```text
src/content/articles/<slug>.md
```

Required event fields:

- title
- eventDate
- eventTime
- city/location
- venue
- short description / excerpt
- sourceUrl
- category
- tags if useful

Required news fields:

- title/headline
- date
- city/location if relevant
- brief summary / excerpt
- sourceUrl
- category
- tags if useful

## Image handling

### Event posts

Event posts get generated LeeScoop-style cover art.

Current local generation path:

```bash
python3 scripts/generate_comfy_cover.py --slug <slug> --subject "<generic visual concept>"
```

Rules:

- Use generic visual concepts, not exact event titles/artist names/business names unless visually necessary.
- No text, words, signage, logos, captions, or fake lettering.
- Default size: `1216x704`.
- Save generated event covers as:

```text
public/covers/<slug>.png
```

Frontmatter:

```yaml
coverImage: /covers/<slug>.png
```

Current positive style block:

```text
(short unique subject prompt:1.3), cel shaded, thick outlines, cute but weird cartoon, angular cartoon energy, exaggerated expressive, sharp jagged shapes, slightly chaotic sci-fi humor, spooky-cute proportions, sharp silhouette, graphic shadows, true black, clean simple shapes, high contrast, bold readable design, modern vector-like finish, #07506F, #197894, #4FA7BC, #8BD2DE, #D94B32, #F28B42, #F7DE69, #F8F3E8, #063A52, #DDEEF1
```

Negative prompt:

```text
nsfw, muddy colors, low contrast, thin outlines, bad anatomy, extra limbs, blurry, text, words, letters, typography, captions, signage, logos, watermark, dull palette, overly realistic rendering
```

### Local news posts

News posts should have a visual. Use this order:

1. Prefer a real/source image when available.
2. Only use/download the image if it clearly comes from the same official/news source domain as `sourceUrl` or `verificationUrl`.
3. Save it into `public/covers/<slug>.<ext>` and preserve the source image URL in the run report or frontmatter note when available.
4. If no usable same-source image exists, generate LeeScoop-style cover art using a generic visual concept based on the news item.

Generated local-news images must follow the same no-text/no-logo rule as events: no exact business names unless visually necessary, no captions, no signs, no fake lettering, no official seals/logos.

## Build gate

Always run:

```bash
npm run build
```

If the build fails, stop and report the error. Do not commit/push.

## Approval gate

The daily run must not commit or push. It reports local changes and waits for Anthony.
