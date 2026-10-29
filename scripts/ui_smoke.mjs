#!/usr/bin/env node
/* Headless smoke test for the PlayUI browser layer: a minimal
 * fake DOM good enough to render the setup screen, start a
 * game, and play it to completion with the deck source. This
 * is a smoke test, not a browser: it catches runtime errors
 * and broken wiring in js/play.js's UI half, nothing more.
 * Run: node scripts/ui_smoke.mjs */
import { createRequire } from 'node:module';
import fs from 'node:fs';

class El {
  constructor(tag) {
    this.tagName = String(tag).toUpperCase();
    this.children = [];
    this.attrs = {};
    this._text = '';
    this._listeners = {};
    this.style = {};
    this.disabled = false;
    this.value = '';
    this.selected = false;
    this.scrollTop = 0;
    this.scrollHeight = 0;
    const self = this;
    this.classList = {
      add(c) { const s = new Set(self.className.split(/\s+/).filter(Boolean)); s.add(c); self.className = [...s].join(' '); },
      remove(c) { const s = new Set(self.className.split(/\s+/).filter(Boolean)); s.delete(c); self.className = [...s].join(' '); },
      contains(c) { return self.className.split(/\s+/).includes(c); },
    };
    this.className = '';
  }
  set textContent(v) { this._text = String(v); this.children = []; }
  get textContent() { return this._text + this.children.map((c) => c.textContent).join(''); }
  setAttribute(k, v) { this.attrs[k] = String(v); if (k === 'class') this.className = String(v); if (k === 'value') this.value = String(v); }
  getAttribute(k) { return k === 'class' ? this.className : (this.attrs[k] ?? null); }
  removeAttribute(k) { delete this.attrs[k]; }
  appendChild(c) { this.children.push(c); return c; }
  replaceChildren(...nodes) { this.children = nodes.slice(); this._text = ''; }
  remove() { this._removed = true; }
  addEventListener(ev, fn) { (this._listeners[ev] = this._listeners[ev] || []).push(fn); }
  click() { (this._listeners.click || []).forEach((fn) => fn({})); }
}
const storageMap = new Map();
global.window = {
  localStorage: {
    get length() { return storageMap.size; },
    key(i) { return [...storageMap.keys()][i]; },
    getItem(k) { return storageMap.has(k) ? storageMap.get(k) : null; },
    setItem(k, v) { storageMap.set(k, String(v)); },
    removeItem(k) { storageMap.delete(k); },
  },
};
global.document = {
  createElement: (t) => new El(t),
  createTextNode: (t) => { const n = new El('#text'); n._text = String(t); return n; },
  body: new El('body'),
  querySelectorAll: () => [],
};
Object.defineProperty(globalThis, 'navigator', { value: {}, configurable: true });
global.fetch = async (url) => {
  if (String(url).includes('playable_r106.json')) {
    return { json: async () => JSON.parse(fs.readFileSync(new URL('../data/playable_r106.json', import.meta.url), 'utf8')) };
  }
  throw new Error('unexpected fetch ' + url);
};

const require = createRequire(import.meta.url);
const P = require('../js/play.js');
const PUI = global.window.PlayUI;
if (!PUI) { console.log('UI SMOKE: FAIL — window.PlayUI missing'); process.exit(1); }

function findButtons(root, label) {
  const out = [];
  (function walk(n) {
    if (n.tagName === 'BUTTON' && n.textContent.trim() === label) out.push(n);
    n.children.forEach(walk);
  })(root);
  return out;
}
function findText(root, needle) {
  let found = false;
  (function walk(n) { if (n.textContent.includes(needle)) found = true; n.children.forEach(walk); })(root);
  return found;
}
const tick = () => new Promise((r) => setTimeout(r, 0));

const view = new El('div');
PUI.renderPlay(view);
await tick(); await tick();
let fails = 0;
const check = (label, ok, detail) => { console.log((ok ? 'PASS ' : 'FAIL ') + label + (ok ? '' : ' -- ' + (detail || ''))); if (!ok) fails++; };
check('setup screen renders with the fixture label', findText(view, 'Play the game'));
check('setup carries the declarations line', findText(view, 'Declarations are not part of Phase 1 play'));
// Assign managers by clicking the profile toggles, as a user
// would (the toggles re-render and enable Start).
for (const label of ['Frank Chance (profile)', 'Dick Williams (profile)']) {
  const b = findButtons(view, label);
  if (b.length) b[0].click();
}
const start = findButtons(view, 'Start the game');
check('start button present and enabled', start.length === 1 && !start[0].disabled);
start[0].click();
check('game screen renders the scorebug', findText(view, 'Saved — after PA 0') || findText(view, 'Top 1'));
function findByClass(root, cls) {
  const out = [];
  (function walk(n) {
    if (n.classList && n.classList.contains(cls)) out.push(n);
    n.children.forEach(walk);
  })(root);
  return out;
}
const facControls = () => findByClass(view, 'ctl-fac');
const hasHl = () => findByClass(view, 'hl-flash').length > 0;
// Matchup moment: the strip names the pair on the table, the
// cards present themselves once per new pair, and a settled
// card's plain structure is exactly what it was before the
// flair (the entrance lives in mx-* classes, stripped here).
const strip = () => findByClass(view, 'play-matchup')[0];
const batCardEl = () => findByClass(view, 'play-card-batter')[0];
const pitCardEl = () => findByClass(view, 'play-card-pitcher')[0];
function livePairNames() {
  const dia = findByClass(view, 'play-home')[0];
  const m = dia && /^(.*) batting · (.*) pitching$/.exec(dia.textContent);
  return m ? [m[1], m[2]] : [null, null];
}
function skeleton(node) {
  const cls = node.className.split(/\s+/).filter((c) => c && !c.startsWith('mx-')).sort().join(' ');
  return node.tagName + '|' + cls + '|style:' + Object.keys(node.style).length + '(' + node.children.map(skeleton).join(',') + ')';
}
{
  const [bn, pn] = livePairNames();
  const s = strip();
  const vsEl = s && findByClass(s, 'mx-vs')[0];
  check('matchup strip names the pair on the table', !!s && !!bn && s.textContent.includes(bn) && s.textContent.includes(pn) && !!vsEl && vsEl.textContent === 'vs', s && s.textContent);
  check('matchup strip names both clubs', !!s && s.textContent.includes('Chicago') && s.textContent.includes('Montreal'), s && s.textContent);
  check('new PA: the batter card flips up and the pitcher card slides in',
    !!batCardEl() && batCardEl().classList.contains('mx-flip') && !!pitCardEl() && pitCardEl().classList.contains('mx-slide'));
  check('the spotlight rides the pair', !!batCardEl() && batCardEl().classList.contains('spot-bat') && !!pitCardEl() && pitCardEl().classList.contains('spot-pit'));
}
const settledBat = skeleton(batCardEl());
const settledPit = skeleton(pitCardEl());
check('no play button: the input controls are the triggers', findButtons(view, 'Play plate appearance').length === 0 && facControls().length === 1);
function driveOne() {
  const rare = findButtons(view, 'Resolve rare play');
  if (rare.length) { rare[0].click(); return true; }
  const fac = facControls();
  if (fac.length && !fac[0].disabled) { fac[0].click(); return true; }
  return false;
}
// One input mid-PA: the entrance is dismissed at once and
// does not replay, and the settled cards keep the plain
// geometry they had under the animation.
if (facControls().length) facControls()[0].click();
check('the next input dismisses the matchup entrance', !!batCardEl() && !batCardEl().classList.contains('mx-flip') && !!pitCardEl() && !pitCardEl().classList.contains('mx-slide'));
check('settled layout matches the pre-change geometry', skeleton(batCardEl()) === settledBat && skeleton(pitCardEl()) === settledPit);
// Highlight persistence: a completed PA leaves its read lit;
// the light survives a bare re-render, clears on the next
// input, and clears on Undo.
let guard = 0;
while (guard++ < 300 && !(PUI.UI.GS && PUI.UI.GS.paCount >= 1 && hasHl())) { if (!driveOne()) break; }
check('a completed PA leaves its read lit', hasHl(), 'pa=' + (PUI.UI.GS && PUI.UI.GS.paCount));
const showBtn = findButtons(view, 'Show');
if (showBtn.length) showBtn[0].click();
check('the highlight survives a re-render with no input', hasHl());
check('the held pair keeps its strip and its spotlight', !!strip() && findByClass(strip(), 'mx-vs').length === 1 && !!batCardEl() && batCardEl().classList.contains('spot-bat') && !batCardEl().classList.contains('mx-flip'));
if (facControls().length) facControls()[0].click();
check('the next input clears the highlight', !hasHl());
{
  const [bn2, pn2] = livePairNames();
  check('the strip names the new pair once play resumes', !!strip() && !!bn2 && strip().textContent.includes(bn2) && strip().textContent.includes(pn2), strip() && strip().textContent);
  check('a new PA presents its cards again', !!batCardEl() && batCardEl().classList.contains('mx-flip') && !!pitCardEl() && pitCardEl().classList.contains('mx-slide'));
}
guard = 0;
const paNow = PUI.UI.GS.paCount;
while (guard++ < 300 && PUI.UI.GS.paCount <= paNow) { if (!driveOne()) break; }
const undoBtn = findButtons(view, 'Undo');
if (undoBtn.length && !undoBtn[0].disabled) undoBtn[0].click();
check('undo clears the highlight', !hasHl());
let clicks = 0;
while (clicks++ < 4000) {
  if (findText(view, 'Final —')) break;
  if (!driveOne()) break;
}
check('the game plays to a final', findText(view, 'Final —'), 'clicks=' + clicks);
check('game over shows the standing exhibition notice', findText(view, 'Exhibition. This game is not in the tournament record. Adoption is Joe'));
check('game over shows the audit line', findText(view, 'Internal audit: every Section 10 equality passes'));
check('an autosave exists for the finished game', storageMap.size >= 1);

// Part 2: a manual-entry game. Start one, serve the parked
// steps through the form, and confirm a PA completes.
PUI.UI.GS = null;
PUI.renderPlay(view);
await tick();
for (const label of ['Frank Chance (profile)', 'Dick Williams (profile)', 'Manual entry']) {
  const b = findButtons(view, label);
  if (b.length) b[0].click();
}
const start2 = findButtons(view, 'Start the game');
start2[0].click();
const manBtn = findButtons(view, 'Manual entry');
if (manBtn.length) manBtn[0].click();
check('manual game parks at the first step with the entry form', findText(view, 'Next step: 2d6') && findButtons(view, 'Serve it').length === 1);
function inputs() {
  const out = [];
  (function walk(n) { if (n.tagName === 'INPUT') out.push(n); n.children.forEach(walk); })(view);
  return out;
}
let serves = 0;
while (serves++ < 40 && !findText(view, 'after PA 1')) {
  const serve = findButtons(view, 'Serve it');
  if (!serve.length) break;
  const ins = inputs();
  ins.forEach((inp, i) => { if (!inp.value) inp.value = String(10 + serves * 2 + i); });
  serve[0].click();
  const rare = findButtons(view, 'Resolve rare play');
  if (rare.length) rare[0].click();
}
check('manual serves complete the first PA', findText(view, 'after PA 1'), 'serves=' + serves);
console.log(fails === 0 ? 'UI SMOKE: PASS' : 'UI SMOKE: FAIL (' + fails + ')');
process.exit(fails ? 1 : 0);
