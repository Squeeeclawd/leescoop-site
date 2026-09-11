import type { CollectionEntry } from 'astro:content';

export type Article = CollectionEntry<'articles'>;

export const LEE_COUNTY_TIME_ZONE = 'America/New_York';

export function siteNow() {
  const override = import.meta.env.LEESCOOP_NOW;
  if (override) {
    const parsed = new Date(override);
    if (!Number.isNaN(parsed.getTime())) return parsed;
  }

  return new Date();
}

const leeDateFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: LEE_COUNTY_TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit'
});

export function leeCountyDateKey(value = siteNow()) {
  return leeDateFormatter.format(value);
}

// Array.filter passes an index as its second argument; it is not a clock.
function resolvedNow(value?: Date | number) {
  return value instanceof Date ? value : siteNow();
}

export function isPublished(article: Article, now?: Date | number) {
  return !article.data.draft && article.data.date <= resolvedNow(now);
}

export function articleDisplayDate(article: Article) {
  return article.data.contentKind === 'event' ? article.data.eventDate ?? article.data.date : article.data.date;
}

// Resolve Lee County wall time independently of the build host timezone.
function leeCountyWallTime(value: Date, hour: number, minute = 0, second = 0, ms = 0) {
  const [year, month, day] = leeCountyDateKey(value).split('-').map(Number);
  const desired = Date.UTC(year, month - 1, day, hour, minute, second, ms);
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: LEE_COUNTY_TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'
  });
  let result = desired;
  for (let i = 0; i < 3; i += 1) {
    const parts = Object.fromEntries(formatter.formatToParts(new Date(result)).map((p) => [p.type, p.value]));
    const observed = Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour, +parts.minute, +parts.second, ms);
    result += desired - observed;
  }
  return new Date(result);
}

function endOfLocalDay(value: Date) {
  return leeCountyWallTime(value, 23, 59, 59, 999);
}

function clockTo24Hour(hour: number, period: string) {
  const normalized = hour % 12;
  return period.toLowerCase() === 'pm' ? normalized + 12 : normalized;
}

function cutoffFromEventTime(eventDate: Date, eventTime?: string) {
  if (!eventTime) return undefined;

  // Only infer an end from an explicit range, not doors + show times or a lone start.
  if (!/\d(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\s*[-–—]\s*\d/i.test(eventTime)) return undefined;
  const clocks = [...eventTime.matchAll(/(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b/gi)];
  if (clocks.length !== 2) return undefined;

  if (clocks.some((clock) => +clock[1] < 1 || +clock[1] > 12 || +(clock[2] ?? 0) > 59)) return undefined;

  const lastClock = clocks[clocks.length - 1];
  const hour = Number(lastClock[1]);
  const minute = Number(lastClock[2] ?? 0);
  const period = lastClock[3].replace(/\./g, '');
  const cutoff = leeCountyWallTime(eventDate, clockTo24Hour(hour, period), minute);
  if (cutoff < eventDate) {
    const nextDay = new Date(`${leeCountyDateKey(eventDate)}T12:00:00Z`);
    nextDay.setUTCDate(nextDay.getUTCDate() + 1);
    return leeCountyWallTime(nextDay, clockTo24Hour(hour, period), minute);
  }
  return cutoff;
}

export function eventArchiveCutoff(article: Article) {
  if (article.data.contentKind !== 'event') return undefined;

  // Schema coerces end values to Date: an explicit end is an exact instant.
  if (article.data.eventEndDate) return article.data.eventEndDate;
  if (!article.data.eventDate) return undefined;

  return cutoffFromEventTime(article.data.eventDate, article.data.eventTime) ?? endOfLocalDay(article.data.eventDate);
}

export function isArchivedEvent(article: Article, now?: Date | number) {
  const eventCutoff = eventArchiveCutoff(article);
  if (!eventCutoff) return false;
  return eventCutoff.getTime() < resolvedNow(now).getTime();
}

export function isActiveArticle(article: Article, now?: Date | number) {
  const clock = resolvedNow(now);
  return isPublished(article, clock) && !isArchivedEvent(article, clock);
}

export function sortArticlesForFeed(articles: Article[], now = siteNow()) {
  const todayKey = leeCountyDateKey(now);

  return [...articles].sort((a, b) => {
    const pinnedDelta = Number(b.data.pinned) - Number(a.data.pinned);
    if (pinnedDelta !== 0) return pinnedDelta;

    const aDisplayDate = articleDisplayDate(a);
    const bDisplayDate = articleDisplayDate(b);
    const aDisplayTime = aDisplayDate?.getTime() ?? Number.MAX_SAFE_INTEGER;
    const bDisplayTime = bDisplayDate?.getTime() ?? Number.MAX_SAFE_INTEGER;
    const aCurrentOrFuture = aDisplayDate ? leeCountyDateKey(aDisplayDate) >= todayKey : false;
    const bCurrentOrFuture = bDisplayDate ? leeCountyDateKey(bDisplayDate) >= todayKey : false;

    // One live timeline: current/future news + events first, chronological by display date.
    // News uses publish date; events use event date. Older news remains visible, but falls below current items.
    if (aCurrentOrFuture !== bCurrentOrFuture) return aCurrentOrFuture ? -1 : 1;
    if (aCurrentOrFuture && bCurrentOrFuture) return aDisplayTime - bDisplayTime;

    // Archive-like leftovers: newest news/evergreen items first. Expired events are already filtered elsewhere.
    return bDisplayTime - aDisplayTime;
  });
}

export function sortArticles(articles: Article[], now = siteNow()) {
  return sortArticlesForFeed(articles, now);
}

export function visibleArticles(articles: Article[], now = siteNow()) {
  return sortArticles(articles.filter((article) => isPublished(article, now)), now);
}

export function activeArticles(articles: Article[], now = siteNow()) {
  return sortArticles(articles.filter((article) => isActiveArticle(article, now)), now);
}

export function featuredArticle(articles: Article[], now = siteNow()) {
  const active = activeArticles(articles, now);
  return active.find((article) => article.data.featured) ?? active[0];
}

export function latestArticles(articles: Article[], count = 6, now = siteNow()) {
  return activeArticles(articles, now).slice(0, count);
}

export function tickerArticles(articles: Article[], now = siteNow()) {
  const visible = activeArticles(articles, now);
  const manual = visible
    .filter((article) => article.data.ticker)
    .sort((a, b) => (a.data.tickerRank ?? 999) - (b.data.tickerRank ?? 999))
    .slice(0, 5);

  if (manual.length === 5) return manual;

  const fallback = visible.filter((article) => !manual.includes(article));
  return [...manual, ...fallback].slice(0, 5);
}

export function categoryMap(articles: Article[], now = siteNow()) {
  const map = new Map<string, Article[]>();
  for (const article of activeArticles(articles, now)) {
    const bucket = map.get(article.data.category) ?? [];
    bucket.push(article);
    map.set(article.data.category, bucket);
  }
  return map;
}

export function tagCounts(articles: Article[], now = siteNow()) {
  const counts = new Map<string, number>();
  for (const article of activeArticles(articles, now)) {
    for (const tag of article.data.tags) {
      counts.set(tag, (counts.get(tag) ?? 0) + 1);
    }
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]);
}


export function slugifyLabel(value: string) {
  return value.toLowerCase().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

export function articlePath(articleOrSlug: Article | string) {
  const slug = typeof articleOrSlug === 'string' ? articleOrSlug : articleOrSlug.slug;
  return `/${slug}/`;
}
