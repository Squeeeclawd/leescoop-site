# File-based publishing health

Run `python3 scripts/publishing_health.py --state /home/shmee/.openclaw/workspace/state/leescoop-publishing` for read-only JSON and exit status (0: no actionable file findings; 1: action required). `--now` accepts an offset timestamp for tests only.

The checker distinguishes due discovery/review reports, review-only holds, active leases, no-op runs, and finalized content backed by matching source/title/cover/deployment receipt and selected ledger identities. Unpublished rejected reserves do not invalidate a mixed finalized batch. `publishable:false` alone is not a preview: legitimate no-op reports remain valid.

Historical receipts lacking checkpointHash are labelled `legacy_ledger_hash_matched_checkpoint_unbound`, not silently upgraded. Invalid receipts, stale/malformed reports and pending release state are actionable. Scheduler enablement is not inspected. Timed unattended publication stays `unproven`: a local JSON report, scheduler status=ok, or one assisted release cannot establish it. Report that separate limitation even when the command exits 0.

This command does not repair state, contact sources, use models, or trigger publication. Committed/pushed recovery requires the guarded parent procedure, not deletion of a lock or lease.

The observed nested discovery report format (`run` plus `sourceAccess`) is recognized only when its source journal is inside canonical state, hash-matched, run-matched, dated consistently, and within per-run/per-host pacing limits. Unknown archived report shapes are not fresh evidence; an unrecognized current canonical report is actionable.

Routine/review report actual models, and API when configured, are compared against `routes.routine.model` / `routes.review.model` and optional `api` in the default source config (or `--config`). This is a shape/model-consistency check, not successful-inference proof. A changed route can mark older reports mismatched; retain those records and produce fresh reports instead of rewriting their model fields.
