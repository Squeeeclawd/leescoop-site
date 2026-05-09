import { checkRateLimit, requireUser } from '../_lib/auth.js';
import { badRequest, conflict, json, readJson, requireDb } from '../_lib/http.js';

function cleanBody(value) {
  return String(value || '').replace(/\r\n/g, '\n').replace(/[\t ]+\n/g, '\n').trim();
}

function linkCount(value) {
  return (String(value || '').match(/https?:\/\//gi) || []).length;
}

function publicComment(row) {
  return {
    id: row.id,
    articleSlug: row.article_slug,
    body: row.body,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    username: row.username,
    userId: row.user_id
  };
}

export async function onRequestGet({ request, env }) {
  const db = requireDb(env);
  const url = new URL(request.url);
  const slug = String(url.searchParams.get('slug') || '').trim();
  if (!slug) return badRequest('Article slug is required.');

  const { results } = await db.prepare(
    `SELECT article_comments.id, article_comments.article_slug, article_comments.user_id, article_comments.body,
            article_comments.created_at, article_comments.updated_at, users.username
     FROM article_comments
     JOIN users ON users.id = article_comments.user_id
     WHERE article_comments.article_slug = ?
       AND article_comments.status = 'visible'
       AND users.status != 'deleted'
     ORDER BY article_comments.created_at ASC
     LIMIT 250`
  ).bind(slug).all();

  return json({ ok: true, comments: (results || []).map(publicComment) });
}

export async function onRequestPost({ request, env }) {
  const db = requireDb(env);
  const auth = await requireUser(env, request);
  if (auth.response) return auth.response;
  const { user } = auth;

  const limitedByUser = await checkRateLimit(env, request, 'comment-user', 10, 60 * 60, user.id);
  if (!limitedByUser.ok) return limitedByUser.response;
  const limitedDaily = await checkRateLimit(env, request, 'comment-user-day', 40, 24 * 60 * 60, user.id);
  if (!limitedDaily.ok) return limitedDaily.response;

  const data = await readJson(request);
  const articleSlug = String(data.articleSlug || '').trim();
  const body = cleanBody(data.body);
  if (!articleSlug) return badRequest('Article slug is required.');
  if (body.length < 2) return badRequest('Comment is too short.');
  if (body.length > 1500) return badRequest('Comment is too long.');
  if (linkCount(body) > 2) return badRequest('Keep it to two links max.');
  if (/<\/?[a-z][\s\S]*>/i.test(body)) return badRequest('Plain text only, no HTML.');

  const duplicate = await db.prepare(
    `SELECT id FROM article_comments
     WHERE user_id = ? AND article_slug = ? AND body = ? AND created_at > ? AND status != 'deleted'
     LIMIT 1`
  ).bind(user.id, articleSlug, body, new Date(Date.now() - 5 * 60 * 1000).toISOString()).first();
  if (duplicate) return conflict('That comment was already posted.');

  const now = new Date().toISOString();
  const id = crypto.randomUUID();
  await db.prepare(
    `INSERT INTO article_comments (id, article_slug, user_id, body, status, created_at, updated_at)
     VALUES (?, ?, ?, ?, 'visible', ?, ?)`
  ).bind(id, articleSlug, user.id, body, now, now).run();

  return json({
    ok: true,
    comment: {
      id,
      articleSlug,
      body,
      createdAt: now,
      updatedAt: now,
      username: user.username,
      userId: user.id
    }
  });
}
