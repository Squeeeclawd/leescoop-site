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
6. Run `npm run build`.
7. Commit and push if the build passes.
8. Report what was created, skipped, or blocked.

## Stop conditions

Stop only for real blockers:

- missing source material
- duplicate collisions that leave the batch short
- image provider failure without approved fallback
- build failure
- git/push failure
