import { getCurrentUser, publicUser } from '../../_lib/auth.js';
import { json } from '../../_lib/http.js';

export async function onRequestGet({ request, env }) {
  const user = await getCurrentUser(env, request);
  return json({ ok: true, user: publicUser(user) });
}
