import { checkRateLimit, createSession, hashPassword, loginCookieResponse, normalizeUsername, publicUser, validateOptionalEmail, validatePassword, validateUsername, verifyTurnstileIfConfigured } from '../../_lib/auth.js';
import { badRequest, conflict, readJson, requireDb, serverError } from '../../_lib/http.js';

export async function onRequestPost({ request, env }) {
  const db = requireDb(env);
  const limited = await checkRateLimit(env, request, 'signup', 3, 60 * 60);
  if (!limited.ok) return limited.response;

  const body = await readJson(request);
  const username = String(body.username || '').trim();
  const usernameNormalized = normalizeUsername(username);
  const password = String(body.password || '');
  const email = String(body.email || '').trim();

  const usernameProblem = validateUsername(username);
  if (usernameProblem) return badRequest(usernameProblem);
  const passwordProblem = validatePassword(password);
  if (passwordProblem) return badRequest(passwordProblem);
  const emailProblem = validateOptionalEmail(email);
  if (emailProblem) return badRequest(emailProblem);

  const turnstile = await verifyTurnstileIfConfigured(env, request, body.turnstileToken || '');
  if (!turnstile.ok) return turnstile.response;

  const now = new Date().toISOString();
  const user = {
    id: crypto.randomUUID(),
    username,
    username_normalized: usernameNormalized,
    email: email || null,
    role: 'user',
    status: 'active'
  };

  let userInserted = false;

  try {
    const existing = await db.prepare(
      'SELECT id FROM users WHERE username_normalized = ? LIMIT 1'
    ).bind(usernameNormalized).first();
    if (existing) return conflict('That username is already taken. Try logging in instead.');

    const passwordHash = await hashPassword(password, env);
    await db.prepare(
      `INSERT INTO users (id, username, username_normalized, password_hash, email, email_is_optional, role, status, created_at, updated_at)
       VALUES (?, ?, ?, ?, ?, 1, 'user', 'active', ?, ?)`
    ).bind(user.id, user.username, user.username_normalized, passwordHash, user.email, now, now).run();
    userInserted = true;

    const session = await createSession(env, request, user.id);
    return loginCookieResponse({ ok: true, user: publicUser(user) }, session.cookie);
  } catch (error) {
    const message = String(error?.message || error || '');
    const lowerMessage = message.toLowerCase();

    if (lowerMessage.includes('unique') || lowerMessage.includes('constraint failed: users.username')) {
      return conflict('That username is already taken. Try logging in instead.');
    }

    if (userInserted) {
      await db.prepare('DELETE FROM users WHERE id = ?').bind(user.id).run().catch((cleanupError) => {
        console.error('Signup cleanup failed', cleanupError);
      });
    }

    console.error('Signup failed', error);

    if (lowerMessage.includes('no such table')) {
      return serverError('Account database setup is incomplete. Re-run the comments SQL migration in Cloudflare D1.');
    }
    if (lowerMessage.includes('no such column')) {
      return serverError('Account database schema is out of date. Re-run the comments SQL migration in Cloudflare D1.');
    }
    if (lowerMessage.includes('missing d1 binding')) {
      return serverError('Comments database is not connected yet. Cloudflare D1 needs to be bound as DB.');
    }

    return serverError('Could not create account. Check Cloudflare Pages Function logs for the exact D1 error.');
  }
}
