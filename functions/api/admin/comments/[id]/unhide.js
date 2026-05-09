import { requireModerator } from '../../../../_lib/auth.js';
import { badRequest, json, notFound, requireDb } from '../../../../_lib/http.js';

export async function onRequestPost({ request, env, params }) {
  const auth = await requireModerator(env, request);
  if (auth.response) return auth.response;
  const db = requireDb(env);
  const id = params.id;
  if (!id) return badRequest('Missing comment id.');
  const existing = await db.prepare('SELECT id FROM article_comments WHERE id = ?').bind(id).first();
  if (!existing) return notFound('Comment not found.');
  const now = new Date().toISOString();
  await db.prepare(
    `UPDATE article_comments
     SET status = 'visible', moderation_reason = NULL, updated_at = ?
     WHERE id = ?`
  ).bind(now, id).run();
  await db.prepare(
    `INSERT INTO moderation_log (id, moderator_id, action, entity_type, entity_id, note, created_at)
     VALUES (?, ?, 'unhide', 'comment', ?, NULL, ?)`
  ).bind(crypto.randomUUID(), auth.user.id, id, now).run();
  return json({ ok: true });
}
