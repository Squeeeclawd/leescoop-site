# LeeScoop comments deployment notes

The comments system is implemented as Cloudflare Pages Functions + D1.

## Files

- `migrations/0001_comments.sql` — D1 schema
- `functions/api/comments.js` — public comment read/post API
- `functions/api/auth/*.js` — username/password auth
- `functions/api/admin/**` — moderation API
- `src/components/Comments.astro` — article comments UI
- `src/pages/admin/comments.astro` — moderation UI
- `public/scripts/comments.js` — article comment client
- `public/scripts/admin-comments.js` — moderation client
- `wrangler.toml.example` — example D1 binding config

## Cloudflare setup

1. Create a D1 database, e.g. `leescoop-comments`.
2. Bind it to the Pages project as `DB`.
3. Set env var `COMMENTS_PEPPER` to a long random secret.
4. Apply migration:

```bash
wrangler d1 migrations apply leescoop-comments --remote
```

If using a local `wrangler.toml`, copy `wrangler.toml.example` to `wrangler.toml` and replace `database_id` + `COMMENTS_PEPPER`.

## Creating the mod/admin account

1. Deploy the site/functions.
2. Visit any article and create Anthony’s username/password account.
3. Promote that account in D1:

```sql
UPDATE users
SET role = 'admin', updated_at = datetime('now')
WHERE username_normalized = 'YOUR_USERNAME_HERE';
```

Then use:

```text
/admin/comments
```

## Behavior

- Comments are visible immediately.
- Signup asks username + password; email is optional.
- Moderators can hide, unhide, delete comments, and ban/unban users.
- Public comments are plain text only.
- API write actions use HttpOnly secure session cookies.

## Notes

- Turnstile is supported server-side if `TURNSTILE_SECRET_KEY` is configured, but the current frontend does not render a widget yet. Leave that env var unset until the widget is wired in.
- Passwords are stored as PBKDF2-SHA256 hashes with per-user salts plus `COMMENTS_PEPPER`; raw passwords are never stored.
- This is intentionally simple and reactive: freedom first, cleanup tools nearby.
