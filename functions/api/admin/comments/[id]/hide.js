import { requireModerator } from '../../../../_lib/auth.js';
import { badRequest, json, notFound, readJson, requireDb } from '../../../../_lib/http.js';

export async function onRequestPost({ request, env, params }) {
  const auth = await requireModerator(env, request);
  if (auth.response) return auth.response;
  const db = requireDb(env);
  const id = params.id;
  const body = await readJson(request);
  const reason = String(body.reason || '').trim().slice(0, 500);
  if (!id) return badRequest('Missing comment id.');
  const existing = await db.prepare('SELECT id FROM article_comments WHERE id = ?').bind(id).first();
  if (!existing) return notFound('Comment not found.');
  const now = new Date().toISOString();
  await db.prepare(
    `UPDATE article_comments
     SET status = 'hidden', moderation_reason = ?, hidden_at = ?, hidden_by = ?, updated_at = ?
     WHERE id = ?`
  ).bind(reason || null, now, auth.user.id, now, id).run();
  await db.prepare(
    `INSERT INTO moderation_log (id, moderator_id, action, entity_type, entity_id, note, created_at)
     VALUES (?, ?, 'hide', 'comment', ?, ?, ?)`
  ).bind(crypto.randomUUID(), auth.user.id, id, reason || null, now).run();
  return json({ ok: true });
}
