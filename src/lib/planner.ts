import { articlePath, eventArchiveCutoff, LEE_COUNTY_TIME_ZONE, siteNow, type Article } from './content.ts';
import { eventMapUrl } from './eventMap.ts';

const plannerDate = new Intl.DateTimeFormat('en-US', {
  timeZone: LEE_COUNTY_TIME_ZONE, year: 'numeric', month: 'short', day: 'numeric'
});

export function makePlannerEntry(article: Article, now = siteNow()) {
  const { data, slug } = article;
  const event = data.contentKind === 'event';
  const start = event ? data.eventDate : data.date;
  const end = eventArchiveCutoff(article);
  const dateText = start && end && end > start
    ? plannerDate.formatRange(start, end)
    : start ? plannerDate.format(start) : 'Date TBA';
  const upcoming = event && (!end || end >= now);
  const mapHref = upcoming ? eventMapUrl(data.address, data.city) : null;
  return {
    ...(upcoming && data.eventTime && { schedule: data.eventTime }),
    ...(mapHref && { mapHref, address: data.address }),
    slug, title: data.title, href: articlePath(article), kind: data.contentKind,
    dateText, place: data.venue || data.location || data.city || data.category,
    startsAt: start?.getTime() ?? null, endsAt: end?.getTime() ?? null,
    calendarHref: event && start && end && end >= now ? `/calendar/${slug}.ics` : null
  };
}

export type PlannerEntry = ReturnType<typeof makePlannerEntry>;

export function groupSavedPlans(entries: readonly PlannerEntry[], slugs: Iterable<string>, now = new Date()) {
  const saved = new Set(slugs);
  const groups: Record<'upcoming' | 'reading' | 'past', PlannerEntry[]> = {
    upcoming: [], reading: [], past: []
  };
  for (const entry of entries) {
    if (!saved.has(entry.slug)) continue;
    if (entry.kind === 'news') groups.reading.push(entry);
    else if (entry.endsAt !== null && entry.endsAt < now.getTime()) groups.past.push(entry);
    else groups.upcoming.push(entry);
  }
  const byTitle = (a: PlannerEntry, b: PlannerEntry) => a.title.localeCompare(b.title, 'en');
  groups.upcoming.sort((a, b) => (a.startsAt ?? Infinity) - (b.startsAt ?? Infinity) || byTitle(a, b));
  groups.reading.sort((a, b) => (b.startsAt ?? 0) - (a.startsAt ?? 0) || byTitle(a, b));
  groups.past.sort((a, b) => (b.endsAt ?? 0) - (a.endsAt ?? 0) || byTitle(a, b));
  return groups;
}
