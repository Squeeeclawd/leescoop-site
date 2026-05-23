import type { CollectionEntry } from 'astro:content';

export type Article = CollectionEntry<'articles'>;

export function isPublished(article: Article) {
  const now = new Date();
  return !article.data.draft && article.data.date <= now;
}

export function articleDisplayDate(article: Article) {
  return article.data.contentKind === 'event' ? article.data.eventDate ?? article.data.date : article.data.date;
}

function endOfLocalDay(value: Date) {
  const end = new Date(value);
  end.setHours(23, 59, 59, 999);
  return end;
}

function clockTo24Hour(hour: number, period: string) {
  const normalized = hour % 12;
  return period.toLowerCase() === 'pm' ? normalized + 12 : normalized;
}

function cutoffFromEventTime(eventDate: Date, eventTime?: string) {
  if (!eventTime) return undefined;

  const clocks = [...eventTime.matchAll(/(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)\b/gi)];
  if (clocks.length === 0) return undefined;

  const lastClock = clocks[clocks.length - 1];
  const hour = Number(lastClock[1]);
  const minute = Number(lastClock[2] ?? 0);
  const period = lastClock[3].replace(/\./g, '');
  const cutoff = new Date(eventDate);
  cutoff.setHours(clockTo24Hour(hour, period), minute, 0, 0);

  // A single listed time is usually the start time. Keep the event live during the likely event window,
  // but remove it from active feeds once that window has passed.
  if (clocks.length === 1) cutoff.setHours(cutoff.getHours() + 4);

  return cutoff;
}

export function eventArchiveCutoff(article: Article) {
  if (article.data.contentKind !== 'event') return undefined;

  if (article.data.eventEndDate) return endOfLocalDay(article.data.eventEndDate);
  if (!article.data.eventDate) return undefined;

  return cutoffFromEventTime(article.data.eventDate, article.data.eventTime) ?? endOfLocalDay(article.data.eventDate);
}

export function isArchivedEvent(article: Article) {
  const eventCutoff = eventArchiveCutoff(article);
  if (!eventCutoff) return false;
  return eventCutoff.getTime() < Date.now();
}

export function isActiveArticle(article: Article) {
  return isPublished(article) && !isArchivedEvent(article);
}

export function sortArticlesForFeed(articles: Article[]) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayTime = today.getTime();

  return [...articles].sort((a, b) => {
    const pinnedDelta = Number(b.data.pinned) - Number(a.data.pinned);
    if (pinnedDelta !== 0) return pinnedDelta;

    const aDisplayDate = articleDisplayDate(a);
    const bDisplayDate = articleDisplayDate(b);
    const aDisplayTime = aDisplayDate?.getTime() ?? Number.MAX_SAFE_INTEGER;
    const bDisplayTime = bDisplayDate?.getTime() ?? Number.MAX_SAFE_INTEGER;
    const aCurrentOrFuture = aDisplayTime >= todayTime;
    const bCurrentOrFuture = bDisplayTime >= todayTime;

    // One live timeline: current/future news + events first, chronological by display date.
    // News uses publish date; events use event date. Older news remains visible, but falls below current items.
    if (aCurrentOrFuture !== bCurrentOrFuture) return aCurrentOrFuture ? -1 : 1;
    if (aCurrentOrFuture && bCurrentOrFuture) return aDisplayTime - bDisplayTime;

    // Archive-like leftovers: newest news/evergreen items first. Expired events are already filtered elsewhere.
    return bDisplayTime - aDisplayTime;
  });
}

export function sortArticles(articles: Article[]) {
  return sortArticlesForFeed(articles);
}

export function visibleArticles(articles: Article[]) {
  return sortArticles(articles.filter(isPublished));
}

export function activeArticles(articles: Article[]) {
  return sortArticles(articles.filter(isActiveArticle));
}

export function featuredArticle(articles: Article[]) {
  const active = activeArticles(articles);
  return active.find((article) => article.data.featured) ?? active[0];
}

export function latestArticles(articles: Article[], count = 6) {
  return activeArticles(articles).slice(0, count);
}

export function tickerArticles(articles: Article[]) {
  const visible = activeArticles(articles);
  const manual = visible
    .filter((article) => article.data.ticker)
    .sort((a, b) => (a.data.tickerRank ?? 999) - (b.data.tickerRank ?? 999))
    .slice(0, 5);

  if (manual.length === 5) return manual;

  const fallback = visible.filter((article) => !manual.includes(article));
  return [...manual, ...fallback].slice(0, 5);
}

export function categoryMap(articles: Article[]) {
  const map = new Map<string, Article[]>();
  for (const article of activeArticles(articles)) {
    const bucket = map.get(article.data.category) ?? [];
    bucket.push(article);
    map.set(article.data.category, bucket);
  }
  return map;
}

export function tagCounts(articles: Article[]) {
  const counts = new Map<string, number>();
  for (const article of activeArticles(articles)) {
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
