import { clearSessionCookie, clientIp, forbidden, json, nowIso, parseCookie, requireDb, sessionCookie, tooMany, unauthorized, userAgent } from './http.js';

const SESSION_DAYS = 30;
const SESSION_MAX_AGE_SECONDS = SESSION_DAYS * 24 * 60 * 60;
const PASSWORD_ITERATIONS = 25000;
const PASSWORD_ALGO = 'sha256_iter';
const LEGACY_PASSWORD_ALGO = 'pbkdf2_sha256';
const textEncoder = new TextEncoder();

function bytesToHex(bytes) {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

function hexToBytes(hex) {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i += 1) out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  return out;
}

function randomHex(bytes = 32) {
  const arr = new Uint8Array(bytes);
  crypto.getRandomValues(arr);
  return bytesToHex(arr);
}

export async function sha256Hex(value) {
  const hash = await crypto.subtle.digest('SHA-256', textEncoder.encode(value));
  return bytesToHex(new Uint8Array(hash));
}

async function pbkdf2(password, saltHex, pepper = '') {
  const material = await crypto.subtle.importKey(
    'raw',
    textEncoder.encode(`${password}${pepper}`),
    'PBKDF2',
    false,
    ['deriveBits']
  );
  const bits = await crypto.subtle.deriveBits(
    { name: 'PBKDF2', salt: hexToBytes(saltHex), iterations: PASSWORD_ITERATIONS, hash: 'SHA-256' },
    material,
    256
  );
  return bytesToHex(new Uint8Array(bits));
}

async function sha256Iter(password, saltHex, pepper = '', iterations = PASSWORD_ITERATIONS) {
  let bytes = textEncoder.encode(`${saltHex}:${pepper}:${password}`);
  for (let i = 0; i < iterations; i += 1) {
    bytes = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
  }
  return bytesToHex(bytes);
}

function constantTimeEqual(a, b) {
  if (a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i += 1) mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return mismatch === 0;
}

export async function hashPassword(password, env) {
  const salt = randomHex(16);
  const hash = await sha256Iter(password, salt, env?.COMMENTS_PEPPER || '');
  return `${PASSWORD_ALGO}$${PASSWORD_ITERATIONS}$${salt}$${hash}`;
}

export async function verifyPassword(password, stored, env) {
  const [algo, iterationsRaw, salt, expected] = String(stored || '').split('$');
  const iterations = Number(iterationsRaw);
  if (!algo || !iterations || !salt || !expected) return false;

  if (algo === PASSWORD_ALGO) {
    const actual = await sha256Iter(password, salt, env?.COMMENTS_PEPPER || '', iterations);
    return constantTimeEqual(actual, expected);
  }

  if (algo === LEGACY_PASSWORD_ALGO) {
    const actual = await pbkdf2(password, salt, env?.COMMENTS_PEPPER || '');
    return constantTimeEqual(actual, expected);
  }

  return false;
}

export function normalizeUsername(username) {
  return String(username || '').trim().toLowerCase();
}

export function validateUsername(username) {
  const trimmed = String(username || '').trim();
  if (trimmed.length < 3 || trimmed.length > 24) return 'Username must be 3–24 characters.';
  if (!/^[a-zA-Z0-9][a-zA-Z0-9._-]*$/.test(trimmed)) return 'Use letters, numbers, dots, underscores, or dashes. Start with a letter or number.';
  return '';
}

export function validatePassword(password) {
  const value = String(password || '');
  if (value.length < 8) return 'Password must be at least 8 characters.';
  if (value.length > 200) return 'Password is too long.';
  return '';
}

export function validateOptionalEmail(email) {
  const value = String(email || '').trim();
  if (!value) return '';
  if (value.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return 'Email is optional, but if you add one it needs to look like an email address.';
  return '';
}

export function publicUser(user) {
  if (!user) return null;
  return {
    id: user.id,
    username: user.username,
    role: user.role,
    status: user.status
  };
}

export async function createSession(env, request, userId) {
  const db = requireDb(env);
  const token = randomHex(32);
  const sessionHash = await sha256Hex(token);
  const createdAt = nowIso();
  const expiresAt = new Date(Date.now() + SESSION_MAX_AGE_SECONDS * 1000).toISOString();
  const ipHash = await sha256Hex(`${env?.COMMENTS_PEPPER || ''}:ip:${clientIp(request)}`);
  const uaHash = await sha256Hex(`${env?.COMMENTS_PEPPER || ''}:ua:${userAgent(request)}`);
  await db.prepare(
    `INSERT INTO sessions (id, user_id, session_hash, created_at, expires_at, user_agent_hash, ip_hash)
     VALUES (?, ?, ?, ?, ?, ?, ?)`
  ).bind(crypto.randomUUID(), userId, sessionHash, createdAt, expiresAt, uaHash, ipHash).run();
  return { token, cookie: sessionCookie(token, SESSION_MAX_AGE_SECONDS) };
}

export async function getCurrentUser(env, request) {
  const db = requireDb(env);
  const token = parseCookie(request, 'leescoop_session');
  if (!token) return null;
  const sessionHash = await sha256Hex(token);
  const row = await db.prepare(
    `SELECT users.id, users.username, users.username_normalized, users.email, users.role, users.status, sessions.id AS session_id
     FROM sessions
     JOIN users ON users.id = sessions.user_id
     WHERE sessions.session_hash = ?
       AND sessions.revoked_at IS NULL
       AND sessions.expires_at > ?
       AND users.status != 'deleted'
     LIMIT 1`
  ).bind(sessionHash, nowIso()).first();
  return row || null;
}

export async function revokeCurrentSession(env, request) {
  const db = requireDb(env);
  const token = parseCookie(request, 'leescoop_session');
  if (!token) return clearSessionCookie();
  const sessionHash = await sha256Hex(token);
  await db.prepare('UPDATE sessions SET revoked_at = ? WHERE session_hash = ?').bind(nowIso(), sessionHash).run();
  return clearSessionCookie();
}

export async function requireUser(env, request) {
  const user = await getCurrentUser(env, request);
  if (!user) return { response: unauthorized() };
  if (user.status === 'banned') return { response: forbidden('This account is banned.') };
  return { user };
}

export async function requireModerator(env, request) {
  const { user, response } = await requireUser(env, request);
  if (response) return { response };
  if (!['moderator', 'admin'].includes(user.role)) return { response: forbidden('Moderator access required.') };
  return { user };
}

export async function checkRateLimit(env, request, label, limit, windowSeconds, subject = '') {
  const db = requireDb(env);
  const ip = clientIp(request);
  const key = await sha256Hex(`${env?.COMMENTS_PEPPER || ''}:rate:${label}:${subject}:${ip}`);
  const now = Math.floor(Date.now() / 1000);
  const windowStart = now - (now % windowSeconds);
  const row = await db.prepare('SELECT window_start, count FROM rate_limits WHERE key = ?').bind(key).first();
  if (!row || Number(row.window_start) !== windowStart) {
    await db.prepare('INSERT OR REPLACE INTO rate_limits (key, window_start, count, updated_at) VALUES (?, ?, 1, ?)')
      .bind(key, windowStart, nowIso()).run();
    return { ok: true };
  }
  if (Number(row.count) >= limit) return { ok: false, response: tooMany() };
  await db.prepare('UPDATE rate_limits SET count = count + 1, updated_at = ? WHERE key = ?')
    .bind(nowIso(), key).run();
  return { ok: true };
}

export async function verifyTurnstileIfConfigured(env, request, token) {
  if (!env?.TURNSTILE_SECRET_KEY) return { ok: true };
  if (!token) return { ok: false, response: forbidden('Please complete the anti-spam check.') };
  const form = new FormData();
  form.set('secret', env.TURNSTILE_SECRET_KEY);
  form.set('response', token);
  form.set('remoteip', clientIp(request));
  const result = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
    method: 'POST',
    body: form
  });
  const data = await result.json().catch(() => ({}));
  if (!data.success) return { ok: false, response: forbidden('Anti-spam check failed.') };
  return { ok: true };
}

export function loginCookieResponse(data, cookie) {
  return json(data, 200, { 'set-cookie': cookie });
}
