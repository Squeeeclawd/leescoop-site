import { requireModerator } from '../../../../_lib/auth.js';
import { badRequest, forbidden, json, notFound, readJson, requireDb } from '../../../../_lib/http.js';

export async function onRequestPost({ request, env, params }) {
  const auth = await requireModerator(env, request);
  if (auth.response) return auth.response;
  const db = requireDb(env);
  const id = params.id;
  const body = await readJson(request);
  const reason = String(body.reason || '').trim().slice(0, 500);
  if (!id) return badRequest('Missing user id.');
  if (id === auth.user.id) return forbidden('Do not ban yourself. Cute try.');
  const user = await db.prepare('SELECT id, role FROM users WHERE id = ?').bind(id).first();
  if (!user) return notFound('User not found.');
  if (user.role === 'admin' && auth.user.role !== 'admin') return forbidden('Only admins can ban admins.');
  const now = new Date().toISOString();
  await db.prepare('UPDATE users SET status = \'banned\', updated_at = ? WHERE id = ?').bind(now, id).run();
  await db.prepare('UPDATE sessions SET revoked_at = ? WHERE user_id = ? AND revoked_at IS NULL').bind(now, id).run();
  await db.prepare(
    `INSERT INTO moderation_log (id, moderator_id, action, entity_type, entity_id, note, created_at)
     VALUES (?, ?, 'ban', 'user', ?, ?, ?)`
  ).bind(crypto.randomUUID(), auth.user.id, id, reason || null, now).run();
  return json({ ok: true });
}
