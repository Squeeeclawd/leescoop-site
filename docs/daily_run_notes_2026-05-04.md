# LeeScoop daily run notes — 2026-05-04

## Goal
Prepare 10 fresh LeeScoop posts using the GPT-5.4-mini OAuth workflow, then verify the site build and note anything that broke.

## Outcome
- Fresh 10-post batch created successfully.
- Duplicate/safety check passed.
- Local ComfyUI fallback was approved and used to generate covers for all 10 posts.
- `npm run build` passed.

## Fresh posts created
### Events
1. `monthly-music-walk-may-15-2026`
2. `palm-city-cinema-lilo-and-stitch-may-8-2026`
3. `cape-coral-hurricane-expo-may-30-2026`
4. `acma-rb-stone-concert-may-9-2026`
5. `vince-gill-50-years-from-home-june-25-2026`

### News
1. `cape-coral-parkway-east-lane-closures-may-11-2026`
2. `fort-myers-beach-pier-rebuild-2027`
3. `lee-county-beach-shoreline-project-funding-2026`
4. `cape-coral-seven-islands-development-deal-2026`
5. `cape-coral-mobility-fees-approved-2026`

## What went wrong
### 1) Prior batch contamination
A previous untracked draft batch was sitting inside live content and covers directories. Some of those posts were already stale or past-dated for 2026-05-04.

Action taken:
- moved that batch to `tmp/failed_batch_2026-05-01/`

### 2) GPT-5.4-mini OAuth candidate run timed out
The subagent did useful research but timed out before returning final JSON.

What helped:
- salvage partial research from session history
- manually compile a validated candidate batch from verified source material

Improvement:
- split the workflow into two smaller model steps:
  1. source discovery
  2. JSON synthesis only
- or reduce candidate search breadth per run to avoid timeout churn

### 3) Internal image generation failed first, then ComfyUI saved the run
Primary internal image generation failed:
- `openai/gpt-image-2` → org verification required (403)

Fallback internal image generation also failed:
- `google/gemini-3.1-flash-image-preview` → no API key configured

Action taken:
- Anthony approved local ComfyUI fallback
- generated all 10 covers through the local ComfyUI workflow
- patched news article frontmatter to point at generated cover files

Improvement:
- add a preflight image-provider auth check before article generation starts
- fail early with a clear status line before the workflow spends time producing posts with missing covers
- keep local ComfyUI as an explicit user-approved fallback path when internal providers are unavailable

### 4) Build gate is too weak about missing covers
The site build passed even though required cover image files were not present.

Improvement:
- add a post-write cover existence check that fails the run when `coverImage` paths do not exist
- or add a script that reports `missing coverImage asset` before build/push

## Current files of interest
- Candidates JSON: `tmp/candidates_fresh_2026-05-04.json`
- Archived failed draft batch: `tmp/failed_batch_2026-05-01/`
- This note: `docs/daily_run_notes_2026-05-04.md`

## Recommended next step
- For article generation, consider moving the candidate-finding agent from GPT-5.4-mini OAuth to GPT-5.4 OAuth if mini keeps timing out on broad 10-item discovery runs.
- Keep mini for narrower JSON formatting tasks if it stays reliable there.
