// Date reminders deliberately avoid inventing performance times for ongoing runs.
export function calendarReminder(slug: string, title: string, start: string, end: string, location: string, url: string) {
  const escape = (value: string) => value.replace(/\\/g, '\\\\').replace(/\r?\n/g, '\\n').replace(/;/g, '\\;').replace(/,/g, '\\,');
  const next = new Date(`${end}T12:00:00Z`); next.setUTCDate(next.getUTCDate() + 1);
  const date = (key: string) => key.replaceAll('-', '');
  const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//LeeScoop//Date reminders//EN', 'BEGIN:VEVENT', `UID:${slug}@leescoop.com`, 'DTSTAMP:20260918T000000Z', `DTSTART;VALUE=DATE:${date(start)}`, `DTEND;VALUE=DATE:${date(next.toISOString().slice(0, 10))}`, `SUMMARY:${escape(title)}`, `LOCATION:${escape(location)}`, `DESCRIPTION:${escape('Date reminder only. A run may have select performances. Confirm dates and times with the organizer. ' + url)}`, `URL:${url}`, 'TRANSP:TRANSPARENT', 'END:VEVENT', 'END:VCALENDAR'];
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
