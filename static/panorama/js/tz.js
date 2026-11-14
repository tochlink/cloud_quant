// Time-zone switcher for the header clock. The chosen zone is applied to every
// timestamp on the page (fmt.hms / hmsms) and remembered in localStorage.
import * as F from './fmt.js';
import { t, getLang } from './i18n.js';

const LOCAL = (() => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'; } catch (e) { return 'UTC'; } })();
export const ZONES = [
  { id: 'UTC', cc: 'UTC', zh: '协调世界时', en: 'Coordinated Universal Time' },
  { id: LOCAL, cc: 'LOC', zh: `本机时区 · ${LOCAL}`, en: `This device · ${LOCAL}`, local: true },
  { id: 'Asia/Shanghai', cc: 'CN', zh: '中国 · 北京', en: 'China · Beijing' },
  { id: 'Asia/Hong_Kong', cc: 'HK', zh: '中国香港', en: 'Hong Kong' },
  { id: 'Asia/Taipei', cc: 'TW', zh: '中国台北', en: 'Taipei' },
  { id: 'Asia/Singapore', cc: 'SG', zh: '新加坡', en: 'Singapore' },
  { id: 'Asia/Tokyo', cc: 'JP', zh: '日本 · 东京', en: 'Japan · Tokyo' },
  { id: 'Asia/Seoul', cc: 'KR', zh: '韩国 · 首尔', en: 'Korea · Seoul' },
  { id: 'Asia/Bangkok', cc: 'TH', zh: '泰国 · 曼谷', en: 'Thailand · Bangkok' },
  { id: 'Asia/Kolkata', cc: 'IN', zh: '印度 · 新德里', en: 'India · New Delhi' },
  { id: 'Asia/Dubai', cc: 'AE', zh: '阿联酋 · 迪拜', en: 'UAE · Dubai' },
  { id: 'Europe/Moscow', cc: 'RU', zh: '俄罗斯 · 莫斯科', en: 'Russia · Moscow' },
  { id: 'Europe/Istanbul', cc: 'TR', zh: '土耳其 · 伊斯坦布尔', en: 'Türkiye · Istanbul' },
  { id: 'Europe/Berlin', cc: 'DE', zh: '德国 · 柏林', en: 'Germany · Berlin' },
  { id: 'Europe/Paris', cc: 'FR', zh: '法国 · 巴黎', en: 'France · Paris' },
  { id: 'Europe/London', cc: 'GB', zh: '英国 · 伦敦', en: 'UK · London' },
  { id: 'America/Sao_Paulo', cc: 'BR', zh: '巴西 · 圣保罗', en: 'Brazil · São Paulo' },
  { id: 'America/New_York', cc: 'US', zh: '美国 · 纽约', en: 'US · New York' },
  { id: 'America/Chicago', cc: 'US', zh: '美国 · 芝加哥', en: 'US · Chicago' },
  { id: 'America/Los_Angeles', cc: 'US', zh: '美国 · 洛杉矶', en: 'US · Los Angeles' },
  { id: 'Australia/Sydney', cc: 'AU', zh: '澳大利亚 · 悉尼', en: 'Australia · Sydney' },
];
const KEY = 'c3.tz';

const offCache = new Map();
/** "UTC+8", "UTC-5", "UTC" for a zone at a given instant */
export function offsetLabel(zone, ms) {
  const k = zone + '|' + Math.floor(ms / 3600000);
  if (offCache.has(k)) return offCache.get(k);
  let s = 'UTC';
  try {
    const p = new Intl.DateTimeFormat('en-US', { timeZone: zone, timeZoneName: 'shortOffset' }).formatToParts(new Date(ms));
    s = (p.find((x) => x.type === 'timeZoneName')?.value || 'GMT').replace('GMT', 'UTC');
  } catch (e) { /* keep UTC */ }
  offCache.set(k, s);
  return s;
}

const short = (z) => {
  const name = getLang() === 'zh' ? z.zh : z.en;
  return z.local ? (getLang() === 'zh' ? '本机' : 'Local') : name.split(' · ').pop();
};

export function createTz(root, { getNow, onChange }) {
  const btn = root.querySelector('.tz-btn');
  const pop = root.querySelector('.tz-pop');
  const list = root.querySelector('.tz-list');
  let open = false;
  let cur = (() => { try { const v = localStorage.getItem(KEY); if (v && ZONES.some((z) => z.id === v)) return v; } catch (e) { /* ignore */ } return 'UTC'; })();
  F.setTz(cur);

  const zone = () => ZONES.find((z) => z.id === cur) || ZONES[0];
  function label() {
    const z = zone(), now = getNow();
    btn.querySelector('.tz-cc').textContent = z.cc;
    btn.querySelector('.tz-name').textContent = z.id === 'UTC' ? 'UTC' : `${short(z)} ${offsetLabel(z.id, now)}`;
  }
  function render() {
    const now = getNow();
    list.innerHTML = ZONES.map((z) => `<div class="tz-row${z.id === cur ? ' on' : ''}" data-id="${F.esc(z.id)}">` +
      `<i>${F.esc(z.cc)}</i><span class="tz-n">${F.esc(getLang() === 'zh' ? z.zh : z.en)}</span>` +
      `<b>${F.hms(now, z.id).slice(0, 5)}</b><em>${F.esc(offsetLabel(z.id, now))}</em></div>`).join('');
  }
  function show() { open = true; pop.hidden = false; root.classList.add('open'); render(); list.querySelector('.on')?.scrollIntoView({ block: 'nearest' }); }
  function hide() { open = false; pop.hidden = true; root.classList.remove('open'); }

  btn.addEventListener('click', (e) => { e.stopPropagation(); open ? hide() : show(); });
  document.addEventListener('pointerdown', (e) => { if (open && !root.contains(e.target)) hide(); });
  document.addEventListener('keydown', (e) => { if (open && e.key === 'Escape') hide(); });
  list.addEventListener('click', (e) => {
    const row = e.target.closest('.tz-row');
    if (!row) return;
    cur = row.dataset.id;
    try { localStorage.setItem(KEY, cur); } catch (err) { /* ignore */ }
    F.setTz(cur);
    label(); hide();
    onChange && onChange(cur);
  });
  setInterval(() => { label(); if (open) render(); }, 1000);
  label();

  return { label, short: () => (cur === 'UTC' ? 'UTC' : offsetLabel(cur, getNow())) };
}
