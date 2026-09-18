// Date reminders deliberately avoid inventing performance times for ongoing runs.
export function calendarReminder(slug: string, title: string, start: string, end: string, location: string, url: string, createdAt = new Date()) {
  const validDateKey = (key: string) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(key)) return false;
    const parsed = new Date(`${key}T12:00:00Z`);
    return !Number.isNaN(parsed.getTime()) && parsed.toISOString().slice(0, 10) === key;
  };
  if (!validDateKey(start) || !validDateKey(end) || end < start || Number.isNaN(createdAt.getTime())) return undefined;
  const escape = (value: string) => value.replace(/\\/g, '\\\\').replace(/\r\n|\r|\n/g, '\\n').replace(/;/g, '\\;').replace(/,/g, '\\,');
  const next = new Date(`${end}T12:00:00Z`); next.setUTCDate(next.getUTCDate() + 1);
  const date = (key: string) => key.replaceAll('-', '');
  const stamp = createdAt.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}Z$/, 'Z');
  const uid = slug.replace(/[^A-Za-z0-9._~-]/g, '-');
  const safeUrl = (() => {
    try {
      if (/[\u0000-\u001F\u007F]/.test(url)) throw new TypeError('Control characters are not allowed in calendar URLs');
      const parsed = new URL(url);
      return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? parsed.href : `https://leescoop.com/${encodeURIComponent(slug)}/`;
    } catch { return `https://leescoop.com/${encodeURIComponent(slug)}/`; }
  })();
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'CALSCALE:GREGORIAN', 'PRODID:-//LeeScoop//Date reminders//EN', 'BEGIN:VEVENT', `UID:${uid}@leescoop.com`, `DTSTAMP:${stamp}`, `DTSTART;VALUE=DATE:${date(start)}`, `DTEND;VALUE=DATE:${date(next.toISOString().slice(0, 10))}`, `SUMMARY:${escape(title)}`, `LOCATION:${escape(location)}`, `DESCRIPTION:${escape('Date reminder only. A run may have select performances. Confirm dates and times with the organizer. ' + safeUrl)}`, `URL:${safeUrl}`, 'TRANSP:TRANSPARENT', 'END:VEVENT', 'END:VCALENDAR'];
  // RFC 5545 folds at octet boundaries, without splitting UTF-8 code points.
  return lines.map(line => {
    let result = '', part = '';
    for (const char of line) {
      if (new TextEncoder().encode(part + char).length > 73) { result += part + '\r\n'; part = ' '; }
      part += char;
    }
    return result + part;
  }).join('\r\n') + '\r\n';
}
