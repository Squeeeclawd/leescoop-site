import { requireModerator } from '../../_lib/auth.js';
import { json, requireDb } from '../../_lib/http.js';

const ALLOWED_STATUSES = new Set(['visible', 'hidden', 'flagged', 'deleted']);

export async function onRequestGet({ request, env }) {
  const auth = await requireModerator(env, request);
  if (auth.response) return auth.response;
  const db = requireDb(env);
  const url = new URL(request.url);
  const rawStatus = String(url.searchParams.get('status') || 'visible');
  const status = ALLOWED_STATUSES.has(rawStatus) ? rawStatus : 'visible';
  const limit = Math.min(Math.max(Number(url.searchParams.get('limit') || 100), 1), 200);

  const { results } = await db.prepare(
    `SELECT article_comments.id, article_comments.article_slug, article_comments.user_id, article_comments.body,
            article_comments.status, article_comments.moderation_reason, article_comments.created_at, article_comments.updated_at,
            article_comments.hidden_at, article_comments.deleted_at,
            users.username, users.email, users.role, users.status AS user_status
     FROM article_comments
     JOIN users ON users.id = article_comments.user_id
     WHERE article_comments.status = ?
     ORDER BY article_comments.created_at DESC
     LIMIT ?`
  ).bind(status, limit).all();

  return json({ ok: true, comments: results || [] });
}
