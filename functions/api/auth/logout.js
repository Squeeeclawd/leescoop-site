import { revokeCurrentSession } from '../../_lib/auth.js';
import { json } from '../../_lib/http.js';

export async function onRequestPost({ request, env }) {
  const cookie = await revokeCurrentSession(env, request);
  return json({ ok: true }, 200, { 'set-cookie': cookie });
}
