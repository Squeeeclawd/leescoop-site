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
  imagePreference: 20,
  imageUrl: 500,
  imageUploadName: 180,
  imageUploadMime: 40,
  imageNotes: 500,
  imageUploadDataUrl: 2_100_000,
  notes: 1200
};

const MAX_IMAGE_UPLOAD_BYTES = 1.5 * 1024 * 1024;
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

function clean(value, max = 500) {
  return String(value || '').replace(/\r\n/g, '\n').replace(/[\t ]+\n/g, '\n').trim().slice(0, max);
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || '').trim());
}

function cleanInt(value, max = 100000) {
  const number = Number(value || 0);
  if (!Number.isFinite(number) || number < 0) return 0;
  return Math.min(Math.round(number), max);
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
  const imagePreferenceRaw = clean(data.imagePreference, MAX.imagePreference).toLowerCase();
  const imagePreference = imagePreferenceRaw === 'provided' ? 'provided' : 'generate';
  const imageUrl = clean(data.imageUrl, MAX.imageUrl);
  const imageUploadName = clean(data.imageUploadName, MAX.imageUploadName);
  const imageUploadMime = clean(data.imageUploadMime, MAX.imageUploadMime).toLowerCase();
  const imageUploadSize = cleanInt(data.imageUploadSize, 20 * 1024 * 1024);
  const imageUploadWidth = cleanInt(data.imageUploadWidth, 20000);
  const imageUploadHeight = cleanInt(data.imageUploadHeight, 20000);
  const imageUploadDataUrl = clean(data.imageUploadDataUrl, MAX.imageUploadDataUrl);
  const imageNotes = clean(data.imageNotes, MAX.imageNotes);
  const notes = clean(data.notes, MAX.notes);

  if (eventName.length < 3) return badRequest('Event name is required.');
  if (eventDate && !/^\d{4}-\d{2}-\d{2}$/.test(eventDate)) return badRequest('Event date needs to use the date picker format.');
  if (organizerEmail && !isValidEmail(organizerEmail)) return badRequest('If you add an email, it needs to look like an email address.');
  if (imageUrl && !/^https?:\/\//i.test(imageUrl)) return badRequest('Image link needs to start with http:// or https://.');
  if (imageUploadDataUrl) {
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(imageUploadMime)) return badRequest('Uploaded image must be JPG, PNG, or WebP.');
    if (imageUploadSize > MAX_IMAGE_UPLOAD_BYTES) return badRequest('Uploaded image must be under 1.5 MB.');
    if (!/^data:image\/(jpeg|png|webp);base64,[a-z0-9+/=]+$/i.test(imageUploadDataUrl)) return badRequest('Uploaded image could not be read.');
  }
  if (/<\/?[a-z][\s\S]*>/i.test(`${eventName}\n${venue}\n${description}\n${imageNotes}\n${notes}`)) return badRequest('Plain text only, no HTML.');

  const now = nowIso();
  const id = crypto.randomUUID();
  const ipHash = await sha256Hex(`${env?.COMMENTS_PEPPER || ''}:event-ip:${clientIp(request)}`);
  const uaHash = await sha256Hex(`${env?.COMMENTS_PEPPER || ''}:event-ua:${userAgent(request)}`);

  await db.prepare(`INSERT INTO event_submissions (
    id, event_name, event_date, event_time, venue, address, city, event_url, ticket_url, description,
    image_preference, image_url, image_upload_name, image_upload_mime, image_upload_size, image_upload_width,
    image_upload_height, image_upload_data_url, image_notes,
    organizer_name, organizer_email, organizer_phone, expected_attendance, notes, status, payment_status,
    stripe_reference, ip_hash, user_agent_hash, created_at, updated_at
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending_payment', 'unpaid', ?, ?, ?, ?, ?)`).bind(
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
    imagePreference,
    imageUrl,
    imageUploadName,
    imageUploadMime,
    imageUploadSize,
    imageUploadWidth,
    imageUploadHeight,
    imageUploadDataUrl,
    imageNotes,
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
