# LeeScoop command contract

## Canonical trigger

When Anthony says any of these, run the full LeeScoop batch workflow automatically:

- `run the LeeScoop autopost`
- `post today's LeeScoop batch`
- `run the LeeScoop batch`
- `make the daily LeeScoop batch`

An explicit numeric request overrides the four-post daily default. Unless Anthony specifies another mix, keep larger manual batches close to the same event-heavy 3:1 ratio. Larger requests must also use the proportional lead, verification, backup, source-family, and venue-diversity rules in `docs/event_discovery_sources.md`.

## Default action

Do this without asking for approval unless a hard blocker appears:

1. Run `docs/event_discovery_sources.md` and gather at least 12 Fort Myers/Lee County event leads.
2. Fully verify and rank at least 8 non-duplicate event candidates plus 3 major local news candidates.
3. Publish exactly 3 events + 1 news brief; at least 2 event listings must use `city: Fort Myers`.
4. Validate / de-duplicate and retain backups until covers are complete.
5. Write markdown posts.
6. Generate or attach covers.
7. Select the single most interesting active post as the homepage feature and run `python3 scripts/leescoop_posts.py feature --slug <selected-feature-slug>`.
8. Run `npm run quality`.
9. Commit and push if the quality gate passes.
10. Report what was created, skipped, featured, or blocked.

## Featured article rule

Every new batch must refresh the featured article deliberately. Pick the strongest overall active post, not just the newest one and not an old stale flag. Use exactly one `featured: true`.

## Stop conditions

Stop only for real blockers:

- missing source material
- duplicate collisions that leave the batch short
- image provider failure without approved fallback
- build failure
- git/push failure
