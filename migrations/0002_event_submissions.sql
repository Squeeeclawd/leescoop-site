-- Featured event paid-submission queue for Cloudflare D1
-- Apply with: wrangler d1 migrations apply <database-name> --remote

CREATE TABLE IF NOT EXISTS event_submissions (
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
  status TEXT NOT NULL DEFAULT 'pending_payment' CHECK (status IN ('pending_payment', 'paid_pending_review', 'queued_for_article', 'published', 'rejected')),
  payment_status TEXT NOT NULL DEFAULT 'unpaid' CHECK (payment_status IN ('unpaid', 'paid', 'refunded', 'disputed')),
  stripe_reference TEXT,
  stripe_checkout_session_id TEXT,
  stripe_payment_intent_id TEXT,
  paid_at TEXT,
  ip_hash TEXT,
  user_agent_hash TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS event_submissions_status_idx ON event_submissions(status, created_at);
CREATE INDEX IF NOT EXISTS event_submissions_payment_idx ON event_submissions(payment_status, created_at);
CREATE INDEX IF NOT EXISTS event_submissions_email_idx ON event_submissions(organizer_email, created_at);
