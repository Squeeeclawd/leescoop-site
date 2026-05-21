import { sendPaidEventSubmissionEmail } from '../../_lib/email.js';
import { json, nowIso, requireDb } from '../../_lib/http.js';

const textEncoder = new TextEncoder();

const IMAGE_COLUMNS = [
  ['image_preference', 'TEXT'],
  ['image_url', 'TEXT'],
  ['image_upload_name', 'TEXT'],
  ['image_upload_mime', 'TEXT'],
  ['image_upload_size', 'INTEGER'],
  ['image_upload_width', 'INTEGER'],
  ['image_upload_height', 'INTEGER'],
  ['image_upload_data_url', 'TEXT'],
  ['image_notes', 'TEXT']
];

function bytesToHex(bytes) {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

function parseStripeSignature(header) {
  const parts = Object.fromEntries(String(header || '').split(',').map((part) => {
    const [key, value] = part.split('=');
    return [key, value];
  }));
  return { timestamp: parts.t || '', signature: parts.v1 || '' };
}

function constantTimeEqual(a, b) {
  if (!a || !b || a.length !== b.length) return false;
  let mismatch = 0;
  for (let i = 0; i < a.length; i += 1) mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return mismatch === 0;
}

async function hmacSha256Hex(secret, payload) {
  const key = await crypto.subtle.importKey(
    'raw',
    textEncoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const signature = await crypto.subtle.sign('HMAC', key, textEncoder.encode(payload));
  return bytesToHex(new Uint8Array(signature));
}

async function verifyStripeRequest(request, env, rawBody) {
  const secret = env?.STRIPE_WEBHOOK_SECRET || '';
  if (!secret) return false;
  const { timestamp, signature } = parseStripeSignature(request.headers.get('stripe-signature'));
  if (!timestamp || !signature) return false;
  const ageSeconds = Math.abs(Date.now() / 1000 - Number(timestamp));
  if (!Number.isFinite(ageSeconds) || ageSeconds > 300) return false;
  const expected = await hmacSha256Hex(secret, `${timestamp}.${rawBody}`);
  return constantTimeEqual(expected, signature);
}

async function addMissingColumns(db, columns) {
  for (const [name, type] of columns) {
    try {
      await db.prepare(`ALTER TABLE event_submissions ADD COLUMN ${name} ${type}`).run();
    } catch (error) {
      if (!String(error?.message || error).toLowerCase().includes('duplicate column')) throw error;
    }
  }
}

async function ensureEventSubmissionSchema(db) {
  await db.prepare(`CREATE TABLE IF NOT EXISTS event_submissions (
    id TEXT PRIMARY KEY,
    event_name TEXT NOT NULL,
    event_date TEXT,
    event_time TEXT,
    venue TEXT,
    address TEXT,
    city TEXT,
    event_url TEXT,
    ticket_url TEXT,
    description TEXT,
    organizer_name TEXT,
    organizer_email TEXT,
    organizer_phone TEXT,
    expected_attendance TEXT,
    image_preference TEXT,
    image_url TEXT,
    image_upload_name TEXT,
    image_upload_mime TEXT,
    image_upload_size INTEGER,
    image_upload_width INTEGER,
    image_upload_height INTEGER,
    image_upload_data_url TEXT,
    image_notes TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'pending_payment',
    payment_status TEXT NOT NULL DEFAULT 'unpaid',
    stripe_reference TEXT,
    stripe_checkout_session_id TEXT,
    stripe_payment_intent_id TEXT,
    paid_at TEXT,
    ip_hash TEXT,
    user_agent_hash TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
  )`).run();
  await addMissingColumns(db, IMAGE_COLUMNS);
}

export async function onRequestPost({ request, env }) {
  const rawBody = await request.text();
  const verified = await verifyStripeRequest(request, env, rawBody);
  if (!verified) return json({ ok: false, error: 'Invalid signature' }, 400);

  const event = JSON.parse(rawBody);
  if (event.type !== 'checkout.session.completed') return json({ ok: true, ignored: true });

  const session = event.data?.object || {};
  const submissionId = String(session.client_reference_id || session.metadata?.submission_id || '').trim();
  if (!submissionId) return json({ ok: true, ignored: true, reason: 'missing client_reference_id' });

  const db = requireDb(env);
  await ensureEventSubmissionSchema(db);
  const now = nowIso();
  const checkoutSessionId = String(session.id || '');
  const paymentIntentId = String(session.payment_intent || '');

  await db.prepare(`UPDATE event_submissions
    SET payment_status = 'paid',
        status = CASE WHEN status = 'pending_payment' THEN 'paid_pending_review' ELSE status END,
        stripe_checkout_session_id = ?,
        stripe_payment_intent_id = ?,
        paid_at = COALESCE(paid_at, ?),
        updated_at = ?
    WHERE id = ?`).bind(
      checkoutSessionId,
      paymentIntentId,
      now,
      now,
      submissionId
    ).run();

  const { results } = await db.prepare('SELECT * FROM event_submissions WHERE id = ? LIMIT 1').bind(submissionId).all();
  const submission = results?.[0];
  let notification = { ok: false, skipped: true, reason: 'submission not found' };
  if (submission) {
    notification = await sendPaidEventSubmissionEmail(env, {
      ...submission,
      stripe_checkout_session_id: checkoutSessionId || submission.stripe_checkout_session_id,
      stripe_payment_intent_id: paymentIntentId || submission.stripe_payment_intent_id
    });
  }

  return json({ ok: true, notification: { ok: Boolean(notification.ok), skipped: Boolean(notification.skipped), provider: notification.provider || null } });
}
