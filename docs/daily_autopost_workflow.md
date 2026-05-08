# LeeScoop Daily Autopost Workflow

Goal: one daily assisted run that prepares **10 total LeeScoop posts** for Anthony to review:

- 5 event posts
- 5 major local news posts

## Canonical trigger

If Anthony says any of these (or close variants), treat it as the full LeeScoop batch command and run this workflow automatically:

- `post 10 articles`
- `post ten new articles`
- `run the LeeScoop batch`
- `make the daily LeeScoop batch`

Do not ask for permission again unless a hard blocker appears.

The run must create local files, run the build gate, then commit/push after the build passes.

## Model target

- Preferred discovery model for full 10-post runs: GPT-5.4 through OAuth.
- GPT-5.4 mini through OAuth is acceptable for narrower or follow-up formatting tasks, but it has shown weakness/timeouts on broader discovery passes.
- Keep the model task narrow: collect candidates and return structured JSON. Do not ask the model to directly edit files freestyle.
- If the chosen OAuth route errors or times out, stop and report the model/provider issue instead of silently switching models.

## High-level run order

0. Run preflight before starting a batch:

   ```bash
   npm run preflight
   ```

   This checks git state, candidate-file freshness, basic tooling, and content validation. Warnings are allowed only when intentionally understood.

1. Check event and news sources.
2. Select candidates:
   - 5 top events.
   - 5 major local news items.
3. Return candidates as strict JSON using `prompts/leescoop_daily_gpt54mini.md`.
4. Run duplicate/safety check with `scripts/leescoop_posts.py`.
5. Create markdown posts only for non-duplicates.
6. Handle images according to content type.
7. Run the quality gate:

   ```bash
   npm run quality
   ```

8. Report:
   - created files
   - skipped duplicates with reason
   - image results
   - validation/build result
9. Commit and push the batch after the quality gate passes, then report the result.

## Event selection rules

Use official event pages/calendars first. Pick the top 5 only.

LeeScoop should prefer events that make a local reader say some version of: "oh shit, that's happening?"

Prioritize in this order:
- major recognizable concerts, comedy, touring acts, headline festivals, citywide happenings
- visually unusual or highly shareable events
- big family draws and seasonal happenings with obvious public appeal
- only then smaller community/calendar fillers

Avoid burning slots on low-stakes filler if stronger events exist.

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

LeeScoop is not trying to sound like a sleepy municipal bulletin. When available, prioritize stories with strong headline pull and real local stakes.

Priority stack for news selection:
- police / sheriff / major crime / arrests / public safety operations
- fires, crashes, missing persons, manhunts, evacuations, boil notices, major outages
- government decisions that hit money, traffic, housing, schools, utilities, beaches, recovery, or development
- corruption, lawsuits, raids, fraud, scams, or political conflict with clear public impact
- weird / surprising / highly talkable local stories with broad curiosity value
- only after those, softer civic or feature-style updates

Avoid these unless the day is unusually quiet:
- bland process stories with weak public stakes
- generic human-interest filler
- minor committee/calendar items with no real consequence
- stale deadline reminders or informational notices without urgency

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

If the batch comes up short after duplicate rejection, keep filling from the next-best verified candidates until the target count is met or the source pool is exhausted.

Use:

```bash
python3 scripts/leescoop_posts.py check --input tmp/candidates.json
```

After writing posts, run the stronger site validator:

```bash
npm run validate
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

### Headline writing rule

For both events and news:
- keep titles factual, but do not flatten them into dull generic summaries
- preserve the strongest truthful hook from the source when possible
- prefer punchy, specific titles over bland institutional phrasing
- do not add clickbait that the source cannot support

Bad:
- `Cape Coral council approves new mobility fee plan`

Better:
- `Cape Coral approves new mobility fees tied to long-term road and infrastructure funding`

## Image handling

### Event posts

Event posts get generated LeeScoop-style cover art. Use the best available generator first, not the local fallback by habit.

Current preferred path:

1. Try OpenClaw internal image generation with `openai/gpt-image-1.5`, `1536x1024`, high quality.
   - `openai/gpt-image-2` is preferred when available, but this account currently returns an organization-verification block.
   - Google image generation currently has no usable key in this agent.
2. Crop/resize the accepted generated image to `1216x704`.
3. Save it under `public/covers/<slug>.png`.
4. Use local ComfyUI only as a fallback, or when Anthony explicitly asks for local ComfyUI.

Local fallback path:

```bash
python3 scripts/generate_comfy_cover.py --slug <slug> --subject "<generic visual concept>"
```

Rules:

- Use concrete scene prompts, not exact event titles/artist names/business names unless visually necessary.
- No text, words, signage, logos, captions, or fake lettering.
- Avoid generic black mascot/blob compositions; make each cover article-specific and locally grounded.
- Default final size: `1216x704`.
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
(short unique subject prompt:1.3), polished cel-shaded editorial illustration, thick confident outlines, cute but clean cartoon style, scene-specific composition, recognizable setting details, sharp silhouettes, graphic shadows, true black accents, clean simple shapes, high contrast, bold readable composition, modern vector-like finish, tropical Gulf Coast energy, playful but not childish, Florida-inspired color palette, #07506F, #197894, #4FA7BC, #8BD2DE, #D94B32, #F28B42, #F7DE69, #F8F3E8, #063A52, #DDEEF1
```

Negative prompt:

```text
nsfw, muddy colors, low contrast, thin outlines, bad anatomy, extra limbs, blurry, text, words, letters, typography, captions, signage, logos, watermark, dull palette, overly realistic rendering, generic black mascot, black blob character, empty arena, demon mascot, ghost mascot, oversized monster, featureless silhouette
```

### Local news posts

News posts should have a visual. Use this order:

1. Prefer a real/source image when available.
2. Actively look for the page's `og:image` or primary article image first.
3. Only use/download the image if it clearly comes from the same official/news source domain as `sourceUrl` or `verificationUrl`, or from that publisher's obvious first-party image/CDN setup.
4. Save it into `public/covers/<slug>.<ext>` and preserve the source image URL in the run report or frontmatter note when available.
5. If no usable same-source image exists, use approved fallback art generation.

Generated local-news images must follow the same no-text/no-logo rule as events: no exact business names unless visually necessary, no captions, no signs, no fake lettering, no official seals/logos.

## Build gate

Always run:

```bash
npm run build
```

If the build fails, stop and report the error.

## Publish gate

If the build passes, commit and push the batch.
