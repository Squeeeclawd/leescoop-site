const DEFAULT_FROM = 'LeeScoop <notifications@leescoop.com>';

function splitEmails(value) {
  return String(value || '')
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function escapeHtml(value) {
  return String(value || '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[char]));
}

function textLine(label, value) {
  return value ? `${label}: ${value}\n` : '';
}

function imageSummary(submission) {
  if (submission.image_preference === 'generate') return 'Generate LeeScoop cover image';
  const parts = ['Provided by submitter'];
  if (submission.image_url) parts.push(`link: ${submission.image_url}`);
  if (submission.image_upload_name) {
    const dimensions = submission.image_upload_width && submission.image_upload_height
      ? `${submission.image_upload_width} × ${submission.image_upload_height}px`
      : '';
    parts.push([submission.image_upload_name, dimensions].filter(Boolean).join(' · '));
  }
  return parts.join('; ');
}

function htmlRow(label, value) {
  return value ? `<p><strong>${escapeHtml(label)}:</strong> ${escapeHtml(value)}</p>` : '';
}

function buildPaidSubmissionMessage(submission) {
  const adminUrl = 'https://leescoop.com/admin/event-submissions/';
  const subject = `New paid LeeScoop featured event: ${submission.event_name || 'Event submission'}`;
  const text = [
    'A LeeScoop featured event submission has been paid and is ready for review.\n\n',
    textLine('Event', submission.event_name),
    textLine('Date', submission.event_date),
    textLine('Time', submission.event_time),
    textLine('Venue', submission.venue),
    textLine('City', submission.city),
    textLine('Address', submission.address),
    textLine('Organizer', submission.organizer_name),
    textLine('Organizer email', submission.organizer_email),
    textLine('Organizer phone', submission.organizer_phone),
    textLine('Expected attendance', submission.expected_attendance),
    textLine('Image preference', imageSummary(submission)),
    textLine('Image notes', submission.image_notes),
    textLine('Event URL', submission.event_url),
    textLine('Ticket URL', submission.ticket_url),
    textLine('Stripe checkout session', submission.stripe_checkout_session_id),
    textLine('Stripe payment intent', submission.stripe_payment_intent_id),
    textLine('Submission ID', submission.id),
    '\nDescription:\n',
    submission.description || '—',
    submission.notes ? `\n\nNotes:\n${submission.notes}` : '',
    `\n\nAdmin queue: ${adminUrl}\n`
  ].join('');

  const html = `
    <div style="font-family:Arial,sans-serif;line-height:1.5;color:#0b2230;max-width:680px">
      <h2 style="margin:0 0 12px">New paid LeeScoop featured event</h2>
      <p>A featured event submission has been paid and is ready for review.</p>
      ${htmlRow('Event', submission.event_name)}
      ${htmlRow('Date', submission.event_date)}
      ${htmlRow('Time', submission.event_time)}
      ${htmlRow('Venue', submission.venue)}
      ${htmlRow('City', submission.city)}
      ${htmlRow('Address', submission.address)}
      ${htmlRow('Organizer', submission.organizer_name)}
      ${htmlRow('Organizer email', submission.organizer_email)}
      ${htmlRow('Organizer phone', submission.organizer_phone)}
      ${htmlRow('Expected attendance', submission.expected_attendance)}
      ${htmlRow('Image preference', imageSummary(submission))}
      ${htmlRow('Image notes', submission.image_notes)}
      ${submission.image_upload_data_url ? `<p><strong>Uploaded image:</strong><br><img src="${escapeHtml(submission.image_upload_data_url)}" alt="Uploaded event image" style="max-width:100%;height:auto;border-radius:12px;border:1px solid #d8e5e8"></p>` : ''}
      ${submission.event_url ? `<p><strong>Event URL:</strong> <a href="${escapeHtml(submission.event_url)}">${escapeHtml(submission.event_url)}</a></p>` : ''}
      ${submission.ticket_url ? `<p><strong>Ticket URL:</strong> <a href="${escapeHtml(submission.ticket_url)}">${escapeHtml(submission.ticket_url)}</a></p>` : ''}
      ${htmlRow('Stripe checkout session', submission.stripe_checkout_session_id)}
      ${htmlRow('Stripe payment intent', submission.stripe_payment_intent_id)}
      ${htmlRow('Submission ID', submission.id)}
      <h3>Description</h3>
      <p>${escapeHtml(submission.description || '—').replace(/\n/g, '<br>')}</p>
      ${submission.notes ? `<h3>Notes</h3><p>${escapeHtml(submission.notes).replace(/\n/g, '<br>')}</p>` : ''}
      <p><a href="${adminUrl}">Open LeeScoop admin queue</a></p>
    </div>
  `;

  return { subject, text, html };
}

async function sendWithResend(env, { to, from, subject, text, html }) {
  const key = env?.RESEND_API_KEY || '';
  if (!key) return { ok: false, skipped: true, reason: 'missing RESEND_API_KEY' };
  const response = await fetch('https://api.resend.com/emails', {
    method: 'POST',
    headers: {
      authorization: `Bearer ${key}`,
      'content-type': 'application/json'
    },
    body: JSON.stringify({ from, to, subject, text, html })
  });
  const body = await response.text();
  return { ok: response.ok, provider: 'resend', status: response.status, body: body.slice(0, 1000) };
}

async function sendWithMailChannels({ to, from, subject, text, html }) {
  const match = String(from || DEFAULT_FROM).match(/^(.*?)<([^>]+)>$/);
  const fromEmail = match ? match[2].trim() : String(from || DEFAULT_FROM).trim();
  const fromName = match ? match[1].trim() : 'LeeScoop';
  const response = await fetch('https://api.mailchannels.net/tx/v1/send', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({
      personalizations: [{ to: to.map((email) => ({ email })) }],
      from: { email: fromEmail, name: fromName || 'LeeScoop' },
      subject,
      content: [
        { type: 'text/plain', value: text },
        { type: 'text/html', value: html }
      ]
    })
  });
  const body = await response.text();
  return { ok: response.ok, provider: 'mailchannels', status: response.status, body: body.slice(0, 1000) };
}

export async function sendPaidEventSubmissionEmail(env, submission) {
  const to = splitEmails(env?.FEATURE_EVENT_NOTIFY_EMAILS || env?.ADMIN_NOTIFY_EMAILS);
  if (!to.length) return { ok: false, skipped: true, reason: 'missing recipients' };

  const from = env?.FEATURE_EVENT_NOTIFY_FROM || env?.ADMIN_NOTIFY_FROM || DEFAULT_FROM;
  const message = buildPaidSubmissionMessage(submission);
  const payload = { to, from, ...message };

  try {
    const resend = await sendWithResend(env, payload);
    if (resend.ok) return resend;
    const provider = String(env?.FEATURE_EVENT_EMAIL_PROVIDER || '').toLowerCase();
    if (provider === 'resend') return resend;
    const mailchannels = await sendWithMailChannels(payload);
    return mailchannels.ok ? mailchannels : { ok: false, resend, mailchannels };
  } catch (error) {
    return { ok: false, error: String(error?.message || error) };
  }
}
