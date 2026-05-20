import { checkRateLimit, sha256Hex, verifyTurnstileIfConfigured } from '../_lib/auth.js';
import { badRequest, clientIp, json, nowIso, readJson, requireDb, userAgent } from '../_lib/http.js';

const MAX = {
  eventName: 160,
  eventTime: 120,
  venue: 180,
  city: 100,
  address: 220,
  url: 500,
  description: 2200,
  organizerName: 140,
  organizerEmail: 254,
  organizerPhone: 80,
  expectedAttendance: 80,
  notes: 1200
};

function clean(value, max = 500) {
  return String(value || '').replace(/\r\n/g, '\n').replace(/[\t ]+\n/g, '\n').trim().slice(0, max);
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || '').trim());
}

function appendPaymentParams(paymentLink, submissionId, email) {
  if (!paymentLink) return '';
  const url = new URL(paymentLink);
  url.searchParams.set('client_reference_id', submissionId);
  if (email) url.searchParams.set('prefilled_email', email);
  return url.toString();
}

async function ensureEventSubmissionSchema(db) {
  await db.prepare(`CREATE TABLE IF NOT EXISTS rate_limits (
    key TEXT PRIMARY KEY,
    window_start INTEGER NOT NULL,
    count INTEGER NOT NULL,
    updated_at TEXT NOT NULL
  )`).run();
  await db.prepare('CREATE INDEX IF NOT EXISTS rate_limits_window_idx ON rate_limits(window_start)').run();

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
    organizer_email TEXT NOT NULL,
    organizer_phone TEXT,
    expected_attendance TEXT,
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
  await db.prepare('CREATE INDEX IF NOT EXISTS event_submissions_status_idx ON event_submissions(status, created_at)').run();
  await db.prepare('CREATE INDEX IF NOT EXISTS event_submissions_payment_idx ON event_submissions(payment_status, created_at)').run();
  await db.prepare('CREATE INDEX IF NOT EXISTS event_submissions_email_idx ON event_submissions(organizer_email, created_at)').run();
}

export async function onRequestPost({ request, env }) {
  const db = requireDb(env);
  await ensureEventSubmissionSchema(db);

  const limitedByIp = await checkRateLimit(env, request, 'event-submission-ip', 5, 60 * 60);
  if (!limitedByIp.ok) return limitedByIp.response;
  const limitedDaily = await checkRateLimit(env, request, 'event-submission-day', 12, 24 * 60 * 60);
  if (!limitedDaily.ok) return limitedDaily.response;

  const data = await readJson(request);
  if (clean(data.website, 200)) return badRequest('Submission rejected.');

  const turnstile = await verifyTurnstileIfConfigured(env, request, data.turnstileToken);
  if (!turnstile.ok) return turnstile.response;

  const eventName = clean(data.eventName, MAX.eventName);
  const eventDate = clean(data.eventDate, 40);
  const eventTime = clean(data.eventTime, MAX.eventTime);
  const venue = clean(data.venue, MAX.venue);
  const address = clean(data.address, MAX.address);
  const city = clean(data.city, MAX.city);
  const eventUrl = clean(data.eventUrl, MAX.url);
  const ticketUrl = clean(data.ticketUrl, MAX.url);
  const description = clean(data.description, MAX.description);
  const organizerName = clean(data.organizerName, MAX.organizerName);
  const organizerEmail = clean(data.organizerEmail, MAX.organizerEmail).toLowerCase();
  const organizerPhone = clean(data.organizerPhone, MAX.organizerPhone);
  const expectedAttendance = clean(data.expectedAttendance, MAX.expectedAttendance);
  const notes = clean(data.notes, MAX.notes);

  if (eventName.length < 3) return badRequest('Event name is required.');
  if (eventDate && !/^\d{4}-\d{2}-\d{2}$/.test(eventDate)) return badRequest('Event date needs to use the date picker format.');
  if (!isValidEmail(organizerEmail)) return badRequest('Your email is required so LeeScoop can confirm payment and follow up.');
  if (/<\/?[a-z][\s\S]*>/i.test(`${eventName}\n${venue}\n${description}\n${notes}`)) return badRequest('Plain text only, no HTML.');

  const now = nowIso();
  const id = crypto.randomUUID();
  const ipHash = await sha256Hex(`${env?.COMMENTS_PEPPER || ''}:event-ip:${clientIp(request)}`);
  const uaHash = await sha256Hex(`${env?.COMMENTS_PEPPER || ''}:event-ua:${userAgent(request)}`);

  await db.prepare(`INSERT INTO event_submissions (
    id, event_name, event_date, event_time, venue, address, city, event_url, ticket_url, description,
    organizer_name, organizer_email, organizer_phone, expected_attendance, notes, status, payment_status,
    stripe_reference, ip_hash, user_agent_hash, created_at, updated_at
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_payment', 'unpaid', ?, ?, ?, ?, ?)`).bind(
    id,
    eventName,
    eventDate,
    eventTime,
    venue,
    address,
    city,
    eventUrl,
    ticketUrl,
    description,
    organizerName,
    organizerEmail,
    organizerPhone,
    expectedAttendance,
    notes,
    id,
    ipHash,
    uaHash,
    now,
    now
  ).run();

  const paymentLink = env?.FEATURE_EVENT_PAYMENT_LINK || env?.STRIPE_FEATURE_EVENT_PAYMENT_LINK || '';
  let paymentUrl = '';
  try {
    paymentUrl = paymentLink ? appendPaymentParams(paymentLink, id, organizerEmail) : '';
  } catch {
    paymentUrl = '';
  }

  return json({
    ok: true,
    submissionId: id,
    paymentUrl,
    message: paymentUrl
      ? 'Submission saved. Redirecting to secure payment.'
      : 'Submission saved. LeeScoop will follow up with payment instructions once payment is connected.'
  });
}
