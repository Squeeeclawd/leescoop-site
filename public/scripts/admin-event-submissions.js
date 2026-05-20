(() => {
  const root = document.querySelector('[data-admin-event-submissions]');
  if (!(root instanceof HTMLElement)) return;

  const escapeHtml = (value) => String(value || '').replace(/[&<>"]/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;'
  }[char]));

  const linkHtml = (url, label) => {
    if (!url) return '';
    return `<a class="read-link" href="${escapeHtml(url)}" target="_blank" rel="noopener">${escapeHtml(label)}</a>`;
  };

  const render = (submissions) => {
    if (!submissions.length) {
      root.innerHTML = '<p class="small-note">No event submissions yet.</p>';
      return;
    }
    root.innerHTML = submissions.map((item) => `
      <article class="admin-event-submission-card">
        <div class="admin-event-submission-topline">
          <div>
            <p class="eyebrow">${escapeHtml(item.paymentStatus)} · ${escapeHtml(item.status)}</p>
            <h2>${escapeHtml(item.eventName)}</h2>
          </div>
          <time>${escapeHtml(item.eventDate)}${item.eventTime ? ` · ${escapeHtml(item.eventTime)}` : ''}</time>
        </div>
        <dl>
          <div><dt>Where</dt><dd>${escapeHtml(item.venue)}${item.city ? ` · ${escapeHtml(item.city)}` : ''}${item.address ? `<br>${escapeHtml(item.address)}` : ''}</dd></div>
          <div><dt>Organizer</dt><dd>${escapeHtml(item.organizerName)} · ${escapeHtml(item.organizerEmail)}${item.organizerPhone ? ` · ${escapeHtml(item.organizerPhone)}` : ''}</dd></div>
          <div><dt>Description</dt><dd>${escapeHtml(item.description)}</dd></div>
          ${item.notes ? `<div><dt>Notes</dt><dd>${escapeHtml(item.notes)}</dd></div>` : ''}
          <div><dt>Links</dt><dd>${[linkHtml(item.eventUrl, 'Event page'), linkHtml(item.ticketUrl, 'Tickets / RSVP')].filter(Boolean).join(' · ') || '—'}</dd></div>
        </dl>
      </article>
    `).join('');
  };

  fetch('/api/admin/event-submissions?limit=100', { headers: { accept: 'application/json' } })
    .then(async (response) => {
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.ok) throw new Error(data.error || 'Unable to load event submissions.');
      render(data.submissions || []);
    })
    .catch((error) => {
      root.innerHTML = `<p class="small-note">${escapeHtml(error.message || 'Unable to load event submissions.')}</p>`;
    });
})();
