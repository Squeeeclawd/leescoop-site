import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';

const source = fs.readFileSync(new URL('../src/lib/homepageDateLabels.ts', import.meta.url), 'utf8');
const js = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext } }).outputText
  .replace("import { LEE_COUNTY_TIME_ZONE } from './content';", "const LEE_COUNTY_TIME_ZONE = 'America/New_York';");
const lib = await import(`data:text/javascript;base64,${Buffer.from(js).toString('base64')}`);

const event = (start, end) => ({
  data: {
    contentKind: 'event',
    eventDate: new Date(start)
  },
  end: end ? new Date(end) : undefined
});
const news = (date) => ({ data: { contentKind: 'news', date: new Date(date) } });

const sizzle = event('2026-09-01T11:00:00-04:00', '2026-09-30T23:00:00-04:00');
assert.equal(lib.homepageTimelineDateLabel(sizzle, sizzle.end), 'Runs');
assert.equal(lib.homepageTimelineDateText(sizzle, sizzle.end), 'Sep 1–Sep 30, 2026');
assert.deepEqual(lib.homepageBadgeParts(sizzle, sizzle.end), { top: 'Sep', bottom: '1–30' });
assert.notEqual(`${lib.homepageTimelineDateLabel(sizzle, sizzle.end)} ${lib.homepageTimelineDateText(sizzle, sizzle.end)}`, 'Happens Tue, Sep 1');

const singleDay = event('2026-09-15T19:30:00-04:00', '2026-09-15T21:30:00-04:00');
assert.equal(lib.homepageTimelineDateLabel(singleDay, singleDay.end), 'Happens');
assert.equal(lib.homepageTimelineDateText(singleDay, singleDay.end), 'Tue, Sep 15');
assert.deepEqual(lib.homepageBadgeParts(singleDay, singleDay.end), { top: 'Sep', bottom: '15' });

const crossMonth = event('2026-09-30T20:00:00-04:00', '2026-10-02T21:00:00-04:00');
assert.equal(lib.homepageTimelineDateText(crossMonth, crossMonth.end), 'Sep 30–Oct 2, 2026');
assert.deepEqual(lib.homepageBadgeParts(crossMonth, crossMonth.end), { top: 'Sep–Oct', bottom: '30–2' });

const crossYear = event('2026-12-31T20:00:00-05:00', '2027-01-02T21:00:00-05:00');
assert.equal(lib.homepageTimelineDateText(crossYear, crossYear.end), 'Dec 31, 2026–Jan 2, 2027');
assert.deepEqual(lib.homepageBadgeParts(crossYear, crossYear.end), { top: 'Dec–Jan', bottom: '31–2' });

assert.equal(lib.homepageTimelineDateLabel(news('2026-09-15T13:00:00-04:00')), 'Posted');
assert.equal(lib.homepageTimelineDateText(news('2026-09-15T13:00:00-04:00')), 'Tue, Sep 15');
assert.equal(lib.homepageDateKey(new Date('2026-09-15T03:30:00Z')), '2026-09-14');
assert.equal(lib.homepageDateKey(new Date('2026-09-15T04:30:00Z')), '2026-09-15');

console.log(`PASS: homepage date labels for ongoing, single-day, month/year ranges, news and Lee County midnight boundaries (host TZ=${process.env.TZ || 'default'})`);
