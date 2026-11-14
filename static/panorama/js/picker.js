// Searchable symbol picker: quick chips (recent + majors), sort tabs, rows with
// avatar / perp tag / price / 24h change pill / volume, keyboard navigation
// (↑ ↓ Enter Esc) and "/" to open from anywhere.
import * as F from './fmt.js';
import { t } from './i18n.js';

const MAJORS = ['BTC_USDT', 'ETH_USDT', 'SOL_USDT', 'XRP_USDT', 'DOGE_USDT', 'BNB_USDT', 'SUI_USDT', 'PEPE_USDT'];
const RECENT_KEY = 'c3.recent';

function loadRecent() {
  try { const v = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'); return Array.isArray(v) ? v.slice(0, 6) : []; } catch (e) { return []; }
}
function saveRecent(list) {
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(list.slice(0, 6))); } catch (e) { /* ignore */ }
}
function hue(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360;
  return h;
}

export function createPicker(root, { getRows, getRec, getSel, onPick }) {
  const btn = root.querySelector('.pk-btn');
  const pop = root.querySelector('.pk-pop');
  const input = root.querySelector('.pk-q');
  const list = root.querySelector('.pk-list');
  const tabs = root.querySelector('.pk-tabs');
  const quick = root.querySelector('.pk-quick');
  const count = root.querySelector('.pk-count');
  let open = false, sort = 'vol', idx = 0, rows = [];
  let recent = loadRecent();

  function renderQuick() {
    const syms = [...new Set([...recent, ...MAJORS])].filter((s) => getRec(s)).slice(0, 8);
    quick.innerHTML = `<span class="pk-ql">${F.esc(t('pk.quick'))}</span>` + syms.map((s) => {
      const r = getRec(s);
      return `<button type="button" class="pk-chip${s === getSel() ? ' on' : ''}" data-sym="${F.esc(s)}">${F.esc(r.base)}<span class="${F.cls(r.chg)}">${F.pct(r.chg, 1)}</span></button>`;
    }).join('');
  }

  function render(keepScroll = true) {
    const top = list.scrollTop;
    const res = getRows(sort, input.value.trim().toUpperCase());
    rows = res.rows;
    count.textContent = t('pk.count', { n: F.num(res.total) });
    idx = Math.max(0, Math.min(idx, rows.length - 1));
    const sel = getSel();
    list.innerHTML = rows.length
      ? rows.map((r, i) => `<div class="pk-row${i === idx ? ' act' : ''}${r.pair === sel ? ' sel' : ''}" data-i="${i}" role="option">` +
          `<span class="pk-coin"><i class="pk-av" style="--h:${hue(r.base)}">${F.esc(r.base.slice(0, 1))}</i><b>${F.esc(r.base)}</b><em>/USDT</em>${r.perp ? `<u>${F.esc(t('perp'))}</u>` : ''}</span>` +
          `<span class="pk-px">${F.price(r.last)}</span>` +
          `<span class="pk-ch"><s class="${r.chg > 0 ? 'up' : r.chg < 0 ? 'dn' : ''}">${F.pct(r.chg)}</s></span>` +
          `<span class="pk-vol">${F.usd(r.qv)}</span></div>`).join('')
      : `<div class="pk-empty">${F.esc(t('pk.none'))}</div>`;
    if (keepScroll) list.scrollTop = top;
    renderQuick();
  }
  function scrollAct() { list.children[idx]?.scrollIntoView({ block: 'nearest' }); }
  function show() {
    open = true; pop.hidden = false; root.classList.add('open');
    input.value = ''; idx = 0; list.scrollTop = 0;
    input.placeholder = t('pk.search');
    render(false); input.focus();
  }
  function hide() { open = false; pop.hidden = true; root.classList.remove('open'); }
  function pick(sym) {
    recent = [sym, ...recent.filter((s) => s !== sym)].slice(0, 6);
    saveRecent(recent);
    onPick(sym);
    hide();
  }
  function choose(i) { const r = rows[i]; if (r) pick(r.pair); }

  btn.addEventListener('click', (e) => { e.stopPropagation(); open ? hide() : show(); });
  document.addEventListener('pointerdown', (e) => { if (open && !root.contains(e.target)) hide(); });
  document.addEventListener('keydown', (e) => {
    if (e.key === '/' && !open && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName || '')) { e.preventDefault(); show(); }
  });
  input.addEventListener('input', () => { idx = 0; list.scrollTop = 0; render(false); });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { idx = Math.min(rows.length - 1, idx + 1); render(); scrollAct(); e.preventDefault(); }
    else if (e.key === 'ArrowUp') { idx = Math.max(0, idx - 1); render(); scrollAct(); e.preventDefault(); }
    else if (e.key === 'Enter') choose(idx);
    else if (e.key === 'Escape') hide();
  });
  list.addEventListener('click', (e) => { const row = e.target.closest('.pk-row'); if (row) choose(+row.dataset.i); });
  quick.addEventListener('click', (e) => { const c = e.target.closest('.pk-chip'); if (c) pick(c.dataset.sym); });
  tabs.addEventListener('click', (e) => {
    const b = e.target.closest('button[data-s]');
    if (!b) return;
    sort = b.dataset.s;
    tabs.querySelectorAll('button').forEach((x) => x.classList.toggle('on', x === b));
    idx = 0; list.scrollTop = 0; render(false); input.focus();
  });
  setInterval(() => { if (open) render(); }, 1500);

  return { refresh: () => open && render() };
}
