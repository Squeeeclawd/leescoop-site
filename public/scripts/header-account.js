const account = document.querySelector('[data-header-account]');

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'same-origin',
    ...options,
    headers: {
      ...(options.body ? { 'content-type': 'application/json' } : {}),
      ...(options.headers || {})
    }
  });
  const data = await response.json().catch(() => null);
  if (!data || !response.ok || data.ok === false) throw new Error(data?.error || 'Account unavailable');
  return data;
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function showLoggedOut() {
  if (!account) return;
  const authed = account.querySelector('[data-header-authed]');
  const login = account.querySelector('[data-header-login]');
  const status = account.querySelector('[data-header-login-status]');
  if (authed) {
    authed.hidden = true;
    authed.style.display = 'none';
  }
  if (login) {
    login.hidden = false;
    login.style.display = '';
  }
  if (status) status.textContent = '';
  account.hidden = false;
}

function showLoggedIn(user) {
  if (!account) return;
  const authed = account.querySelector('[data-header-authed]');
  const login = account.querySelector('[data-header-login]');
  const username = account.querySelector('[data-header-username]');
  const admin = account.querySelector('[data-header-admin]');
  if (username) username.textContent = user.username;
  if (admin) admin.hidden = !['admin', 'moderator'].includes(user.role);
  if (login) {
    login.hidden = true;
    login.style.display = 'none';
  }
  if (authed) {
    authed.hidden = false;
    authed.style.display = '';
  }
  account.hidden = false;
}

async function refreshHeaderAccount() {
  if (!account) return;
  const logout = account.querySelector('[data-header-logout]');
  const loginForm = account.querySelector('[data-header-login-form]');
  const loginDetails = account.querySelector('[data-header-login]');
  const loginStatus = account.querySelector('[data-header-login-status]');

  try {
    const data = await api('/api/auth/me');
    if (data.user) showLoggedIn(data.user);
    else showLoggedOut();
  } catch {
    showLoggedOut();
  }

  logout?.addEventListener('click', async () => {
    logout.disabled = true;
    try {
      await api('/api/auth/logout', { method: 'POST' });
      showLoggedOut();
      window.dispatchEvent(new CustomEvent('leescoop:auth-change'));
    } catch {
      logout.disabled = false;
    }
  });

  loginForm?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const submit = loginForm.querySelector('button[type="submit"]');
    if (loginStatus) loginStatus.textContent = 'Logging in…';
    if (submit) submit.disabled = true;
    try {
      const data = await api('/api/auth/login', { method: 'POST', body: JSON.stringify(formData(loginForm)) });
      loginForm.reset();
      if (loginDetails instanceof HTMLDetailsElement) loginDetails.open = false;
      showLoggedIn(data.user);
      window.dispatchEvent(new CustomEvent('leescoop:auth-change'));
    } catch (error) {
      if (loginStatus) loginStatus.textContent = error.message;
    } finally {
      if (submit) submit.disabled = false;
    }
  });
}

refreshHeaderAccount();
