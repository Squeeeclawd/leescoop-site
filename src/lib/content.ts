import type { CollectionEntry } from 'astro:content';

export type Article = CollectionEntry<'articles'>;

export function isPublished(article: Article) {
  const now = new Date();
  return !article.data.draft && article.data.date <= now;
}

export function sortArticles(articles: Article[]) {
  return [...articles].sort((a, b) => {
    const pinnedDelta = Number(b.data.pinned) - Number(a.data.pinned);
    if (pinnedDelta !== 0) return pinnedDelta;
    return b.data.date.getTime() - a.data.date.getTime();
  });
}

export function visibleArticles(articles: Article[]) {
  return sortArticles(articles.filter(isPublished));
}

export function featuredArticle(articles: Article[]) {
  return visibleArticles(articles).find((article) => article.data.featured) ?? visibleArticles(articles)[0];
}

export function latestArticles(articles: Article[], count = 6) {
  return visibleArticles(articles).slice(0, count);
}

export function tickerArticles(articles: Article[]) {
  const visible = visibleArticles(articles);
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
  for (const article of visibleArticles(articles)) {
    const bucket = map.get(article.data.category) ?? [];
    bucket.push(article);
    map.set(article.data.category, bucket);
  }
  return map;
}

export function tagCounts(articles: Article[]) {
  const counts = new Map<string, number>();
  for (const article of visibleArticles(articles)) {
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
