const JSON_HEADERS = {
  'content-type': 'application/json; charset=utf-8',
  'cache-control': 'no-store'
};

export function json(data, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { ...JSON_HEADERS, ...extraHeaders }
  });
}

export function badRequest(message = 'Bad request') {
  return json({ ok: false, error: message }, 400);
}

export function unauthorized(message = 'Login required') {
  return json({ ok: false, error: message }, 401);
}

export function forbidden(message = 'Not allowed') {
  return json({ ok: false, error: message }, 403);
}

export function notFound(message = 'Not found') {
  return json({ ok: false, error: message }, 404);
}

export function conflict(message = 'Conflict') {
  return json({ ok: false, error: message }, 409);
}

export function tooMany(message = 'Slow down a little') {
  return json({ ok: false, error: message }, 429);
}

export function serverError(message = 'Server error') {
  return json({ ok: false, error: message }, 500);
}

export async function readJson(request) {
  const type = request.headers.get('content-type') || '';
  if (!type.includes('application/json')) return {};
  try {
    return await request.json();
  } catch {
    return {};
  }
}

export function requireDb(env) {
  if (!env?.DB) {
    throw new Error('Missing D1 binding: DB');
  }
  return env.DB;
}

export function parseCookie(request, name) {
  const header = request.headers.get('cookie') || '';
  const parts = header.split(';').map((part) => part.trim()).filter(Boolean);
  for (const part of parts) {
    const eq = part.indexOf('=');
    if (eq === -1) continue;
    const key = decodeURIComponent(part.slice(0, eq));
    if (key === name) return decodeURIComponent(part.slice(eq + 1));
  }
  return '';
}

export function sessionCookie(token, maxAgeSeconds) {
  const attrs = [
    `leescoop_session=${encodeURIComponent(token)}`,
    'Path=/',
    'HttpOnly',
    'Secure',
    'SameSite=Lax',
    `Max-Age=${maxAgeSeconds}`
  ];
  return attrs.join('; ');
}

export function clearSessionCookie() {
  return 'leescoop_session=; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=0';
}

export function nowIso() {
  return new Date().toISOString();
}

export function clientIp(request) {
  return request.headers.get('cf-connecting-ip') || request.headers.get('x-forwarded-for') || 'unknown';
}

export function userAgent(request) {
  return request.headers.get('user-agent') || 'unknown';
}
