// Small Canvas-2D chart helpers for the HUD panels. Charts that support hover
// read cv._hover ({x, y} in canvas pixels, set by tip.hoverable), paint their own
// crosshair / highlight and return what is under the pointer.
import { price as fmtPrice } from './fmt.js';

export const C = {
  cyan: '#45d4ff', blue: '#4b8bff', amber: '#ffb22e', green: '#22e3a0', red: '#ff4f6e',
  violet: '#a78bfa', pink: '#ff5fd2', dim: '#6c80a3', dim2: '#46577a', grid: 'rgba(60,90,140,.18)', white: '#eef4ff',
};
const FONT = '10px "JetBrains Mono", Menlo, Consolas, monospace';

export function fitCanvas(cv) {
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const w = cv.clientWidth, h = cv.clientHeight;
  const W = Math.max(1, Math.round(w * dpr)), H = Math.max(1, Math.round(h * dpr));
  if (cv.width !== W || cv.height !== H) { cv.width = W; cv.height = H; }
  const ctx = cv.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return { ctx, w, h };
}

export function hexA(hex, a) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}

function vline(ctx, x, y0, y1) {
  ctx.strokeStyle = 'rgba(238,244,255,.35)'; ctx.setLineDash([3, 3]);
  ctx.beginPath(); ctx.moveTo(x + 0.5, y0); ctx.lineTo(x + 0.5, y1); ctx.stroke(); ctx.setLineDash([]);
}

/**
 * candles: [{t,o,h,l,c,v}] oldest → newest.
 * view: {step: px per candle, offset: candles scrolled back from the latest}.
 * Returns {k, prev, maxOffset} — k is the hovered candle (or null).
 */
export function drawCandles(cv, candles, view = {}) {
  const { ctx, w, h } = fitCanvas(cv);
  if (!candles.length || w < 40) return { k: null, maxOffset: 0 };
  const axisW = 58, plotW = w - axisW, volH = h * 0.18, plotH = h - volH - 4;
  const step = view.step || 6;
  const n = Math.min(candles.length, Math.floor(plotW / step));
  const maxOffset = Math.max(0, candles.length - n);
  const off = Math.min(maxOffset, Math.max(0, Math.round(view.offset || 0)));
  const end = candles.length - off, start = end - n;
  const cs = candles.slice(start, end);
  let lo = Infinity, hi = -Infinity, vmax = 0;
  for (const k of cs) { lo = Math.min(lo, k.l); hi = Math.max(hi, k.h); vmax = Math.max(vmax, k.v); }
  if (hi === lo) { hi += 1; lo -= 1; }
  const pad = (hi - lo) * 0.08; hi += pad; lo -= pad;
  const y = (p) => 4 + (hi - p) / (hi - lo) * (plotH - 8);
  ctx.font = FONT;
  ctx.textBaseline = 'middle';
  for (let i = 0; i <= 3; i++) {
    const p = lo + (hi - lo) * (i / 3), yy = y(p);
    ctx.strokeStyle = C.grid; ctx.setLineDash([2, 3]); ctx.beginPath(); ctx.moveTo(0, yy); ctx.lineTo(plotW, yy); ctx.stroke();
    ctx.setLineDash([]); ctx.fillStyle = C.dim2; ctx.fillText(fmtPrice(p), plotW + 4, yy);
  }
  const x0 = plotW - n * step, bw = Math.max(1, Math.round(step * 0.66));
  const hv = cv._hover;
  const hi_ = hv && hv.x < plotW ? Math.floor((hv.x - x0) / step) : -1;
  cs.forEach((k, i) => {
    const x = Math.round(x0 + i * step + step / 2), up = k.c >= k.o, col = up ? C.green : C.red;
    ctx.globalAlpha = hi_ >= 0 && hi_ !== i ? 0.75 : 1;
    ctx.strokeStyle = col; ctx.fillStyle = col;
    ctx.beginPath(); ctx.moveTo(x + 0.5, y(k.h)); ctx.lineTo(x + 0.5, y(k.l)); ctx.stroke();
    const yo = y(k.o), yc = y(k.c);
    ctx.fillRect(x - Math.floor(bw / 2), Math.min(yo, yc), bw, Math.max(1, Math.abs(yc - yo)));
    const vh = vmax ? (k.v / vmax) * volH : 0;
    ctx.fillStyle = hexA(col, i === hi_ ? 0.6 : 0.28); ctx.fillRect(x - Math.floor(bw / 2), h - vh, bw, vh);
  });
  ctx.globalAlpha = 1;
  // last price tag (latest candle, even when scrolled back)
  const last = candles[candles.length - 1].c, yl = y(last);
  if (yl > 0 && yl < plotH) {
    ctx.strokeStyle = hexA(C.amber, 0.7); ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(0, yl); ctx.lineTo(plotW, yl); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = C.amber; ctx.fillRect(plotW + 1, yl - 8, axisW - 1, 16);
    ctx.fillStyle = '#1a1200'; ctx.font = 'bold ' + FONT; ctx.fillText(fmtPrice(last), plotW + 4, yl + 0.5); ctx.font = FONT;
  }
  if (off > 0) { ctx.fillStyle = C.dim; ctx.textAlign = 'right'; ctx.fillText(`◀ ${off}`, plotW - 4, 10); ctx.textAlign = 'left'; }
  // crosshair
  let k = null, prev = null;
  if (hv) {
    if (hi_ >= 0 && hi_ < cs.length) {
      k = cs[hi_]; prev = candles[start + hi_ - 1] || null;
      vline(ctx, Math.round(x0 + hi_ * step + step / 2), 0, h);
    }
    if (hv.y < plotH && hv.x < plotW) {
      const p = hi - ((hv.y - 4) / (plotH - 8)) * (hi - lo);
      ctx.strokeStyle = 'rgba(238,244,255,.35)'; ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(0, Math.round(hv.y) + 0.5); ctx.lineTo(plotW, Math.round(hv.y) + 0.5); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = C.cyan; ctx.fillRect(plotW + 1, hv.y - 8, axisW - 1, 16);
      ctx.fillStyle = '#04121c'; ctx.font = 'bold ' + FONT; ctx.fillText(fmtPrice(p), plotW + 4, hv.y + 0.5); ctx.font = FONT;
    }
  }
  return { k, prev, maxOffset, n };
}

export function drawSpark(cv, arr, color, { fill = true, dot = true, zero = false } = {}) {
  const { ctx, w, h } = fitCanvas(cv);
  const v = arr.filter(Number.isFinite);
  if (v.length < 2) return;
  let lo = Math.min(...v), hi = Math.max(...v);
  if (zero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
  if (hi === lo) { hi += Math.abs(hi) * 0.001 + 1e-9; lo -= Math.abs(lo) * 0.001 + 1e-9; }
  const X = (i) => 1 + (i / (v.length - 1)) * (w - 4);
  const Y = (p) => 2 + (hi - p) / (hi - lo) * (h - 4);
  if (zero && lo < 0 && hi > 0) {
    ctx.strokeStyle = C.grid; ctx.beginPath(); ctx.moveTo(0, Y(0)); ctx.lineTo(w, Y(0)); ctx.stroke();
  }
  ctx.beginPath();
  v.forEach((p, i) => (i ? ctx.lineTo(X(i), Y(p)) : ctx.moveTo(X(i), Y(p))));
  ctx.strokeStyle = color; ctx.lineWidth = 1.3; ctx.shadowColor = color; ctx.shadowBlur = 6; ctx.stroke(); ctx.shadowBlur = 0;
  if (fill) {
    ctx.lineTo(X(v.length - 1), h); ctx.lineTo(X(0), h); ctx.closePath();
    const g = ctx.createLinearGradient(0, 0, 0, h); g.addColorStop(0, hexA(color, 0.25)); g.addColorStop(1, hexA(color, 0));
    ctx.fillStyle = g; ctx.fill();
  }
  if (dot) {
    const x = X(v.length - 1), y = Y(v[v.length - 1]);
    ctx.fillStyle = C.white; ctx.shadowColor = color; ctx.shadowBlur = 8;
    ctx.beginPath(); ctx.arc(x, y, 2, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0;
  }
}

/** simple bar series; returns the hovered index (or -1) */
export function drawBars(cv, arr, color) {
  const { ctx, w, h } = fitCanvas(cv);
  const max = Math.max(1, ...arr), bw = w / arr.length;
  const hv = cv._hover, hi = hv ? Math.min(arr.length - 1, Math.max(0, Math.floor(hv.x / bw))) : -1;
  ctx.fillStyle = color; ctx.shadowColor = color; ctx.shadowBlur = 4;
  arr.forEach((v, i) => {
    const bh = (v / max) * (h - 2);
    ctx.globalAlpha = hi >= 0 ? (i === hi ? 1 : 0.3) : 0.35 + 0.65 * (i / arr.length);
    ctx.fillRect(i * bw + 0.5, h - bh, Math.max(1, bw - 1.5), bh);
  });
  ctx.globalAlpha = 1; ctx.shadowBlur = 0;
  return hi;
}

/** series: [{ts, bps, prem, latS, latF}] sampled 1/s; returns the hovered index (or -1) */
export function drawBasis(cv, series, labels) {
  const { ctx, w, h } = fitCanvas(cv);
  ctx.font = FONT; ctx.textBaseline = 'top';
  const lat = h * 0.26, ph = h - lat - 6;
  ctx.strokeStyle = C.grid;
  for (let i = 1; i < 4; i++) { const y = (ph / 4) * i; ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke(); }
  if (series.length < 2) return -1;
  const vals = series.flatMap((s) => [s.bps, s.prem]).filter(Number.isFinite);
  let lo = Math.min(0, ...vals), hi = Math.max(0, ...vals);
  if (hi - lo < 2) { hi += 1; lo -= 1; }
  const X = (i) => (i / (series.length - 1)) * (w - 2);
  const Y = (v) => 2 + (hi - v) / (hi - lo) * (ph - 4);
  ctx.strokeStyle = hexA(C.white, 0.18); ctx.setLineDash([2, 3]);
  ctx.beginPath(); ctx.moveTo(0, Y(0)); ctx.lineTo(w, Y(0)); ctx.stroke(); ctx.setLineDash([]);
  const line = (key, col) => {
    ctx.beginPath(); let started = false;
    series.forEach((s, i) => {
      if (!Number.isFinite(s[key])) return;
      started ? ctx.lineTo(X(i), Y(s[key])) : ctx.moveTo(X(i), Y(s[key])); started = true;
    });
    ctx.strokeStyle = col; ctx.lineWidth = 1.3; ctx.shadowColor = col; ctx.shadowBlur = 6; ctx.stroke(); ctx.shadowBlur = 0;
  };
  line('prem', C.violet);
  line('bps', C.cyan);
  const lmax = Math.max(50, ...series.map((s) => Math.max(s.latS || 0, s.latF || 0)));
  const bw = (w - 2) / series.length;
  series.forEach((s, i) => {
    const a = Math.max(0, s.latS || 0) / lmax * lat, b = Math.max(0, s.latF || 0) / lmax * lat;
    ctx.fillStyle = hexA(C.amber, 0.65); ctx.fillRect(i * bw, h - a, Math.max(1, bw * 0.45), a);
    ctx.fillStyle = hexA(C.violet, 0.55); ctx.fillRect(i * bw + bw * 0.5, h - b, Math.max(1, bw * 0.45), b);
  });
  ctx.fillStyle = C.cyan; ctx.fillText('— ' + labels.basis, 4, 3);
  ctx.fillStyle = C.violet; ctx.fillText('— ' + labels.prem, 4, 15);
  ctx.fillStyle = C.amber; ctx.fillText('▮ ' + labels.lat + ' (max ' + Math.round(lmax) + ')', 4, ph + 2);
  ctx.fillStyle = C.dim2; ctx.textAlign = 'right';
  ctx.fillText(hi.toFixed(1), w - 2, 3); ctx.fillText(lo.toFixed(1), w - 2, ph - 12); ctx.textAlign = 'left';
  const hv = cv._hover;
  if (!hv) return -1;
  const i = Math.min(series.length - 1, Math.max(0, Math.round((hv.x / (w - 2)) * (series.length - 1))));
  vline(ctx, X(i), 0, h);
  for (const [key, col] of [['bps', C.cyan], ['prem', C.violet]]) {
    if (!Number.isFinite(series[i][key])) continue;
    ctx.fillStyle = col; ctx.beginPath(); ctx.arc(X(i), Y(series[i][key]), 3, 0, Math.PI * 2); ctx.fill();
  }
  return i;
}

/** buckets: [{buy, sell}] oldest → newest; returns the hovered index (or -1) */
export function drawFlow(cv, buckets) {
  const { ctx, w, h } = fitCanvas(cv);
  const max = Math.max(1, ...buckets.map((b) => Math.max(b.buy, b.sell)));
  const mid = h / 2, bw = w / buckets.length;
  const hv = cv._hover, hi = hv ? Math.min(buckets.length - 1, Math.max(0, Math.floor(hv.x / bw))) : -1;
  ctx.strokeStyle = C.grid; ctx.beginPath(); ctx.moveTo(0, mid); ctx.lineTo(w, mid); ctx.stroke();
  buckets.forEach((b, i) => {
    const up = (b.buy / max) * (mid - 2), dn = (b.sell / max) * (mid - 2), a = hi >= 0 && hi !== i ? 0.35 : 0.85;
    ctx.fillStyle = hexA(C.green, a); ctx.fillRect(i * bw + 1, mid - up, bw - 2, up);
    ctx.fillStyle = hexA(C.red, a); ctx.fillRect(i * bw + 1, mid + 1, bw - 2, dn);
  });
  if (hi >= 0) { ctx.strokeStyle = 'rgba(238,244,255,.5)'; ctx.strokeRect(hi * bw + 0.5, 0.5, bw - 1, h - 1); }
  return hi;
}

/** bins: [{label, n, sign}] — 24h change distribution; returns the hovered index (or -1) */
export function drawDist(cv, bins) {
  const { ctx, w, h } = fitCanvas(cv);
  if (!bins.length) return -1;
  const max = Math.max(1, ...bins.map((b) => b.n));
  const labH = 12, cntH = 11, ph = h - labH - cntH, bw = w / bins.length;
  const hv = cv._hover, hi = hv ? Math.min(bins.length - 1, Math.max(0, Math.floor(hv.x / bw))) : -1;
  ctx.font = FONT; ctx.textAlign = 'center'; ctx.textBaseline = 'top';
  bins.forEach((b, i) => {
    const bh = Math.max(1, (b.n / max) * ph), x = i * bw;
    const col = b.sign > 0 ? C.green : b.sign < 0 ? C.red : C.dim;
    const g = ctx.createLinearGradient(0, h - labH - bh, 0, h - labH);
    g.addColorStop(0, hexA(col, 0.95)); g.addColorStop(1, hexA(col, 0.25));
    ctx.globalAlpha = hi >= 0 && hi !== i ? 0.4 : 1;
    ctx.fillStyle = g; ctx.shadowColor = col; ctx.shadowBlur = 6;
    ctx.fillRect(x + 2, h - labH - bh, bw - 4, bh);
    ctx.shadowBlur = 0;
    ctx.fillStyle = C.white; ctx.fillText(String(b.n), x + bw / 2, h - labH - bh - cntH);
    ctx.fillStyle = C.dim2; ctx.fillText(b.label, x + bw / 2, h - labH + 2);
  });
  ctx.globalAlpha = 1; ctx.textAlign = 'left';
  return hi;
}
