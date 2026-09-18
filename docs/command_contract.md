# Publishing parent integration contract
All commands run in an isolated publishing checkout. State must be a shared absolute
path across overlapping automation workers; default tmp/publishing is for one checkout.
No command here fetches, invokes a model, generates content, commits, pushes or edits
schedules. `prepare`/`gate` are validation/checkpoint stages, NOT publication claims.

```bash
python3 scripts/publishing_workflow.py --state /ABS/STATE plan
python3 scripts/publishing_workflow.py --config /ABS/config.json route routine
python3 scripts/publishing_workflow.py --config /ABS/config.json route review
python3 scripts/publishing_workflow.py --config /ABS/config.json route image
python3 scripts/publishing_workflow.py --config /ABS/config.json --state /ABS/STATE prepare --run YYYY-MM-DD-am --input /ABS/candidates.json
python3 scripts/publishing_workflow.py --config /ABS/config.json --state /ABS/STATE gate --run YYYY-MM-DD-am --input /ABS/candidates.json
python3 scripts/publishing_workflow.py --state /ABS/STATE status
```
Exit 0 means command succeeded (including no_op); exit 2 means blocked. JSON output.
Ledger and per-run reports/checkpoints use atomic replace under nonblocking flock.
A crash releases OS lock; rerun same id/input to recover. Changed inputs need new id.
Gate revalidates freshness, duplicate state, asset hashes and exact selected payload.
Blocked reports retain reasons; previous good checkpoints never authorize a failed gate.
Parent must hold the SAME workflow.lock across gate/materialization/quality/commit
(using the Python lock helper around an integrated call, not nested CLI locking), so
no overlapping publisher can slip between check and write. External agents changing
files are not controlled by this lock; isolate checkout and recheck exact manifest.
Legacy leescoop_posts.py write now fails closed rather than bypass the checkpoint.
Its feature operation is not part of automated workflow and must not touch old files.

Parent materialization adapter is intentionally not installed by this build: use
leescoop_posts.frontmatter/body_from_summary only on checkpoint selected entries,
write exclusive-create only, preserve existing assets, add direct source link and
nearby label visibly, and rollback only files in its exact own manifest on failure.
Record published candidate keys/commit/URLs in shared ledger under lock only after
verified deployment. Never mark published from prepare/ready. Parent integration must
supply that receipt and reconcile interrupted commits before trying again; existing
article indexing already prevents duplicates on subsequent prepare runs.

Routes: copy registry to operator-owned local config; routine and review start null.
Set explicit provider/model refs only after successful OAuth invocation evidence;
record auth=oauth, verifiedAt, expiresAt, evidence (secret-free receipt/reference).
Use economical verified routine model for extraction, stronger verified review model
for selection and final review. No retired default, unknown-model optimism or silent
fallback. Image additionally requires directOverrideAbsent=true and gpt-image-2.
Configuration attestation is operator evidence, not independent cryptographic proof.

## Recommended schedules (America/New_York; NOT installed)
1. Daily 06:15 (`15 6 * * *`): deterministic plan + routine discovery payload:
   "Run plan; check routine route; collect leads per source budgets; save candidates
   and access/gap report. No images, writes, delegation or publication."
2. Daily 08:15 (`15 8 * * *`): review/prepare payload:
   "Check review route; verify/rank accumulated leads; quality over fill; resolve
   images only after image route proof; prepare+gate; parent-owned scoped publish
   only if all quality/manifest gates pass; report no-op/blocker otherwise."
3. Thu 16:00 (`0 16 * * 4`): weekend gaps payload:
   "Refresh next 0–14 days across underrepresented Lee County areas; dedupe ledger
   and articles; review only material new options; same image/publication gates."
4. Daily 20:30 (`30 20 * * *`): deterministic status/reconciliation payload:
   "Read status and parent publication receipts; report blocked/stale/interrupted
   runs, do not retry generation or publish automatically."

Parent inventory: supplied handoff says seven maintenance jobs, no LeeScoop jobs;
no crontab, unrelated user timers. Not independently re-audited here. Create new jobs
only after route proof, fetch/materialization adapters and final receipts integration;
do not overwrite maintenance jobs. Schedule cron timezone must be explicitly set by
parent in supported scheduler fields, not inferred from server timezone.
