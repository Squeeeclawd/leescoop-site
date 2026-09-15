import { LEE_COUNTY_TIME_ZONE } from './content';

type HomepageDateArticle = {
  data: {
    contentKind?: string;
    date?: Date;
    eventDate?: Date;
  };
};

export type HomepageDateBadgeParts = {
  top: string;
  bottom: string;
};

export function formatHomepageDate(value?: Date) {
  if (!value) return 'Date TBA';
  return value.toLocaleDateString('en-US', { timeZone: LEE_COUNTY_TIME_ZONE, month: 'short', day: 'numeric' });
}

export function formatHomepageLongDate(value?: Date) {
  if (!value) return 'Date TBA';
  return value.toLocaleDateString('en-US', { timeZone: LEE_COUNTY_TIME_ZONE, weekday: 'short', month: 'short', day: 'numeric' });
}

export function homepageDateKey(value?: Date) {
  if (!value) return '';
  return new Intl.DateTimeFormat('en-CA', { timeZone: LEE_COUNTY_TIME_ZONE, year: 'numeric', month: '2-digit', day: '2-digit' }).format(value);
}

function formatRangeEndpoint(value: Date, includeYear = false) {
  return value.toLocaleDateString('en-US', {
    timeZone: LEE_COUNTY_TIME_ZONE,
    month: 'short',
    day: 'numeric',
    ...(includeYear ? { year: 'numeric' as const } : {})
  });
}

export function formatHomepageEventRange(start?: Date, end?: Date) {
  if (!start) return 'Date TBA';
  if (!end || homepageDateKey(start) === homepageDateKey(end)) return formatHomepageLongDate(start);

  const startYear = start.toLocaleDateString('en-US', { timeZone: LEE_COUNTY_TIME_ZONE, year: 'numeric' });
  const endYear = end.toLocaleDateString('en-US', { timeZone: LEE_COUNTY_TIME_ZONE, year: 'numeric' });
  const includeStartYear = startYear !== endYear;
  return `${formatRangeEndpoint(start, includeStartYear)}–${formatRangeEndpoint(end, true)}`;
}

export function homepageDisplayDate(article: HomepageDateArticle) {
  return article.data.contentKind === 'event' ? article.data.eventDate : article.data.date;
}

export function hasHomepageMultiDayEventRange(article: HomepageDateArticle, eventEnd?: Date) {
  if (article.data.contentKind !== 'event' || !article.data.eventDate) return false;
  return Boolean(eventEnd && homepageDateKey(article.data.eventDate) !== homepageDateKey(eventEnd));
}

export function homepageTimelineDateLabel(article: HomepageDateArticle, eventEnd?: Date) {
  if (article.data.contentKind === 'news') return 'Posted';
  return hasHomepageMultiDayEventRange(article, eventEnd) ? 'Runs' : 'Happens';
}

export function homepageTimelineDateText(article: HomepageDateArticle, eventEnd?: Date) {
  if (article.data.contentKind === 'news') return formatHomepageLongDate(article.data.date);
  if (!hasHomepageMultiDayEventRange(article, eventEnd)) return formatHomepageLongDate(article.data.eventDate);
  return formatHomepageEventRange(article.data.eventDate, eventEnd);
}

export function homepageBadgeParts(article: HomepageDateArticle, eventEnd?: Date): HomepageDateBadgeParts {
  const start = homepageDisplayDate(article);
  if (article.data.contentKind !== 'event' || !hasHomepageMultiDayEventRange(article, eventEnd)) {
    const parts = formatHomepageDate(start).split(' ');
    return { top: parts[0] ?? '', bottom: parts[1] ?? '' };
  }

  const startMonth = start?.toLocaleDateString('en-US', { timeZone: LEE_COUNTY_TIME_ZONE, month: 'short' }) ?? '';
  const endMonth = eventEnd?.toLocaleDateString('en-US', { timeZone: LEE_COUNTY_TIME_ZONE, month: 'short' }) ?? '';
  const startDay = start?.toLocaleDateString('en-US', { timeZone: LEE_COUNTY_TIME_ZONE, day: 'numeric' }) ?? '';
  const endDay = eventEnd?.toLocaleDateString('en-US', { timeZone: LEE_COUNTY_TIME_ZONE, day: 'numeric' }) ?? '';
  return {
    top: startMonth === endMonth ? startMonth : `${startMonth}–${endMonth}`,
    bottom: `${startDay}–${endDay}`
  };
}
