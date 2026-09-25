# Unlimited reviewed release handoff (2026-09-25)

This repair is code/tests/docs only. It does not publish content or attest replacement models.

## Parent prerequisites

1. Integrate the tested workflow commit into the production branch through a clean checkout; never use the protected dirty primary. Check remote HEAD before integration. Create a fresh isolated release worktree from the resulting production HEAD. The guarded content push requires remote main to equal the prepared base, so do not prepare content on top of an unpushed workflow/config commit.
2. Refresh tested routine/reviewer routes and reviewer sessionKey in `docs/workflow/sources.json` as described in `../command_contract.md`; set `model` to the actual assistant provider/model and `api` when observed, while keeping requested aliases only in `requestedModel` for audit. Commit/integrate those updates before prepare. Existing route values were preserved, not re-certified. The retired mini-named prompt is already only a compatibility pointer. The former receipt/health Sol hardcoding is now config-driven, matching the release gate.
3. Inspect canonical state with `status`. Preserve legacy ledger/checkpoint records. Resolve any active lease through its original workflow or safe pre-commit abort; never delete lease/journals. Committed remote-moved recovery still requires parent investigation.
4. Read `/home/shmee/.openclaw/workspace/artifacts/leescoop-ten-events-2026-09-25/manifest.json`, `FINAL.md`, `validation-report.md`, drafts and source receipts. Those are external unpublished drafts, not checkpoint input. Recheck actual title/date/time/venue evidence, freshness, registry membership and dedupe against current production and protected drafts. Use the existing recorded source-access run/journal; do not reset budgets to force ten successes. Fix factual blockers rather than asserting verified flags. Multiple reviewed events from the same organizer are allowed.
5. Complete all ten covers with exact `openai/gpt-image-2` OAuth route proof and real generation task evidence; decode/crop to 1216x704 PNG. Copy only final selected covers into the release checkout. No cover generation was performed by this repair.
6. Obtain actual routine/review jobs and immutable input/report hash bindings. Export the review step using the helper with the actual stored session ID and the same config. Assemble the candidate JSON per `prompts/leescoop_candidates.md`, with ten fully reviewed items and final asset paths/evidence. Keep it outside the worktree. Do not copy unreviewed Markdown directly into the site or fabricate receipt fields.

## Exact release sequence after prerequisites

Set RELEASE to the fresh release checkout, not the workflow repair worktree. Use a new run ID; the example below must not replace an existing terminal run.

```bash
export LEESCOOP_RELEASE=/absolute/path/to/fresh-release-worktree
export LEESCOOP_STATE=/home/shmee/.openclaw/workspace/state/leescoop-publishing
export LEESCOOP_RUN=2026-09-25-ten-events-unlimited
cd "$LEESCOOP_RELEASE"
export LEESCOOP_INPUT="$LEESCOOP_STATE/inbox/$LEESCOOP_RUN-candidates.json"
python3 scripts/publishing_workflow.py --state "$LEESCOOP_STATE" status
python3 scripts/publishing_workflow.py --state "$LEESCOOP_STATE" route routine
python3 scripts/publishing_workflow.py --state "$LEESCOOP_STATE" route review
python3 scripts/publishing_workflow.py --state "$LEESCOOP_STATE" route image
python3 scripts/publishing_workflow.py --state "$LEESCOOP_STATE" prepare --run "$LEESCOOP_RUN" --input "$LEESCOOP_INPUT"
python3 scripts/publishing_workflow.py --state "$LEESCOOP_STATE" gate --run "$LEESCOOP_RUN" --input "$LEESCOOP_INPUT"
# Inspect report/checkpoint: exactly the ten intended slugs, no rejects, complete asset hashes.
# If not exact: stop, safely abort before commit intent, correct evidence, use a new run ID.
python3 scripts/publishing_workflow.py --state "$LEESCOOP_STATE" materialize --dry-run --run "$LEESCOOP_RUN" --input "$LEESCOOP_INPUT" --release-root "$LEESCOOP_RELEASE"
python3 scripts/publishing_workflow.py --state "$LEESCOOP_STATE" materialize --run "$LEESCOOP_RUN" --input "$LEESCOOP_INPUT" --release-root "$LEESCOOP_RELEASE"
python3 scripts/publishing_workflow.py --state "$LEESCOOP_STATE" quality --run "$LEESCOOP_RUN" --release-root "$LEESCOOP_RELEASE"
python3 scripts/publishing_workflow.py --state "$LEESCOOP_STATE" commit --run "$LEESCOOP_RUN" --release-root "$LEESCOOP_RELEASE" --message "Publish ten reviewed LeeScoop events"
python3 scripts/publishing_workflow.py --state "$LEESCOOP_STATE" push --run "$LEESCOOP_RUN" --release-root "$LEESCOOP_RELEASE" --remote origin --branch main
# Parent now verifies exact production commit/deployment and ALL ten titles, source links,
# canonical routes, cover hashes and decoded assets; write the real receipt schema.
python3 scripts/publishing_workflow.py --state "$LEESCOOP_STATE" finalize --run "$LEESCOOP_RUN" --receipt "$LEESCOOP_STATE/inbox/$LEESCOOP_RUN-live-receipt.json"
python3 scripts/publishing_workflow.py --state "$LEESCOOP_STATE" status
```

Run commands sequentially and stop on any nonzero status. Do not continue from a partial selection just because prepare returned success. If midnight intervenes, preserve freshness guards and abort/rebuild safely before commit; never alter recorded days. Parent must update automation payloads to use configured routes, unlimited-reviewed selection, editorial targets (not caps), unchanged source budgets and the same release contract. Gateway/scheduler edits are outside this repair.

## Async cover-generation recovery

If an image task is accepted but the cover child exits before artifact edits, keep the accepted task ID with its slug/output path and wait for the original task completion. Resume the same visible child with `sessions_send`; do not generate a duplicate. Inspect, crop/format, hash and bind the completed artifact before candidate prepare/gate. Use the parent progress card for status; do not add dashboard widgets for this workflow.
