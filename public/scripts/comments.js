const roots = document.querySelectorAll('[data-comments-root]');

function fmtDate(value) {
  try {
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    }).format(new Date(value));
  } catch {
    return '';
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    ...options,
    headers: {
      ...(options.body ? { 'content-type': 'application/json' } : {}),
      ...(options.headers || {})
    }
  });
  const data = await response.json().catch(() => ({ ok: false, error: 'Comments are not available in this preview yet.' }));
  if (!response.ok || data.ok === false) throw new Error(data.error || 'Something went sideways.');
  return data;
}

function setStatus(root, message, tone = '') {
  const status = root.querySelector('[data-comments-status]');
  if (!status) return;
  status.textContent = message || '';
  status.dataset.tone = tone;
}

function renderUser(root, user) {
  const guestBox = root.querySelector('[data-guest-box]');
  const userBox = root.querySelector('[data-user-box]');
  const commentForm = root.querySelector('[data-comment-form]');
  const username = root.querySelector('[data-current-username]');
  if (user) {
    if (guestBox) guestBox.hidden = true;
    if (userBox) userBox.hidden = false;
    if (commentForm) commentForm.hidden = false;
    if (username) username.textContent = user.username;
  } else {
    if (guestBox) guestBox.hidden = false;
    if (userBox) userBox.hidden = true;
    if (commentForm) commentForm.hidden = true;
    if (username) username.textContent = '';
  }
}

function commentNode(comment) {
  const article = document.createElement('article');
  article.className = 'comment-card';

  const meta = document.createElement('div');
  meta.className = 'comment-meta';

  const author = document.createElement('strong');
  author.textContent = comment.username || 'local';
  meta.append(author);

  const time = document.createElement('time');
  time.dateTime = comment.createdAt;
  time.textContent = fmtDate(comment.createdAt);
  meta.append(time);

  const body = document.createElement('p');
  body.className = 'comment-body';
  body.textContent = comment.body;

  article.append(meta, body);
  return article;
}

function renderComments(root, comments) {
  const list = root.querySelector('[data-comments-list]');
  const count = root.querySelector('[data-comments-count]');
  if (count) count.textContent = comments.length === 1 ? '1 comment' : `${comments.length} comments`;
  if (!list) return;
  list.innerHTML = '';
  if (!comments.length) {
    const empty = document.createElement('p');
    empty.className = 'comments-empty';
    empty.textContent = 'No comments yet. Be first, if you dare.';
    list.append(empty);
    return;
  }
  comments.forEach((comment) => list.append(commentNode(comment)));
}

async function refresh(root) {
  const slug = root.dataset.articleSlug;
  const [commentsData, meData] = await Promise.all([
    api(`/api/comments?slug=${encodeURIComponent(slug)}`),
    api('/api/auth/me')
  ]);
  renderComments(root, commentsData.comments || []);
  renderUser(root, meData.user || null);
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function init(root) {
  const slug = root.dataset.articleSlug;
  const loginForm = root.querySelector('[data-login-form]');
  const signupForm = root.querySelector('[data-signup-form]');
  const commentForm = root.querySelector('[data-comment-form]');
  const logoutButton = root.querySelector('[data-logout-button]');

  refresh(root).catch((error) => {
    renderComments(root, []);
    renderUser(root, null);
    setStatus(root, error.message || 'Comments are not available yet.', 'warn');
  });

  loginForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    setStatus(root, 'Logging in…');
    try {
      await api('/api/auth/login', { method: 'POST', body: JSON.stringify(formData(loginForm)) });
      loginForm.reset();
      await refresh(root);
      setStatus(root, 'Logged in.', 'ok');
    } catch (error) {
      setStatus(root, error.message, 'error');
    }
  });

  signupForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    setStatus(root, 'Creating account…');
    try {
      await api('/api/auth/signup', { method: 'POST', body: JSON.stringify(formData(signupForm)) });
      signupForm.reset();
      await refresh(root);
      setStatus(root, 'Account created. You’re in.', 'ok');
    } catch (error) {
      setStatus(root, error.message, 'error');
    }
  });

  logoutButton?.addEventListener('click', async () => {
    setStatus(root, 'Logging out…');
    try {
      await api('/api/auth/logout', { method: 'POST' });
      await refresh(root);
      setStatus(root, 'Logged out.', 'ok');
    } catch (error) {
      setStatus(root, error.message, 'error');
    }
  });

  commentForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = formData(commentForm);
    data.articleSlug = slug;
    setStatus(root, 'Posting…');
    try {
      await api('/api/comments', { method: 'POST', body: JSON.stringify(data) });
      commentForm.reset();
      await refresh(root);
      setStatus(root, 'Posted. Thanks for keeping it local.', 'ok');
    } catch (error) {
      setStatus(root, error.message, 'error');
    }
  });
}

roots.forEach(init);
