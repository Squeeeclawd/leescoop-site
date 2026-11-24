// LeeScoop homepage discovery UI regression: event-first filtering plus saved/share/calendar affordances.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import { discoveryTestWindow } from './discovery_test_window.mjs';
import { calendarReminder } from '../src/lib/calendar.ts';
import ts from 'typescript';

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
const area = new Element({'data-filter-category':'Cape Coral','data-filter-pill':'Cape Coral'});
const chips = ['category','query'].map(key => new Element({'data-clear-refinement':key}));
const handlers = {};
const document = {hidden:false, dispatchEvent() {}, querySelectorAll(sel) { return ({'.home-tile':tiles,'[data-filter-date-window]':dates,'[data-filter-kind]':kinds,'[data-filter-pill]':[area],'[data-clear-refinement]':chips})[sel] ?? []; }, querySelector(){ return null; }, getElementById(id){ return ids[id]; }, addEventListener(k,f){ handlers[k]=f; }};
const filterWindow = discoveryTestWindow(handlers);
vm.runInNewContext(script, {Event: class {}, document, window: filterWindow, URL, Date: Clock, Intl, HTMLElement: Element, HTMLInputElement: Element, HTMLFormElement: Element, HTMLButtonElement: Element});
const shown = () => tiles.flatMap((t,i)=>t.hidden?[]:[i]);
const click = el => handlers.click({target: el, preventDefault(){}});
assert.deepEqual(shown(), [0,1], 'homepage opens events-first, not a mixed Yahoo-style portal');
assert.equal(ids['feed-result'].textContent, '2 events · Lee County time');
click(kinds[1]); assert.deepEqual(shown(), [2], 'news tab shows brief source-linked local updates separately');
click(dates[0]); assert.deepEqual(shown(), [0], 'date chip returns to event discovery and Today');
ids['home-filter-input'].value = 'market'; ids['home-filter-input'].listeners.input(); assert.deepEqual(shown(), [], 'search combines with current Today filter naturally');
click(ids['filter-clear-all']); assert.deepEqual(shown(), [0,1], 'reset returns to event-first discovery');
filterWindow.location.href = 'https://leescoop.com/?when=weekend&q=market&ref=newsletter#browse';
handlers.popstate();
assert.deepEqual(shown(), [1], 'a shared weekend search restores the matching listing');
assert.equal(ids['home-filter-input'].value, 'market');
click(ids['filter-clear-all']);
assert.equal(filterWindow.location.href, 'https://leescoop.com/?ref=newsletter#browse', 'reset removes only owned parameters');
filterWindow.location.href = 'https://leescoop.com/?area=Cape+Coral&q=market&when=weekend';
handlers.popstate();
assert.equal(chips[0].attrs['aria-label'], 'Remove area filter: Cape Coral');
assert.equal(chips[1].count.textContent, '“market”');
click(chips[0]);
assert.ok(chips[0].hidden && !chips[1].hidden && chips[1].focused);
assert.equal(filterWindow.location.href, 'https://leescoop.com/?q=market&when=weekend');
click(chips[1]);
assert.equal(ids['home-filter-input'].value, '');
assert.deepEqual(shown(), [1], 'removing refinements preserves the weekend filter');
filterWindow.history.replaceState = () => { throw new Error('History API unavailable'); };
click(ids['filter-clear-all']);
assert.deepEqual(shown(), [0,1], 'restricted history permissions do not prevent filtering');
const indexMarkup = source;
const actionsMarkup = fs.readFileSync('src/lib/discoveryActions.ts','utf8');
for (const required of ['id="saved-filter"','data-save={article.slug}','data-share={articlePath(article)}','/calendar/${article.slug}.ics']) assert.ok(indexMarkup.includes(required), `missing ${required}`);
for (const required of ['openSavedPlans','navigator.share','navigator.clipboard']) assert.ok(actionsMarkup.includes(required), `missing ${required}`);
assert.ok(indexMarkup.includes("parsed.protocol === 'https:' || parsed.protocol === 'http:'"), 'external news destinations must reject unsafe URL schemes');
assert.ok(fs.readFileSync('src/styles/discovery.css','utf8').includes('prefers-reduced-motion'));

class ActionNode {
  constructor(dataset = {}) { this.dataset = dataset; this.attrs = {}; this.textContent = ''; this.hidden = false; this.listeners = {}; this.classList = {toggle: (name, active) => { this[name] = active; }}; }
  getAttribute(name) { return this.attrs[name] ?? null; }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  addEventListener(name, handler) { this.listeners[name] = handler; }
  closest(selector) { return selector === '[data-save]' && this.dataset.save ? this : selector === '[data-share]' && this.dataset.share ? this : null; }
  append() {}
}
const actionButtons = [new ActionNode({save: 'one'}), new ActionNode({save: 'two'})];
const actionCards = [new ActionNode({slug: 'one'}), new ActionNode({slug: 'two'})];
const actionStatus = new ActionNode();
const savedFilter = new ActionNode();
const savedEmpty = new ActionNode();
const savedResult = new ActionNode();
savedResult.textContent = '1 events · Lee County time';
savedResult.setAttribute('data-base-text', savedResult.textContent);
const actionHandlers = {};
const storageHandlers = {};
let stored = JSON.stringify(['one', 42]);
const actionDocument = {
  querySelectorAll(selector) { return selector === '[data-save]' ? actionButtons : selector === '.discovery-card' ? actionCards : []; },
  getElementById(id) { return ({'action-status': actionStatus, 'saved-filter': savedFilter, 'saved-empty': savedEmpty, 'feed-result': savedResult})[id] ?? null; },
  addEventListener(name, handler) { actionHandlers[name] = handler; },
  createElement() { return new ActionNode(); }
};
const uiContext = vm.createContext({
  document: actionDocument,
  window: {addEventListener(name, handler) { storageHandlers[name] = handler; }, dispatchEvent() {}},
  localStorage: {getItem() { return stored; }, setItem(_key, value) { stored = value; }},
  navigator: {}, location: {origin: 'https://leescoop.com'}, Element: ActionNode, Event, URL, Set, JSON
});
function loadUiModule(source, imports = {}) {
  const compiled = ts.transpileModule(source, {compilerOptions: {target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS}}).outputText;
  const run = vm.runInContext(`(function (exports, require) { ${compiled} })`, uiContext);
  const exports = {};
  run(exports, name => imports[name]);
  return exports;
}
const savedPlans = loadUiModule(fs.readFileSync('src/lib/savedPlans.ts', 'utf8'));
loadUiModule(actionsMarkup, {'./savedPlans': savedPlans});
assert.equal(actionButtons[0].attrs['aria-pressed'], 'true', 'valid saved slugs restore without login');
assert.equal(actionButtons[1].attrs['aria-pressed'], 'false', 'non-string storage entries are ignored');
await actionHandlers.click({target: actionButtons[1]});
assert.deepEqual(JSON.parse(stored), ['one', 'two'], 'save changes persist locally');
actionCards[1].hidden = true;
savedFilter.listeners.click({currentTarget: savedFilter});
assert.equal(actionCards[0]['not-saved'], false);
assert.equal(actionCards[1]['not-saved'], false);
assert.equal(savedResult.textContent, '1 saved item · this browser', 'Saved count must reflect active filters');
savedFilter.listeners.click({currentTarget: savedFilter});
assert.equal(savedResult.textContent, '1 events · Lee County time', 'leaving Saved restores the active-filter count');
stored = '[]'; storageHandlers.storage({key: 'leescoop:saved:v1'});
savedFilter.listeners.click({currentTarget: savedFilter});
assert.equal(savedEmpty.hidden, false, 'matching cards exist but none are saved');
actionCards[0].hidden = true;
actionHandlers['leescoop:filtered']();
assert.equal(savedEmpty.hidden, true, 'no base matches: use the ordinary empty state only');
stored = '{'; storageHandlers.storage({key: 'leescoop:saved:v1'});
assert.match(actionStatus.textContent, /storage unavailable/i, 'corrupt or unavailable storage fails softly');

const reminder = calendarReminder('sample/event', 'Café, Music; Night\\Fun\rATTENDEE:bad', '2026-09-18', '2026-09-20', 'Hall, A; East\\Wing\nDesk', 'https://example.com/\r\nATTENDEE:bad', new Date('2026-09-18T18:49:00Z'));
assert.ok(reminder, 'valid date ranges must produce a reminder');
assert.ok(reminder.endsWith('\r\n'), 'ICS must end with CRLF');
assert.ok(reminder.includes('DTSTAMP:20260918T184900Z\r\n'));
assert.ok(reminder.includes('DTSTART;VALUE=DATE:20260918\r\nDTEND;VALUE=DATE:20260921\r\n'), 'all-day DTEND must be exclusive');
assert.ok(reminder.includes('SUMMARY:Café\\, Music\\; Night\\\\Fun\\nATTENDEE:bad\r\n'));
assert.ok(reminder.includes('LOCATION:Hall\\, A\\; East\\\\Wing\\nDesk\r\n'));
assert.ok(reminder.includes('URL:https://leescoop.com/sample%2Fevent/\r\n'), 'control-bearing calendar URLs must fall back to LeeScoop');
assert.ok(reminder.includes('UID:sample-event@leescoop.com\r\n'), 'calendar UID must be header-safe');
assert.ok(reminder.split('\r\n').every(line => Buffer.byteLength(line) <= 75), 'folded ICS lines must fit RFC 5545 octet limits');
assert.ok(!/(^|[^\r])\n/.test(reminder), 'ICS must not contain bare LF line endings');
assert.equal(calendarReminder('sample', 'Title', 'not-a-date', '2026-09-20', '', 'https://leescoop.com/', new Date()), undefined);
assert.equal(calendarReminder('sample', 'Title', '2026-09-21', '2026-09-20', '', 'https://leescoop.com/', new Date()), undefined);
assert.equal(calendarReminder('sample', 'Title', '2026-02-30', '2026-03-01', '', 'https://leescoop.com/', new Date()), undefined);
assert.equal(calendarReminder('sample', 'Title', '2026-09-18', '2026-09-20', '', 'https://leescoop.com/', new Date('invalid')), undefined);
console.log('PASS: discovery UI opens events-first, keeps Saved counts aligned, and includes resilient safe RFC-shaped calendar downloads');
