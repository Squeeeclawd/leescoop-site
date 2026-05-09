import { json } from './_lib/http.js';

export async function onRequest(context) {
  try {
    return await context.next();
  } catch (error) {
    const url = new URL(context.request.url);
    const isApi = url.pathname.startsWith('/api/');
    const message = String(error?.message || error || '');

    if (message.includes('Missing D1 binding: DB')) {
      if (isApi) {
        return json({
          ok: false,
          error: 'Comments database is not connected yet. Cloudflare D1 needs to be bound as DB.'
        }, 503);
      }
      return new Response('Comments database is not connected yet.', { status: 503 });
    }

    console.error(error);
    if (isApi) return json({ ok: false, error: 'Comments are temporarily unavailable.' }, 500);
    throw error;
  }
}
