# LeeScoop comments + low-profile login plan

Goal: add article-level discussion with a **freedom-first comment model**: people can post with a low-profile username/password account, comments appear immediately, and Anthony/mods remove or ban only when needed. Email is optional and must be clearly labeled optional.

## User-facing requirements

- Readers can read comments without logging in.
- To comment, a reader creates a low-profile account with:
  - username
  - password
  - optional email address
- The email field must say clearly: `Email optional — only used for account recovery or moderation contact if you provide it.`
- No required email verification.
- No OAuth/social login in v1.
- No public real names required.
- Comments appear immediately after posting.
- Anthony/mod account can hide, unhide, delete, and ban users.
- Moderation is reactive/manual, not pre-approval.

## Recommendation

Use a tiny custom auth/comments backend instead of Supabase Auth.

Reason: Supabase Auth is excellent, but it is email-centered. For “username + password, optional email,” a small purpose-built backend is cleaner and avoids fake-email nonsense.

Best fit for LeeScoop:

- **Cloudflare Pages** for the Astro site
- **Cloudflare Worker/Pages Functions** for comment/auth API routes
- **Cloudflare D1** for users, comments, sessions, and moderation state
- **Cloudflare Turnstile** for signup/comment spam throttling

If LeeScoop stays static, the comments UI can still talk to these API routes from article pages.

## Philosophy

Default posture: let locals talk.

This should feel closer to an old-school local message board than a locked-down corporate comment system:
- pseudonymous by default
- email optional
- posts appear immediately
- moderation exists, but mostly as cleanup and anti-abuse
- keep the interface light and non-creepy

## Important security stance

“Low profile” is fine. “Loose security” is not.

Do not store raw passwords. Ever. Store only password hashes.

Minimum safe implementation:
- password hashing with Argon2id if available; otherwise bcrypt/scrypt through a vetted library
- HttpOnly secure session cookies
- CSRF protection for write actions
- rate limits on signup, login, and comment submit
- Turnstile on signup; optional/invisible Turnstile on comment submit if spam appears
- plain-text comments only
- no HTML rendering from users
- max comment length, e.g. 1,500 characters
- visible comments by default, with fast hide/delete tools
- ban controls for accounts/IP-hash patterns that abuse the system

## Reader flow

1. Article page loads visible comments for that article slug.
2. Logged-out readers see:
   - visible comments
   - `Log in or create a username to comment`
3. Signup form:
   - Username
   - Password
   - Email optional
   - tiny note explaining optional email
4. New comment is submitted and appears immediately.
5. Reader sees: `Posted. Thanks for keeping it local.`
6. If needed, a moderator can hide/delete it later.

## Moderator/admin flow

Create at least one admin/mod account manually.

Capabilities:
- view newest comments across all articles
- hide comment
- unhide comment
- soft-delete comment
- hard-delete only if absolutely needed
- ban user
- unban user
- see optional email only in moderator/admin views
- see recent moderation history
- filter by article slug/user/status

Admin route:

```text
/admin/comments
```

Keep this route hidden from public navigation. It still needs authentication and role checks; hidden is not security, because the internet has raccoons with keyboards.

## Data model

### `users`

```sql
id text primary key,
username text not null unique,
username_normalized text not null unique,
password_hash text not null,
email text,
email_is_optional integer not null default 1,
role text not null default 'user', -- user | moderator | admin
status text not null default 'active', -- active | banned | deleted
created_at text not null,
updated_at text not null,
last_login_at text
```

### `sessions`

```sql
id text primary key,
user_id text not null references users(id) on delete cascade,
session_hash text not null unique,
created_at text not null,
expires_at text not null,
revoked_at text,
user_agent_hash text,
ip_hash text
```

### `article_comments`

```sql
id text primary key,
article_slug text not null,
user_id text not null references users(id) on delete cascade,
parent_id text references article_comments(id) on delete cascade,
body text not null,
status text not null default 'visible', -- visible | hidden | deleted | flagged
moderation_reason text,
created_at text not null,
updated_at text not null,
hidden_at text,
hidden_by text references users(id),
deleted_at text,
deleted_by text references users(id)
```

### `moderation_log`

```sql
id text primary key,
moderator_id text not null references users(id),
action text not null, -- hide | unhide | delete | ban | unban | flag | unflag
entity_type text not null, -- comment | user
entity_id text not null,
note text,
created_at text not null
```

### Optional later: `comment_reports`

```sql
id text primary key,
comment_id text not null references article_comments(id) on delete cascade,
reporter_id text references users(id) on delete set null,
reason text not null,
status text not null default 'open',
created_at text not null
```

## API routes

Public/read:

```text
GET /api/comments?slug=<article-slug>        # visible comments only
GET /api/auth/me
```

Auth:

```text
POST /api/auth/signup
POST /api/auth/login
POST /api/auth/logout
```

User comment actions:

```text
POST /api/comments                           # creates visible comment immediately
DELETE /api/comments/:id                     # own recent comment, soft-delete; optional
```

Moderator/admin:

```text
GET /api/admin/comments?status=visible|hidden|flagged|deleted
POST /api/admin/comments/:id/hide
POST /api/admin/comments/:id/unhide
POST /api/admin/comments/:id/delete
POST /api/admin/users/:id/ban
POST /api/admin/users/:id/unban
```

## Astro integration

Add:

- `src/components/Comments.astro`
- `src/components/CommentForm.astro` or client-rendered equivalent
- `src/pages/admin/comments.astro`
- `public/scripts/comments.js`
- `public/scripts/admin-comments.js`

Update article templates:

- `src/pages/[slug].astro`
- `src/pages/articles/[slug].astro`

Add below article body:

```astro
<Comments articleSlug={article.slug} />
```

## UI copy

Signup form email label:

```text
Email optional
```

Helper text:

```text
You can leave this blank. If you add one, it is only used for account recovery or moderation contact.
```

Post success message:

```text
Posted. Thanks for keeping it local.
```

Community note:

```text
Comments post immediately. Keep it useful, local, and human. Anthony/mods may remove spam, threats, doxxing, or pointless garbage.
```

Soft moderation note shown near comment box:

```text
No real name required. Email is optional. Don’t be a menace.
```

## Abuse controls without killing the vibe

Use guardrails that are mostly invisible:
- rate-limit signups by IP hash
- rate-limit comments by user and IP hash
- block repeat identical comments
- auto-flag comments with too many links
- auto-flag obvious slurs/threat patterns for moderator review, but do not overdo the nanny filter
- let moderators hide/ban quickly from `/admin/comments`

Suggested limits:
- signup: 3 per IP hash per hour
- login attempts: 10 per username/IP hash per hour
- comments: 10 per user per hour, 40 per day
- links: max 2 links per comment in v1
- body length: 20–1,500 characters

## Implementation phases

### Phase 1 — database + API skeleton

- Add D1 database.
- Add users/sessions/comments/moderation tables.
- Add API routes for signup/login/logout/me.
- Seed Anthony admin/mod account manually.

### Phase 2 — article comments

- Add comments component to article templates.
- Load visible comments by article slug.
- Add signup/login form.
- Add comment submit as immediately `visible`.
- Add rate limits and basic spam checks.

### Phase 3 — manual moderation

- Add `/admin/comments` page.
- Require moderator/admin role.
- Show newest comments first.
- Add quick hide/delete/ban buttons.
- Add hidden/deleted filters.
- Write moderation log entries.

### Phase 4 — polish

- Comment counts on article cards/homepage.
- One-level replies.
- Optional report button.
- Optional account recovery using optional email.
- Optional moderator alerts for flagged/high-link comments.

## Practical v1 choice

Launch with:
- username + password signup
- optional email, clearly labeled optional
- one manually created mod/admin account
- comments appear immediately
- manual cleanup/hide/delete/ban tools
- plain text only
- no replies/threading at first
- simple `/admin/comments` moderation page

This keeps the freedom-first feel while still giving Anthony a broom for spam, weirdos, and the inevitable comment-section raccoons.
