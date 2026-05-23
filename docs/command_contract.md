# LeeScoop command contract

## Canonical trigger

When Anthony says any of these, run the full LeeScoop batch workflow automatically:

- `post 10 articles`
- `post ten new articles`
- `run the LeeScoop batch`
- `make the daily LeeScoop batch`

## Default action

Do this without asking for approval unless a hard blocker appears:

1. Find 5 strong event candidates.
2. Find 5 major local news candidates.
3. Validate / de-duplicate.
4. Write markdown posts.
5. Generate or attach covers.
6. Select the single most interesting active post as the homepage feature and run `python3 scripts/leescoop_posts.py feature --slug <selected-feature-slug>`.
7. Run `npm run build`.
8. Commit and push if the build passes.
9. Report what was created, skipped, featured, or blocked.

## Featured article rule

Every new batch must refresh the featured article deliberately. Pick the strongest overall active post, not just the newest one and not an old stale flag. Use exactly one `featured: true`.

## Stop conditions

Stop only for real blockers:

- missing source material
- duplicate collisions that leave the batch short
- image provider failure without approved fallback
- build failure
- git/push failure
