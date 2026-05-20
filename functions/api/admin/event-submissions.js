import { requireModerator } from '../../_lib/auth.js';
import { json, requireDb } from '../../_lib/http.js';

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
}

function publicSubmission(row) {
  return {
    id: row.id,
    eventName: row.event_name,
    eventDate: row.event_date,
    eventTime: row.event_time,
    venue: row.venue,
    address: row.address,
    city: row.city,
    eventUrl: row.event_url,
    ticketUrl: row.ticket_url,
    description: row.description,
    organizerName: row.organizer_name,
    organizerEmail: row.organizer_email,
    organizerPhone: row.organizer_phone,
    expectedAttendance: row.expected_attendance,
    notes: row.notes,
    status: row.status,
    paymentStatus: row.payment_status,
    paidAt: row.paid_at,
    createdAt: row.created_at,
    updatedAt: row.updated_at
  };
}

export async function onRequestGet({ request, env }) {
  const auth = await requireModerator(env, request);
  if (auth.response) return auth.response;
  const db = requireDb(env);
  await ensureEventSubmissionSchema(db);

  const url = new URL(request.url);
  const status = String(url.searchParams.get('status') || '').trim();
  const payment = String(url.searchParams.get('payment') || '').trim();
  const limit = Math.min(Math.max(Number(url.searchParams.get('limit') || 50), 1), 100);

  const clauses = [];
  const bindings = [];
  if (status) {
    clauses.push('status = ?');
    bindings.push(status);
  }
  if (payment) {
    clauses.push('payment_status = ?');
    bindings.push(payment);
  }

  const where = clauses.length ? `WHERE ${clauses.join(' AND ')}` : '';
  const { results } = await db.prepare(`SELECT * FROM event_submissions ${where} ORDER BY created_at DESC LIMIT ?`)
    .bind(...bindings, limit)
    .all();

  return json({ ok: true, submissions: (results || []).map(publicSubmission) });
}
