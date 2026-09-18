import { getCollection } from 'astro:content';
import type { APIRoute } from 'astro';
import { activeArticles, eventArchiveCutoff, leeCountyDateKey, siteNow } from '@/lib/content';
import { calendarReminder } from '@/lib/calendar';
export async function getStaticPaths() {
  return activeArticles(await getCollection('articles')).filter(a => a.data.contentKind === 'event' && a.data.eventDate).map(article => ({params: {slug: article.slug}, props: {article}}));
}
export const GET: APIRoute = ({props}) => {
  const article = props.article;
  const data = article.data;
  const reminder = calendarReminder(article.slug, data.title, leeCountyDateKey(data.eventDate), leeCountyDateKey(eventArchiveCutoff(article) ?? data.eventDate), data.venue ?? data.location ?? data.city ?? '', data.sourceUrl ?? `https://leescoop.com/${article.slug}/`, siteNow());
  if (!reminder) return new Response('Calendar reminder unavailable.', {status: 404});
  return new Response(reminder, {headers: {'Content-Type': 'text/calendar; charset=utf-8', 'Content-Disposition': `attachment; filename="leescoop-${article.slug}.ics"`}});
};
