// Executes the homepage inline script against the Sept. 15 Today screenshot case:
// one valid ongoing range, one already-expired start date, one future event, and one news item.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync('src/pages/index.astro', 'utf8');
const script = source.match(/<script is:inline>([\s\S]*?)<\/script>/)[1];

class Element {
  constructor(attrs = {}) {
    this.attrs = attrs;
    this.hidden = false;
    this.disabled = false;
    this.value = '';
    this.listeners = {};
    this.classList = {toggle() {}};
    this.count = {textContent: ''};
  }
  getAttribute(key) { return this.attrs[key] ?? null; }
  setAttribute(key, value) { this.attrs[key] = value; }
  querySelector() { return this.count; }
  addEventListener(key, fn) { this.listeners[key] = fn; }
  closest(selector) {
    if (selector.startsWith('[')) return selector.slice(1, -1) in this.attrs ? this : null;
    if (selector === '#filter-clear-all' && this.attrs.id === 'filter-clear-all') return this;
    return null;
  }
  focus() {}
}

let now = '2026-09-15T13:00:00Z';
class Clock extends Date {
  constructor(...args) { super(...(args.length ? args : [now])); }
  static now() { return new Date(now).getTime(); }
}

const tile = (title, start, end, cutoff, kind = 'event') => new Element({
  'data-kind': kind,
  'data-date-key': start,
  'data-end-date-key': end,
  'data-active-until': cutoff,
  'data-category': 'Fort Myers',
  'data-search': title
});

const tiles = [
  tile('sizzle ongoing dining range', '2026-09-01', '2026-09-30', '2026-10-01T03:00:00Z'),
  tile('expired old event', '2026-09-01', '2026-09-01', '2026-09-02T03:59:59Z'),
  tile('future tomorrow event', '2026-09-16', '2026-09-16', '2026-09-17T03:59:59Z'),
  tile('today news story', '2026-09-15', '', '', 'news')
];
const dates = ['today','weekend','next14'].map(x => new Element({'data-filter-date-window':x}));
const kinds = ['event','news'].map(x => new Element({'data-filter-kind':x}));
const ids = Object.fromEntries(['home-filter-input','filter-search-form','filter-clear-all','home-empty-state'].map(x => [x,new Element({id:x})]));
const handlers = {};
const document = {
  hidden: false,
  querySelectorAll(selector) { return ({'.home-tile': tiles, '[data-filter-date-window]': dates, '[data-filter-kind]': kinds})[selector] ?? []; },
  querySelector() { return null; },
  getElementById(id) { return ids[id]; },
  addEventListener(key, fn) { handlers[key] = fn; }
};
vm.runInNewContext(script, {document, window: {setInterval() {}}, Date: Clock, Intl, HTMLElement: Element, HTMLInputElement: Element, HTMLFormElement: Element, HTMLButtonElement: Element});

const click = element => handlers.click({target: element, preventDefault() {}});
const shown = () => tiles.flatMap((tile, index) => tile.hidden ? [] : [index]);

assert.deepEqual(shown(), [0, 2, 3], 'runtime expiry hides expired event but keeps ongoing, future and news before filters');
assert.deepEqual(dates.map(x => x.count.textContent), ['1', '1', '2'], 'Today counts ongoing only; weekend counts the still-running range; next14 counts ongoing plus future event');

click(dates[0]);
assert.deepEqual(shown(), [0], 'Today event filter keeps the ongoing Sep 1–30 run only');

click(dates[2]);
assert.deepEqual(shown(), [0, 2], 'Next 14 days includes ongoing plus future, not expired');

click(kinds[1]);
assert.deepEqual(shown(), [3], 'Local News filter clears date-window event state and shows news only');

now = '2026-09-15T03:30:00Z';
click(kinds[0]);
click(dates[0]);
assert.deepEqual(shown(), [0], 'Lee County pre-midnight host instant still treats Sep 14/15 overlap consistently for ongoing ranges');

now = '2026-10-01T03:00:00.001Z';
click(dates[0]);
assert.deepEqual(shown(), [], 'ongoing range expires immediately after explicit cutoff');

console.log(`PASS: Sept. 15 Today filter regression for ongoing vs expired vs future, news switching, Lee County midnight and exact cutoff (host TZ=${process.env.TZ || 'default'})`);
