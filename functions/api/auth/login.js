import { checkRateLimit, createSession, loginCookieResponse, normalizeUsername, publicUser, verifyPassword } from '../../_lib/auth.js';
import { badRequest, forbidden, readJson, requireDb, unauthorized } from '../../_lib/http.js';

export async function onRequestPost({ request, env }) {
  const db = requireDb(env);
  const body = await readJson(request);
  const usernameNormalized = normalizeUsername(body.username || '');
  const password = String(body.password || '');
  if (!usernameNormalized || !password) return badRequest('Username and password are required.');

  const limited = await checkRateLimit(env, request, 'login', 10, 60 * 60, usernameNormalized);
  if (!limited.ok) return limited.response;

  const user = await db.prepare(
    `SELECT id, username, username_normalized, password_hash, email, role, status
     FROM users
     WHERE username_normalized = ?
     LIMIT 1`
  ).bind(usernameNormalized).first();

  if (!user) return unauthorized('Wrong username or password.');
  if (user.status === 'banned') return forbidden('This account is banned.');
  if (user.status === 'deleted') return unauthorized('Wrong username or password.');

  const ok = await verifyPassword(password, user.password_hash, env);
  if (!ok) return unauthorized('Wrong username or password.');

  await db.prepare('UPDATE users SET last_login_at = ?, updated_at = ? WHERE id = ?')
    .bind(new Date().toISOString(), new Date().toISOString(), user.id).run();
  const session = await createSession(env, request, user.id);
  return loginCookieResponse({ ok: true, user: publicUser(user) }, session.cookie);
}
