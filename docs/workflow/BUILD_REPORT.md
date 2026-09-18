# Workflow build — 2026-09-18
Base fetched origin/main: daccb0ee5828d5c64c7bba5fd2713e6e5339e05f.
Fresh isolated worktree: /home/shmee/Desktop/leescoop-publishing-2026-09-18.
No frontend/content generation, network source fetching, scheduler writes or push.

Passed:
- `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s scripts -p 'test_*.py'`: 18 tests, including real competing process lock, failed report/resume, changed-asset gate rejection, dates/ongoing ranges, dedupe, missing/corrupt/wrong-size covers, OAuth defaults and legacy writer block.
- `node scripts/test_event_dates.mjs`: 17 assertions.
- `node scripts/test_event_discovery.mjs`: real inline-script suite plus 6 boundary assertions.
- `npm run quality`: Astro check, 368-article validation, build, Pagefind; existing expired-event warnings and Pagefind legacy UI notice, no errors.
- `bash -n scripts/run_daily_cron.sh`; `git diff --check`.
- All 10 original protected paths match provided backup SHA256 hashes.

First JS attempt lacked dependencies in fresh worktree. Copied existing node_modules
from original checkout, never installed packages or modified original dependencies;
reran JS and full quality successfully. Logs /tmp/leescoop-workflow-{tests,quality}.log.

Missing setup before autonomous publication: verified routine/review model routes,
secret-free proof of image OAuth without explicit direct-route override, permitted
source adapters/cache, parent scoped materialization and deployment receipt integration,
shared absolute state/lock and scheduler creation. These are intentionally not claimed
working. Empty routes fail closed. Existing covers remain untouched. Legacy writer is
disabled until parent integration, rather than preserving an unsafe alternate path.

The control plane performs selection/checkpoint/validation only, not full automated
publishing. Source registry URLs are unverified seeds. Network budgets are adapter
contracts, not claimed enforced fetching. Candidate factual review and configuration
attestation still require the parent; flags are not independent proof of truth.

Recommended schedule and exact command/payload contracts: ../command_contract.md.
