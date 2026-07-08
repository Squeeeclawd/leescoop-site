Run the daily LeeScoop 4-post autopost workflow.

Repo/workdir: /home/shmee/Desktop/leescoop

Goal: create exactly 4 publishable LeeScoop posts: 2 local news articles and 2 local event posts. Do not substitute extra news posts for missing events. If two strong event posts cannot be completed with valid covers, publish only the complete valid set if that is acceptable under quality rules, or stop and clearly report the blocker/shortfall. Never force weak filler or incomplete event posts just to hit quota.

Use OAuth GPT-5.4 for judgment/discovery if you delegate or need model-heavy source selection. Do not silently switch model/provider if OAuth GPT-5.4 fails; report the blocker.

Required workflow:
1. cd /home/shmee/Desktop/leescoop.
2. Run npm run preflight first. Understand warnings; stop only for hard blockers.
3. Use existing project docs as authority: docs/daily_autopost_workflow.md, docs/command_contract.md, prompts/leescoop_daily_gpt54mini.md, scripts/leescoop_posts.py, and /home/shmee/.openclaw/workspace/reference/leescoop/article_image_workflow.md.
4. Discover fresh Lee County candidates from reliable/official/local sources. Select exactly 2 strong local news items and exactly 2 strong local event items when available. Prefer reader-value items, not filler.
5. De-dupe against src/content/articles/*.md by source URL, title, slug, and event date+venue. Use shell rg/find commands for repo searches, and make no-match searches non-fatal with `|| true`; a helper search returning no matches is not a workflow failure.
6. Do not overwrite existing files. If the repo already contains untracked LeeScoop articles/covers from a previous failed run, inspect them first and either complete that exact batch safely or stop with a clear blocker; do not stack a second unrelated draft batch on top.
7. Images:
   - News: prefer source/OG/primary article image from the same publisher/source; preserve sourceImageUrl.
   - Events: generate LeeScoop-style covers with OpenClaw image generation openai/gpt-image-1.5 at 1536x1024, then crop/resize to 1216x704 when tooling is available.
   - No readable text, logos, watermarks, fake signs, or exact protected/proper-name prompts in generated covers.
   - If OpenAI image generation fails, do NOT silently fall back to ComfyUI. Stop and report the blocker unless Anthony has explicitly approved fallback.
   - CRITICAL: if OpenClaw image generation returns a background task / says to wait for a completion event, that is NOT a completed cover. Do not proceed, validate, commit, or publish any event post whose cover file is not already present under public/covers. Stop and report the event-cover blocker rather than replacing events with extra news.
8. Write markdown posts in src/content/articles only after each selected item has a complete image plan. For event posts, the cover file must exist before publish. For news posts, source images may be downloaded by scripts/leescoop_posts.py.
9. Before quality/build, verify every new post has a nonempty coverImage value and that each referenced file exists under public/covers. If a cover was created/downloaded but frontmatter is blank, fix the frontmatter before continuing. Do not publish posts with blank or missing covers.
10. Run npm run quality. If it fails, stop and report the exact blocker.
11. Stage ONLY files created/changed by this run. Do not include unrelated dirty files.
12. Commit with a clear message and push to main.
13. Final response must be a concise Telegram-ready report: posts created, split between news/events, image handling summary, quality/build result, commit hash, and any skipped duplicates/blockers.

Safety: do not publish partial/low-confidence work. If fewer than 2 strong non-duplicate news items or fewer than 2 strong non-duplicate event items exist, report the shortfall clearly and do not silently change the ratio.
