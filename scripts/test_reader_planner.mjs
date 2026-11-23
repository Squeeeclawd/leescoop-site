import assert from 'node:assert/strict';
import { groupSavedPlans, makePlannerEntry } from '../src/lib/planner.ts';
import { openSavedPlans, SAVED_PLANS_KEY } from '../src/lib/savedPlans.ts';

const now = new Date('2026-11-23T18:00:00-05:00');
const event = (slug, start, end) => makePlannerEntry({
  slug, data: {title: slug, contentKind: 'event', eventDate: start ? new Date(start) : undefined,
    eventEndDate: end ? new Date(end) : undefined, city: 'Fort Myers'}
}, now);
const entries = [
  event('later', '2026-12-18T10:00:00-05:00'),
  event('ended', '2026-11-22T20:00:00-05:00'),
  event('ongoing', '2026-11-21T15:00:00-05:00', '2026-11-24T13:00:00-05:00'),
  event('date-tba'),
  makePlannerEntry({slug:'news', data:{title:'News', contentKind:'news', date:now}}, now)
];
const saved = entries.map(entry => entry.slug);
const groups = groupSavedPlans(entries, [...saved, 'no-longer-published'], now);
assert.deepEqual(groups.upcoming.map(entry => entry.slug), ['ongoing', 'later', 'date-tba']);
assert.deepEqual(groups.reading.map(entry => entry.slug), ['news']);
assert.deepEqual(groups.past.map(entry => entry.slug), ['ended']);
assert.equal(entries[2].calendarHref, '/calendar/ongoing.ics');
assert.equal(entries[1].calendarHref, null);
assert.equal(entries[3].calendarHref, null);
assert.equal(entries[4].calendarHref, null);
const cutoff = new Date(entries[2].endsAt);
assert.equal(groupSavedPlans(entries, ['ongoing'], cutoff).upcoming.length, 1);
assert.equal(groupSavedPlans(entries, ['ongoing'], new Date(cutoff.getTime() + 1)).past.length, 1);

let storage = '["legacy",null,"legacy"]';
let writeDenied = false;
let notifications = 0;
globalThis.window = new EventTarget();
window.addEventListener('leescoop:saves-changed', () => notifications++);
Object.defineProperty(globalThis, 'localStorage', {value:{
  getItem(key) { assert.equal(key, SAVED_PLANS_KEY); return storage; },
  setItem(key, value) {
    assert.equal(key, SAVED_PLANS_KEY);
    if (writeDenied) throw Error('quota full');
    storage = value;
  }
}});
const warnings = [];
const list = openSavedPlans(message => warnings.push(message));
assert.deepEqual(list.slugs(), ['legacy']);
// Re-read another tab's persisted change before toggling.
storage = '["legacy","another-tab"]';
assert.equal(list.toggle('legacy'), false);
assert.deepEqual(JSON.parse(storage), ['another-tab']);
writeDenied = true;
assert.equal(list.toggle('local-only'), true);
list.sync();
assert.equal(list.has('local-only'), true);
assert.match(warnings.at(-1), /page only/);
storage = '["another-tab","added-in-another-tab"]';
writeDenied = false;
list.toggle('another');
assert.deepEqual(JSON.parse(storage), ['another-tab','added-in-another-tab','local-only','another']);
storage = '["added-in-another-tab","local-only","another"]';
list.remove('another-tab'); // A stale Remove button must never restore the slug.
assert.equal(list.has('another-tab'), false);
assert.equal(notifications, 4);
assert.equal(list.persistent, true);
storage = '{';
list.sync();
assert.equal(list.persistent, false);
assert.equal(list.has('another'), true);
console.log('PASS: shared bookmarks, cross-tab reads, memory fallback, grouped itinerary, local event cutoff and reminder eligibility');
