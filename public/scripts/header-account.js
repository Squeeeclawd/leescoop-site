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

async function refreshHeaderAccount() {
  if (!account) return;
  const username = account.querySelector('[data-header-username]');
  const admin = account.querySelector('[data-header-admin]');
  const logout = account.querySelector('[data-header-logout]');

  try {
    const data = await api('/api/auth/me');
    const user = data.user;
    if (!user) {
      account.hidden = true;
      return;
    }

    if (username) username.textContent = user.username;
    if (admin) admin.hidden = !['admin', 'moderator'].includes(user.role);
    account.hidden = false;

    logout?.addEventListener('click', async () => {
      logout.disabled = true;
      try {
        await api('/api/auth/logout', { method: 'POST' });
        window.location.reload();
      } catch {
        logout.disabled = false;
      }
    }, { once: true });
  } catch {
    account.hidden = true;
  }
}

refreshHeaderAccount();
