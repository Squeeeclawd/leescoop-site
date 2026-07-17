Run the daily LeeScoop event-first 4-post autopost workflow.

Repo/workdir: /home/shmee/Desktop/leescoop

Goal: create exactly 4 publishable LeeScoop posts: 3 local event posts and 1 major local news brief. At least 2 of the 3 events must have a verified `city` value of `Fort Myers`; Fort Myers Beach is a separate geography. Do not substitute extra news for missing events. Never force weak filler or incomplete event posts just to hit quota.

Use OAuth GPT-5.4 for judgment/discovery if you delegate or need model-heavy source selection. Do not silently switch model/provider if OAuth GPT-5.4 fails; report the blocker.

Required workflow:
1. cd /home/shmee/Desktop/leescoop.
2. Run npm run preflight first. Understand warnings; stop only for hard blockers.
3. Use existing project docs as authority: docs/daily_autopost_workflow.md, docs/event_discovery_sources.md, docs/command_contract.md, prompts/leescoop_daily_gpt54mini.md, scripts/leescoop_posts.py, and /home/shmee/.openclaw/workspace/reference/leescoop/article_image_workflow.md.
4. Run the full source and query sweep in docs/event_discovery_sources.md. Gather at least 12 plausible event leads, then fully verify and rank at least 8 non-duplicate event candidates. Cover first-party Fort Myers venues, city/county/tourism/library calendars, ticketing platforms, and community/recurring-event leads. Do not stop after the obvious arena calendars.
5. Rank at least 3 major local news candidates as reserves. Select exactly 3 events + 1 news brief for publication. At least 2 selected events must have verified `city: Fort Myers`, and the event set should span at least 2 sources and 2 event types.
6. De-dupe against src/content/articles/*.md by source URL, title, slug, and event date+venue. Retain at least 3 verified event backups until covers and quality checks are complete. Use shell rg/find commands for repo searches, and make no-match searches non-fatal with `|| true`; a helper search returning no matches is not a workflow failure.
7. Do not overwrite existing files. If the repo already contains untracked LeeScoop articles/covers from a previous failed run, inspect them first and either complete that exact batch safely or stop with a clear blocker; do not stack a second unrelated draft batch on top.
8. Images:
   - News: prefer source/OG/primary article image from the same publisher/source; preserve sourceImageUrl.
   - Events: generate LeeScoop-style covers with OpenClaw image generation openai/gpt-image-1.5 at 1536x1024, then crop/resize to 1216x704 when tooling is available.
   - No readable text, logos, watermarks, fake signs, or exact protected/proper-name prompts in generated covers.
   - If OpenAI image generation fails, do NOT silently fall back to ComfyUI. Stop and report the blocker unless Anthony has explicitly approved fallback.
   - CRITICAL: if OpenClaw image generation returns a background task / says to wait for a completion event, that is NOT a completed cover. Do not proceed, validate, commit, or publish any event post whose cover file is not already present under public/covers. Stop and report the event-cover blocker rather than replacing events with extra news.
9. Write markdown posts in src/content/articles only after each selected item has a complete image plan. For event posts, the cover file must exist before publish. For news posts, source images may be downloaded by scripts/leescoop_posts.py. Use `python3 scripts/leescoop_posts.py write --input tmp/candidates.json --max-events 3 --max-news 1`.
10. Before quality/build, verify every new post has a nonempty coverImage value and that each referenced file exists under public/covers. If a cover was created/downloaded but frontmatter is blank, fix the frontmatter before continuing. Do not publish posts with blank or missing covers.
11. Run npm run quality. If it fails, stop and report the exact blocker.
12. Stage ONLY files created/changed by this run. Do not include unrelated dirty files.
13. Commit with a clear message and push to main.
14. Final response must be a concise Telegram-ready report: posts created, 3-event/1-news split, `city: Fort Myers` count, source/category diversity, image handling summary, quality/build result, commit hash, and any skipped duplicates/blockers.

Safety: do not publish partial/low-confidence work. If fewer than 3 strong non-duplicate events or fewer than 1 major non-duplicate news item exist, report the shortfall clearly and do not silently change the ratio.
