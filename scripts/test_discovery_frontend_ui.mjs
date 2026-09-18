// LeeScoop homepage discovery UI regression: event-first filtering plus saved/share/calendar affordances.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source = fs.readFileSync('src/pages/index.astro', 'utf8');
const script = source.match(/<script is:inline>([\s\S]*?)<\/script>/)[1];
class Element {
  constructor(attrs = {}) { this.attrs = attrs; this.hidden = false; this.disabled = false; this.value = ''; this.listeners = {}; this.classList = {toggle() {}}; this.count = {textContent: ''}; }
  getAttribute(k) { return this.attrs[k] ?? null; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  querySelector() { return this.count; }
  addEventListener(k, fn) { this.listeners[k] = fn; }
  closest(selector) { if (selector.startsWith('[')) return selector.slice(1,-1) in this.attrs ? this : null; if (selector === '#filter-clear-all' && this.attrs.id === 'filter-clear-all') return this; return null; }
  focus() { this.focused = true; }
}
let now = '2026-09-18T16:00:00-04:00';
class Clock extends Date { constructor(...args) { super(...(args.length ? args : [now])); } static now() { return new Date(now).getTime(); } }
const tile = (attrs) => new Element(attrs);
const tiles = [
  tile({'data-kind':'event','data-category':'Fort Myers','data-date-key':'2026-09-18','data-end-date-key':'2026-09-18','data-active-until':'2026-09-19T03:59:59Z','data-search':'music fort myers'}),
  tile({'data-kind':'event','data-category':'Cape Coral','data-date-key':'2026-09-19','data-end-date-key':'2026-09-20','data-active-until':'2026-09-21T03:59:59Z','data-search':'market cape'}),
  tile({'data-kind':'news','data-category':'Fort Myers','data-date-key':'2026-09-18','data-end-date-key':'','data-active-until':'','data-search':'brief source linked'}),
];
const dates = ['today','weekend','next14'].map(x => new Element({'data-filter-date-window':x}));
const kinds = ['event','news'].map(x => new Element({'data-filter-kind':x}));
const ids = Object.fromEntries(['home-filter-input','filter-search-form','filter-clear-all','home-empty-state','feed-result'].map(x => [x,new Element({id:x})]));
const handlers = {};
const document = {hidden:false, dispatchEvent() {}, querySelectorAll(sel) { return ({'.home-tile':tiles,'[data-filter-date-window]':dates,'[data-filter-kind]':kinds,'[data-filter-pill]':[]})[sel] ?? []; }, querySelector(){ return null; }, getElementById(id){ return ids[id]; }, addEventListener(k,f){ handlers[k]=f; }};
vm.runInNewContext(script, {Event: class {}, document, window: {setInterval(){}}, Date: Clock, Intl, HTMLElement: Element, HTMLInputElement: Element, HTMLFormElement: Element, HTMLButtonElement: Element});
const shown = () => tiles.flatMap((t,i)=>t.hidden?[]:[i]);
const click = el => handlers.click({target: el, preventDefault(){}});
assert.deepEqual(shown(), [0,1], 'homepage opens events-first, not a mixed Yahoo-style portal');
assert.equal(ids['feed-result'].textContent, '2 events · Lee County time');
click(kinds[1]); assert.deepEqual(shown(), [2], 'news tab shows brief source-linked local updates separately');
click(dates[0]); assert.deepEqual(shown(), [0], 'date chip returns to event discovery and Today');
ids['home-filter-input'].value = 'market'; ids['home-filter-input'].listeners.input(); assert.deepEqual(shown(), [], 'search combines with current Today filter naturally');
click(ids['filter-clear-all']); assert.deepEqual(shown(), [0,1], 'reset returns to event-first discovery');
const indexMarkup = source;
const actionsMarkup = fs.readFileSync('src/lib/discoveryActions.ts','utf8');
for (const required of ['id="saved-filter"','data-save={article.slug}','data-share={articlePath(article)}','/calendar/${article.slug}.ics']) assert.ok(indexMarkup.includes(required), `missing ${required}`);
for (const required of ['localStorage','navigator.share','navigator.clipboard']) assert.ok(actionsMarkup.includes(required), `missing ${required}`);
assert.ok(fs.readFileSync('src/styles/discovery.css','utf8').includes('prefers-reduced-motion'));
console.log('PASS: discovery UI opens events-first, filters naturally, includes save/share/calendar affordances and reduced-motion CSS');
