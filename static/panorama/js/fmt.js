import { locale } from './i18n.js';

const ok = (v) => v != null && Number.isFinite(v);
const nf = new Map();
function fmt(key, opts) {
  const k = locale() + key;
  if (!nf.has(k)) nf.set(k, new Intl.NumberFormat(locale(), opts));
  return nf.get(k);
}

/** 1.28B / 12.8亿 */
export function compact(v, d = 2) {
  if (!ok(v)) return '—';
  return fmt('c' + d, { notation: 'compact', maximumFractionDigits: d }).format(v);
}
export const usd = (v, d = 2) => (ok(v) ? (v < 0 ? '-$' : '$') + compact(Math.abs(v), d) : '—');

export function priceDigits(p) {
  const a = Math.abs(p);
  if (a >= 10000) return 1;
  if (a >= 100) return 2;
  if (a >= 1) return 3;
  if (a >= 0.01) return 5;
  if (a >= 0.0001) return 7;
  return 9;
}
export function price(p, d) {
  if (!ok(p)) return '—';
  const n = d ?? priceDigits(p);
  return p.toLocaleString('en-US', { minimumFractionDigits: n, maximumFractionDigits: n });
}
export function num(v, d = 0) {
  if (!ok(v)) return '—';
  return v.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
}
/** Size (base amount) with adaptive precision */
export function amt(v) {
  if (!ok(v)) return '—';
  const a = Math.abs(v);
  return num(v, a >= 1000 ? 0 : a >= 10 ? 2 : a >= 1 ? 3 : a >= 0.01 ? 4 : 6);
}
export function pct(v, d = 2) {
  if (!ok(v)) return '—';
  return (v > 0 ? '+' : '') + v.toFixed(d) + '%';
}
export function bps(v, d = 1) {
  if (!ok(v)) return '—';
  return (v > 0 ? '+' : '') + v.toFixed(d);
}
const p2 = (n) => String(n).padStart(2, '0');
// display time zone for every timestamp on the page (set by the header switcher)
let tz = 'UTC';
const tzFmt = new Map();
export const setTz = (z) => { tz = z; };
export const getTz = () => tz;
function zoneFmt(z) {
  if (!tzFmt.has(z)) {
    try { tzFmt.set(z, new Intl.DateTimeFormat('en-GB', { timeZone: z, hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' })); }
    catch (e) { tzFmt.set(z, null); }
  }
  return tzFmt.get(z);
}
export function hms(ms, zone = tz) {
  const f = zone === 'UTC' ? null : zoneFmt(zone);
  if (f) return f.format(new Date(ms));
  const d = new Date(ms);
  return `${p2(d.getUTCHours())}:${p2(d.getUTCMinutes())}:${p2(d.getUTCSeconds())}`;
}
const dFmt = new Map();
/** "11-14 13:35" in the display time zone (for candles) */
export function dhm(ms, zone = tz) {
  if (!dFmt.has(zone)) {
    try { dFmt.set(zone, new Intl.DateTimeFormat('en-GB', { timeZone: zone, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })); }
    catch (e) { dFmt.set(zone, null); }
  }
  const f = dFmt.get(zone);
  if (!f) return hms(ms).slice(0, 5);
  const p = Object.fromEntries(f.formatToParts(new Date(ms)).map((x) => [x.type, x.value]));
  return `${p.month}-${p.day} ${p.hour}:${p.minute}`;
}
export function hmsms(ms) {
  return hms(ms) + '.' + String(Math.floor(((ms % 1000) + 1000) % 1000)).padStart(3, '0');
}
export function dur(sec) {
  if (!ok(sec) || sec < 0) return '—';
  const h = Math.floor(sec / 3600), m = Math.floor((sec % 3600) / 60), s = Math.floor(sec % 60);
  return `${p2(h)}:${p2(m)}:${p2(s)}`;
}
export function bytes(n) {
  if (!ok(n)) return '—';
  if (n < 1024) return n + ' B';
  if (n < 1048576) return (n / 1024).toFixed(1) + ' KB';
  return (n / 1048576).toFixed(2) + ' MB';
}
export const base = (pair) => (pair || '').split('_')[0];
export const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'dn' : '');
// numeric entities (same meaning as the named ones, which the repo sync would decode)
const ESC = { '&': '&#38;', '<': '&#60;', '>': '&#62;', '"': '&#34;', "'": '&#39;' };
export const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ESC[c]);
