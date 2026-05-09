-- LeeScoop comments/auth schema for Cloudflare D1
-- Apply with: wrangler d1 migrations apply <database-name> --remote

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  username_normalized TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  email TEXT,
  email_is_optional INTEGER NOT NULL DEFAULT 1,
  role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'moderator', 'admin')),
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'banned', 'deleted')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  last_login_at TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  session_hash TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT,
  user_agent_hash TEXT,
  ip_hash TEXT
);

CREATE INDEX IF NOT EXISTS sessions_user_idx ON sessions(user_id);
CREATE INDEX IF NOT EXISTS sessions_hash_idx ON sessions(session_hash);
CREATE INDEX IF NOT EXISTS sessions_expiry_idx ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS article_comments (
  id TEXT PRIMARY KEY,
  article_slug TEXT NOT NULL,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  parent_id TEXT REFERENCES article_comments(id) ON DELETE CASCADE,
  body TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'visible' CHECK (status IN ('visible', 'hidden', 'deleted', 'flagged')),
  moderation_reason TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  hidden_at TEXT,
  hidden_by TEXT REFERENCES users(id),
  deleted_at TEXT,
  deleted_by TEXT REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS comments_article_visible_idx ON article_comments(article_slug, status, created_at);
CREATE INDEX IF NOT EXISTS comments_user_idx ON article_comments(user_id, created_at);
CREATE INDEX IF NOT EXISTS comments_status_idx ON article_comments(status, created_at);

CREATE TABLE IF NOT EXISTS moderation_log (
  id TEXT PRIMARY KEY,
  moderator_id TEXT NOT NULL REFERENCES users(id),
  action TEXT NOT NULL CHECK (action IN ('hide', 'unhide', 'delete', 'ban', 'unban', 'flag', 'unflag')),
  entity_type TEXT NOT NULL CHECK (entity_type IN ('comment', 'user')),
  entity_id TEXT NOT NULL,
  note TEXT,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS moderation_log_entity_idx ON moderation_log(entity_type, entity_id, created_at);
CREATE INDEX IF NOT EXISTS moderation_log_moderator_idx ON moderation_log(moderator_id, created_at);

CREATE TABLE IF NOT EXISTS rate_limits (
  key TEXT PRIMARY KEY,
  window_start INTEGER NOT NULL,
  count INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS rate_limits_window_idx ON rate_limits(window_start);
