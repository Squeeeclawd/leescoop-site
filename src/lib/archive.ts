import { isPublished, leeCountyDateKey, siteNow, type Article } from './content';

export type ArchiveView = 'all' | 'events' | 'news';
export const archivePageSize = 18;

export function archiveDate(article: Article) {
  return article.data.contentKind === 'event' ? article.data.eventDate : article.data.date;
}

export function archiveMonthName(key: string) {
  if (key === 'undated') return 'Date to be announced';
  return new Intl.DateTimeFormat('en-US', { month: 'long', year: 'numeric', timeZone: 'UTC' })
    .format(new Date(key + '-01T12:00:00Z'));
}

export function groupArchive(articles: Article[], now = siteNow()) {
  const buckets = new Map<string, Article[]>();
  for (const article of articles.filter(item => isPublished(item, now))) {
    const date = archiveDate(article);
    const key = date ? leeCountyDateKey(date).slice(0, 7) : 'undated';
    const items = buckets.get(key) ?? [];
    items.push(article);
    buckets.set(key, items);
  }
  const keys = [...buckets.keys()].filter(key => key !== 'undated').sort().reverse();
  if (buckets.has('undated')) keys.push('undated');
  return keys.map(key => {
    const articles = buckets.get(key)!;
    const events = articles.filter(item => item.data.contentKind === 'event').length;
    return { key, label: archiveMonthName(key), articles, events, news: articles.length - events };
  });
}

export function archivePath(month: string, view: ArchiveView = 'all', page = 1) {
  return '/archive/' + month + '/' + (view === 'all' ? '' : view + '/') + (page > 1 ? 'page/' + page + '/' : '');
}

export function archiveResults(articles: Article[], view: ArchiveView) {
  const filtered = articles.filter(item => view === 'all' || item.data.contentKind === (view === 'events' ? 'event' : 'news'));
  return filtered.sort((a, b) => {
    const delta = (archiveDate(a)?.getTime() ?? 0) - (archiveDate(b)?.getTime() ?? 0);
    return (view === 'events' ? delta : -delta) || a.slug.localeCompare(b.slug);
  });
}
