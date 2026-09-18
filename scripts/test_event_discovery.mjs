// Executes the actual homepage inline script with a deterministic DOM and clock.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source = fs.readFileSync('src/pages/index.astro', 'utf8');
const script = source.match(/<script is:inline>([\s\S]*?)<\/script>/)[1];
class Element {
  constructor(attrs = {}) { this.attrs = attrs; this.hidden = false; this.disabled = false; this.value = ''; this.listeners = {}; this.classList = {toggle() {}}; this.count = {textContent: ''}; }
  getAttribute(key) { return this.attrs[key] ?? null; }
  setAttribute(key, value) { this.attrs[key] = value; }
  querySelector() { return this.count; }
  addEventListener(key, fn) { this.listeners[key] = fn; }
  closest(selector) { return selector.startsWith('[') && selector.slice(1,-1) in this.attrs ? this : selector === '#filter-clear-all' && this.attrs.id === 'filter-clear-all' ? this : null; }
  focus() {}
}
let now = '2026-09-10T20:00:00Z';
class Clock extends Date { constructor(...args) { super(...(args.length ? args : [now])); } static now() { return new Date(now).getTime(); } }
const tile = (start, end, cutoff, kind = 'event') => new Element({'data-kind': kind, 'data-date-key': start, 'data-end-date-key': end, 'data-active-until': cutoff, 'data-category': 'Fort Myers', 'data-search': 'music'});
const tiles = [
 tile('2026-09-10','2026-09-10','2026-09-11T03:59:59Z'),
 tile('2026-09-09','2026-09-10','2026-09-10T21:00:00Z'),
 tile('2026-09-12','2026-09-13','2026-09-14T03:59:59Z'),
 tile('2026-09-23','2026-09-23','2026-09-24T03:59:59Z'),
 tile('2026-09-24','2026-09-24','2026-09-25T03:59:59Z'),
 tile('2026-09-10','2026-09-10','2026-09-10T19:00:00Z'),
 tile('2026-09-10','','','news')
];
const dates = ['today','weekend','next14'].map(x => new Element({'data-filter-date-window':x}));
const kinds = ['event','news'].map(x => new Element({'data-filter-kind':x}));
const ids = Object.fromEntries(['home-filter-input','filter-search-form','filter-clear-all','home-empty-state'].map(x => [x,new Element({id:x})]));
const handlers = {};
let refresh;
const document = {hidden:false, dispatchEvent() {}, querySelectorAll(s) { return ({'.home-tile':tiles,'[data-filter-date-window]':dates,'[data-filter-kind]':kinds})[s] ?? []; }, querySelector() {return null;}, getElementById(s) {return ids[s];}, addEventListener(k,f) {handlers[k]=f;} };
vm.runInNewContext(script, {Event: class {}, document,window:{setInterval(f){refresh=f;}},Date:Clock,Intl,HTMLElement:Element,HTMLInputElement:Element,HTMLFormElement:Element,HTMLButtonElement:Element});
const click = e => handlers.click({target:e,preventDefault(){}});
const shown = () => tiles.flatMap((t,i)=>t.hidden?[]:[i]);
assert.deepEqual(shown(),[0,1,2,3,4]);
assert.deepEqual(dates.map(x=>x.count.textContent),['2','1','4']);
assert.equal(ids['filter-clear-all'].hidden,true);
click(dates[0]); assert.deepEqual(shown(),[0,1]);
click(dates[1]); assert.deepEqual(shown(),[2]);
click(dates[2]); assert.deepEqual(shown(),[0,1,2,3]);
click(kinds[1]); assert.deepEqual(shown(),[6]); assert.equal(dates[2].attrs['aria-pressed'],'false');
click(dates[0]); assert.deepEqual(shown(),[0,1]);
now='2026-09-10T21:00:00.001Z'; refresh(); assert.deepEqual(shown(),[0]);
ids['home-filter-input'].value='nothing'; ids['home-filter-input'].listeners.input(); assert.deepEqual(shown(),[]); assert.equal(ids['home-empty-state'].hidden,false);
click(ids['filter-clear-all']); assert.deepEqual(shown(),[0,2,3,4]);
now='2026-09-13T16:00:00Z'; click(dates[1]); assert.deepEqual(shown(),[2]);
now='2026-09-14T04:00:00Z'; refresh(); assert.deepEqual(shown(),[]);
const css = fs.readFileSync('src/styles/global.css','utf8');
for (const selector of ['.home-tile[hidden]','[data-expirable-feature][hidden]','[data-filter-category][hidden]','#filter-clear-all[hidden]','#home-empty-state[hidden]']) assert.ok(css.includes(selector));
console.log('PASS: actual inline-script filtering, counts, news switch, expiry refresh, Sunday, midnight, search/reset and hidden CSS');
const helpers = script.slice(script.indexOf('      const leeCountyDateKey ='), script.indexOf('      const isPastActiveWindow ='));
const range = (clock, key) => vm.runInNewContext(`${helpers}\nfilterNow = new Date('${clock}'); JSON.stringify(dateWindowRange('${key}'));`, {Date,Intl});
assert.equal(range('2026-09-11T02:00:00Z','today'), JSON.stringify({start:'2026-09-10',end:'2026-09-10'}));
assert.equal(range('2026-09-13T16:00:00Z','weekend'), JSON.stringify({start:'2026-09-12',end:'2026-09-13'}));
assert.equal(range('2026-09-14T04:00:00Z','weekend'), JSON.stringify({start:'2026-09-19',end:'2026-09-20'}));
assert.equal(range('2026-03-07T17:00:00Z','next14'), JSON.stringify({start:'2026-03-07',end:'2026-03-20'}));
assert.equal(range('2026-10-31T16:00:00Z','next14'), JSON.stringify({start:'2026-10-31',end:'2026-11-13'}));
assert.equal(range('2026-12-31T17:00:00Z','next14'), JSON.stringify({start:'2026-12-31',end:'2027-01-13'}));
console.log('PASS: 6 civil window boundary assertions including DST and year rollover');
