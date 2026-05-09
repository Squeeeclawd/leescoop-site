const root = document.querySelector('[data-admin-comments-root]');

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    ...options,
    headers: {
      ...(options.body ? { 'content-type': 'application/json' } : {}),
      ...(options.headers || {})
    }
  });
  const data = await response.json().catch(() => ({ ok: false, error: 'Admin API is not available in this preview yet.' }));
  if (!response.ok || data.ok === false) throw new Error(data.error || 'Request failed.');
  return data;
}

function setStatus(message, tone = '') {
  const status = root?.querySelector('[data-admin-status]');
  if (!status) return;
  status.textContent = message || '';
  status.dataset.tone = tone;
}

function fmtDate(value) {
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit'
    }).format(new Date(value));
  } catch {
    return '';
  }
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function renderLogin(show) {
  const box = root.querySelector('[data-admin-login-box]');
  const tools = root.querySelector('[data-admin-tools]');
  if (box) box.hidden = !show;
  if (tools) tools.hidden = show;
}

function commentCard(comment) {
  const card = document.createElement('article');
  card.className = 'admin-comment-card';

  const meta = document.createElement('div');
  meta.className = 'comment-meta';
  const left = document.createElement('strong');
  left.textContent = `${comment.username} · ${comment.article_slug}`;
  const right = document.createElement('time');
  right.dateTime = comment.created_at;
  right.textContent = fmtDate(comment.created_at);
  meta.append(left, right);

  const body = document.createElement('p');
  body.className = 'comment-body';
  body.textContent = comment.body;

  const details = document.createElement('p');
  details.className = 'admin-comment-details';
  details.textContent = `status: ${comment.status} · user: ${comment.user_status}${comment.email ? ` · email: ${comment.email}` : ' · email: none'}`;

  const actions = document.createElement('div');
  actions.className = 'admin-comment-actions';

  const hide = document.createElement('button');
  hide.className = 'button secondary comments-small-button';
  hide.type = 'button';
  hide.textContent = comment.status === 'hidden' ? 'Unhide' : 'Hide';
  hide.addEventListener('click', () => moderateComment(comment.id, comment.status === 'hidden' ? 'unhide' : 'hide'));

  const del = document.createElement('button');
  del.className = 'button secondary comments-small-button danger-button';
  del.type = 'button';
  del.textContent = 'Delete';
  del.addEventListener('click', () => moderateComment(comment.id, 'delete'));

  const ban = document.createElement('button');
  ban.className = 'button secondary comments-small-button danger-button';
  ban.type = 'button';
  ban.textContent = comment.user_status === 'banned' ? 'Unban user' : 'Ban user';
  ban.addEventListener('click', () => moderateUser(comment.user_id, comment.user_status === 'banned' ? 'unban' : 'ban'));

  actions.append(hide, del, ban);
  card.append(meta, body, details, actions);
  return card;
}

function renderComments(comments) {
  const list = root.querySelector('[data-admin-comments-list]');
  const count = root.querySelector('[data-admin-count]');
  if (count) count.textContent = comments.length === 1 ? '1 comment' : `${comments.length} comments`;
  list.innerHTML = '';
  if (!comments.length) {
    const empty = document.createElement('p');
    empty.className = 'comments-empty';
    empty.textContent = 'Nothing in this bucket.';
    list.append(empty);
    return;
  }
  comments.forEach((comment) => list.append(commentCard(comment)));
}

async function load() {
  const filter = root.querySelector('[data-status-filter]')?.value || 'visible';
  setStatus('Loading…');
  try {
    const me = await api('/api/auth/me');
    if (!me.user || !['moderator', 'admin'].includes(me.user.role)) {
      renderLogin(true);
      renderComments([]);
      setStatus(me.user ? 'That account is not a moderator.' : 'Moderator login required.', 'warn');
      return;
    }
    renderLogin(false);
    const data = await api(`/api/admin/comments?status=${encodeURIComponent(filter)}`);
    renderComments(data.comments || []);
    setStatus('Loaded.', 'ok');
  } catch (error) {
    renderLogin(true);
    renderComments([]);
    setStatus(error.message, 'error');
  }
}

async function moderateComment(id, action) {
  if (action === 'delete' && !confirm('Delete this comment? It will be hidden from public view.')) return;
  setStatus(`${action}…`);
  try {
    await api(`/api/admin/comments/${encodeURIComponent(id)}/${action}`, {
      method: 'POST',
      body: JSON.stringify({ reason: action === 'delete' ? 'Deleted by moderator' : 'Hidden by moderator' })
    });
    await load();
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

async function moderateUser(id, action) {
  if (action === 'ban' && !confirm('Ban this user and revoke their sessions?')) return;
  setStatus(`${action} user…`);
  try {
    await api(`/api/admin/users/${encodeURIComponent(id)}/${action}`, {
      method: 'POST',
      body: JSON.stringify({ reason: action === 'ban' ? 'Banned by moderator' : 'Unbanned by moderator' })
    });
    await load();
  } catch (error) {
    setStatus(error.message, 'error');
  }
}

if (root) {
  const loginForm = root.querySelector('[data-admin-login-form]');
  loginForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    setStatus('Logging in…');
    try {
      await api('/api/auth/login', { method: 'POST', body: JSON.stringify(formData(loginForm)) });
      loginForm.reset();
      await load();
    } catch (error) {
      setStatus(error.message, 'error');
    }
  });
  root.querySelector('[data-status-filter]')?.addEventListener('change', load);
  root.querySelector('[data-admin-refresh]')?.addEventListener('click', load);
  load();
}
