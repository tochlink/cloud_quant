// Market heatmap: squarified treemap, area = 24h volume (dampened), colour =
// 24h change, tiles flash on live trades. Hover for details, click to select.
import { fitCanvas, C } from './charts.js';
import * as F from './fmt.js';

function worst(row, side) {
  let sum = 0, mx = 0, mn = Infinity;
  for (const r of row) { sum += r.v; mx = Math.max(mx, r.v); mn = Math.min(mn, r.v); }
  const s2 = side * side, sum2 = sum * sum;
  return Math.max((s2 * mx) / sum2, sum2 / (s2 * mn));
}

function squarify(items, x, y, w, h) {
  const out = [];
  let rest = items.slice();
  while (rest.length) {
    const side = Math.min(w, h);
    const row = [rest[0]];
    let i = 1;
    while (i < rest.length && worst([...row, rest[i]], side) <= worst(row, side)) { row.push(rest[i]); i++; }
    rest = rest.slice(i);
    const sum = row.reduce((s, r) => s + r.v, 0);
    if (w >= h) {
      const cw = sum / h; let yy = y;
      for (const r of row) { const rh = r.v / cw; out.push({ ...r, x, y: yy, w: cw, h: rh }); yy += rh; }
      x += cw; w -= cw;
    } else {
      const rh = sum / w; let xx = x;
      for (const r of row) { const rw = r.v / rh; out.push({ ...r, x: xx, y, w: rw, h: rh }); xx += rw; }
      y += rh; h -= rh;
    }
  }
  return out;
}

function tileColor(chg) {
  const a = Math.min(1, Math.abs(chg || 0) / 8);
  const base = [12, 22, 42];
  const tgt = chg >= 0 ? [16, 168, 116] : [196, 46, 78];
  const c = base.map((b, i) => Math.round(b + (tgt[i] - b) * (0.18 + 0.82 * a)));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}

export function createHeatmap(cv, { onPick, onHover } = {}) {
  let items = [], rects = [], dirty = true, lastW = 0, lastH = 0, hover = null, sel = null, lastDraw = 0;
  const flashes = new Map();

  /** list: [{sym, rec}] where rec is the live spot record ({base, last, chg, qv}) */
  function setData(list) { items = list; dirty = true; }
  function setSelected(sym) { sel = sym; }
  function flash(sym, a) { flashes.set(sym, Math.min(1, (flashes.get(sym) || 0) + a)); }

  function layout(w, h) {
    const weights = items.map((x) => Math.pow(Math.max(1, x.rec.qv), 0.55));
    const tot = weights.reduce((a, b) => a + b, 0) || 1;
    const arr = items.map((x, i) => ({ sym: x.sym, rec: x.rec, v: (weights[i] / tot) * w * h })).sort((a, b) => b.v - a.v);
    rects = arr.length ? squarify(arr, 0, 0, w, h) : [];
  }

  function hit(x, y) { return rects.find((r) => x >= r.x && x < r.x + r.w && y >= r.y && y < r.y + r.h); }
  cv.addEventListener('pointermove', (e) => {
    const b = cv.getBoundingClientRect(), r = hit(e.clientX - b.left, e.clientY - b.top);
    hover = r ? r.sym : null;
    cv.style.cursor = r ? 'pointer' : '';
    onHover && onHover(hover, e.clientX - b.left, e.clientY - b.top);
  });
  cv.addEventListener('pointerleave', () => { hover = null; onHover && onHover(null); });
  cv.addEventListener('click', (e) => {
    const b = cv.getBoundingClientRect(), r = hit(e.clientX - b.left, e.clientY - b.top);
    if (r && onPick) onPick(r.sym);
  });

  function draw(now) {
    if (now - lastDraw < 66) return;
    const dt = Math.min(0.3, (now - lastDraw) / 1000);
    lastDraw = now;
    const { ctx, w, h } = fitCanvas(cv);
    if (dirty || w !== lastW || h !== lastH) { layout(w, h); dirty = false; lastW = w; lastH = h; }
    const decay = Math.exp(-dt * 2.5);
    ctx.textBaseline = 'top';
    for (const r of rects) {
      const rec = r.rec, x = r.x + 1, y = r.y + 1, rw = r.w - 2, rh = r.h - 2;
      if (rw <= 0 || rh <= 0) continue;
      ctx.fillStyle = tileColor(rec.chg);
      ctx.fillRect(x, y, rw, rh);
      const g = ctx.createLinearGradient(0, y, 0, y + rh);
      g.addColorStop(0, 'rgba(255,255,255,.06)'); g.addColorStop(1, 'rgba(0,0,0,.18)');
      ctx.fillStyle = g; ctx.fillRect(x, y, rw, rh);
      const fl = flashes.get(r.sym) || 0;
      if (fl > 0.02) {
        ctx.strokeStyle = `rgba(255,178,46,${Math.min(1, fl).toFixed(2)})`; ctx.lineWidth = 2;
        ctx.strokeRect(x + 1, y + 1, rw - 2, rh - 2);
        flashes.set(r.sym, fl * decay);
      }
      if (r.sym === sel || r.sym === hover) {
        ctx.strokeStyle = r.sym === sel ? C.cyan : 'rgba(238,244,255,.8)'; ctx.lineWidth = r.sym === sel ? 2 : 1;
        ctx.shadowColor = C.cyan; ctx.shadowBlur = r.sym === sel ? 10 : 0;
        ctx.strokeRect(x + 1, y + 1, rw - 2, rh - 2); ctx.shadowBlur = 0;
      }
      if (rw < 28 || rh < 16) continue;
      const fs = Math.max(9, Math.min(24, Math.min(rw / 4.2, rh / 2.6)));
      ctx.fillStyle = '#f4f8ff';
      ctx.font = `800 ${fs.toFixed(0)}px "JetBrains Mono", Menlo, Consolas, monospace`;
      ctx.fillText(rec.base, x + 5, y + 4, rw - 8);
      if (rh > fs + 16) {
        const s = Math.max(9, fs * 0.6);
        ctx.font = `700 ${s.toFixed(0)}px "JetBrains Mono", Menlo, Consolas, monospace`;
        ctx.fillStyle = 'rgba(244,248,255,.9)';
        ctx.fillText(F.pct(rec.chg), x + 5, y + 6 + fs, rw - 8);
        if (rh > fs + s * 2 + 18) {
          ctx.fillStyle = 'rgba(244,248,255,.6)';
          ctx.font = `${Math.max(9, s * 0.85).toFixed(0)}px "JetBrains Mono", Menlo, Consolas, monospace`;
          ctx.fillText(F.price(rec.last), x + 5, y + 8 + fs + s, rw - 8);
        }
      }
    }
  }

  return { setData, setSelected, flash, draw };
}
