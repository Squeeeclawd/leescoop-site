(() => {
  const form = document.querySelector('[data-feature-event-form]');
  const status = document.querySelector('[data-feature-event-status]');
  if (!(form instanceof HTMLFormElement) || !(status instanceof HTMLElement)) return;

  const setStatus = (message, tone = 'neutral') => {
    status.textContent = message;
    status.dataset.tone = tone;
  };

  const fieldValue = (name) => {
    const field = form.elements.namedItem(name);
    if (field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement) return field.value.trim();
    return '';
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = form.querySelector('button[type="submit"]');
    if (button instanceof HTMLButtonElement) button.disabled = true;
    const missing = [];
    if (!fieldValue('eventDate')) missing.push('date');
    if (!fieldValue('venue')) missing.push('venue');
    if (!fieldValue('city')) missing.push('city/area');
    if (!fieldValue('description')) missing.push('description');
    if (!fieldValue('organizerName')) missing.push('organizer name');
    setStatus(missing.length ? `Saving your event details. Missing: ${missing.join(', ')} — you can still submit.` : 'Saving your event details…');

    const payload = {
      website: fieldValue('website'),
      eventName: fieldValue('eventName'),
      eventDate: fieldValue('eventDate'),
      eventTime: fieldValue('eventTime'),
      venue: fieldValue('venue'),
      city: fieldValue('city'),
      address: fieldValue('address'),
      eventUrl: fieldValue('eventUrl'),
      ticketUrl: fieldValue('ticketUrl'),
      description: fieldValue('description'),
      organizerName: fieldValue('organizerName'),
      organizerEmail: fieldValue('organizerEmail'),
      organizerPhone: fieldValue('organizerPhone'),
      expectedAttendance: fieldValue('expectedAttendance'),
      notes: fieldValue('notes')
    };

    try {
      const response = await fetch('/api/event-submissions', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.ok) throw new Error(data.error || 'Something went sideways. Please try again.');

      if (data.paymentUrl) {
        setStatus('Saved. Sending you to secure payment…', 'success');
        window.location.assign(data.paymentUrl);
        return;
      }

      form.reset();
      setStatus(data.message || 'Submission saved. LeeScoop will follow up with payment instructions.', 'success');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Something went sideways. Please try again.', 'error');
      if (button instanceof HTMLButtonElement) button.disabled = false;
    }
  });
})();
