# LeeScoop publishing workflow

Quality over fill: publication is unlimited for reviewed eligible content; zero is valid. Three strong events and one consequential news brief remain optional discovery targets, not caps. Explicit ten-event batches are supported. The executable and recovery contract is `docs/command_contract.md`.

Standing owner authorization (November 10, 2026): automatically complete and publish eligible LeeScoop posts, including disclosed generated-news-art fallbacks. Do not ask for routine publishing or cover approval. Source/factual verification, dedupe, image validation, quality and live verification remain required; a failed check is repaired or the affected item is honestly skipped, not turned into an approval request.

1. Run the deterministic source plan and require a fresh successful routine-route receipt.
2. Read only configured public sources with supported agent tools and explicit plan budgets. Use the bounded source-fetch helper described in `docs/workflow/source_fetch.md`.
3. Require a fresh successful strong-review route receipt; verify facts, dates, locality, usefulness and diversity. Every event needs an actual extracted title/date and matching structured start from its event page. Reachability, HTTP 200, a root/calendar title or search snippet is only a lead.
4. Resolve selected covers automatically. New events require exact `openai/gpt-image-2` generation through live-proven Codex OAuth. Reviewed tracked existing covers may be preserved. For news, prefer attributable source art; if unavailable, use relevant reviewed archived artwork or generate a conceptual illustration with an explicit visible disclosure. Record the fallback reason and actual completed task/receipt identity. Never invent a task ID for a synchronous CLI result.
5. `prepare` acquires the durable global release lease. `gate` binds routes, input, selection and asset hashes. `materialize` exclusively creates checkpoint-selected articles in the isolated release checkout.
6. Run fixed quality, scoped commit and fast-forward push commands. Push is not publication.
7. Parent verifies production title, direct source link and decoded cover hash for every selected item. `finalize` updates the ledger only from the exact deployment/live receipt.

Do not bypass the lease, checkpoint writer, source registry, cover policy or receipt finalizer. Do not add shell/model callbacks to the workflow script. The scheduled publishing agent owns the complete release and production verification; it does not require a foreground human or a separate approval turn. Parent/agent ownership in this contract denotes responsibility, not human permission.


No daily or per-batch publication cap applies. Source-access budgets remain enforced. See the unlimited publication, legacy reservation, finalization and recovery rules in `command_contract.md`.
