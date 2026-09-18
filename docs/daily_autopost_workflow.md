# LeeScoop publishing workflow
Supersedes fixed 3+1 and Fort Myers quotas. Quality over fill: aim for up to three
strong events and one consequential news brief; zero is a valid no-op. Never make
news compensate for event/cover failure. No new content is created by planning.

1. Deterministic daily source plan: `bash scripts/run_daily_cron.sh`.
2. Parent checks verified routine OAuth route; narrowly collect source-backed leads.
3. Strong verified review route checks facts, usefulness, dates and diversity.
4. Parent resolves covers before prepare. OAuth-only image policy below.
5. Prepare validated checkpoint, inspect rejects/reserves/report; gate immediately
   before materializing exact selected files. See command_contract.md.
6. Parent materializes only checkpoint entries, runs existing quality/build checks,
   checks exact file manifest, then commits/pushes ONLY under separate publication
   authority. This build does not publish. Verify actual deployed title/source/image,
   not just HTTP 200. Record final commit/URLs in a parent receipt.

## Image policy (mandatory)
New generated covers use `openai/gpt-image-2` through verified Codex OAuth only.
Installed OpenClaw docs tools/image-generation.md say OAuth wins over API-key env
when configured UNLESS explicit models.providers.openai opts into direct routing.
Tool listing/configured=true is NOT proof of auth route. Parent must obtain secret-free
route evidence (OAuth profile active, no direct override, effective routing evidence),
record evidence reference and expiry in local config, and verify again after config
changes. No credentials are read by these scripts. No API-key fallback or ComfyUI.
Current image route is UNVERIFIED and blocked. Preserve existing covers and their
provenance. Completed task receipt plus decoded 1216x704 PNG required for events;
queued/running does not count. Missing/invalid covers block the whole selected batch.
News defaults to source/OG images with attribution and source rights/access review;
if unavailable, stop that image-required item, never silently generate art.

Retain coastal cel-shaded editorial art: thick confident outlines, crisp silhouettes,
graphic shadows, tropical Gulf Coast palette; concrete article-specific scenes,
no text, fake lettering, signage, logos or watermarks. No frontend change here.
