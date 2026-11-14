// Interactive liquidation timeline.
// Liquidations of the same contract + side within a short window are merged into
// one bubble (area ~ total notional), so cascades read as one event instead of a
// column of dots. Hover: crosshair + details, click: select the contract,
// filters: side / minimum size / time range, external highlight of one contract.
import { fitCanvas, C, hexA } from './charts.js';
import * as F from './fmt.js';
import { t } from './i18n.js';

const FONT = '10px "JetBrains Mono", Menlo, Consolas, monospace';

export function createLiqChart(root, { onPick, getNow, getSel }) {
  const cv = root.querySelector('canvas');
  const tip = root.querySelector('.lq-tip');
  const ctl = root.querySelector('.lq-ctl');
  const st = { side: 'all', min: 0, range: 60 };
  let points = [], buckets = [], geom = null, mouse = null, highlight = null, hoverPt = null, lastDraw = 0, data = [];

  ctl.addEventListener('click', (e) => {
    const b = e.target.closest('button[data-v]');
    if (!b) return;
    const seg = b.parentElement, k = seg.dataset.k;
    st[k] = k === 'side' ? b.dataset.v : +b.dataset.v;
    seg.querySelectorAll('button').forEach((x) => x.classList.toggle('on', x === b));
    lastDraw = 0;
  });
  cv.addEventListener('pointermove', (e) => {
    const r = cv.getBoundingClientRect();
    mouse = { x: e.clientX - r.left, y: e.clientY - r.top };
    lastDraw = 0;
  });
  cv.addEventListener('pointerleave', () => { mouse = null; tip.style.display = 'none'; lastDraw = 0; });
  cv.addEventListener('click', () => { if (hoverPt && onPick) onPick(hoverPt.pair); });

  function setHighlight(pair) { highlight = pair; lastDraw = 0; }

  // merge raw liquidations into bubbles
  function cluster(liqs, now) {
    const t0 = now - st.range * 60000, win = st.range > 30 ? 30000 : 10000, map = new Map();
    for (const q of liqs) {
      if (q.ts < t0) break;
      if (st.side !== 'all' && q.side !== st.side) continue;
      const key = q.pair + '|' + q.side + '|' + Math.floor(q.ts / win);
      let c = map.get(key);
      if (!c) { c = { pair: q.pair, side: q.side, ts: q.ts, t1: q.ts, n: 0, notional: 0, lo: Infinity, hi: -Infinity }; map.set(key, c); }
      c.n++; c.notional += q.notional; c.ts = Math.max(c.ts, q.ts); c.t1 = Math.min(c.t1, q.ts);
      c.lo = Math.min(c.lo, q.px); c.hi = Math.max(c.hi, q.px);
    }
    return [...map.values()].filter((c) => c.notional >= st.min).sort((a, b) => a.notional - b.notional);
  }

  function showTip(html, x, y) {
    tip.innerHTML = html;
    tip.style.display = 'block';
    const w = root.querySelector('.lq-cv');
    tip.style.left = Math.max(4, Math.min(x + 14, w.clientWidth - tip.offsetWidth - 4)) + 'px';
    tip.style.top = Math.max(4, Math.min(y + 14, w.clientHeight - tip.offsetHeight - 4)) + 'px';
  }

  function draw(nowPerf, liqs) {
    data = liqs;
    if (nowPerf - lastDraw < 250) return;
    lastDraw = nowPerf;
    const now = getNow(), sel = getSel();
    const { ctx, w, h } = fitCanvas(cv);
    const padL = 46, padR = 10, padT = 10, stripH = 34, axisH = 14;
    const plotH = h - padT - stripH - axisH - 8, plotW = w - padL - padR;
    if (plotW < 60 || plotH < 40) return;
    const span = st.range * 60000, t0 = now - span;
    const X = (ts) => padL + ((ts - t0) / span) * plotW;
    const yLo = 1, yHi = 7;
    const Y = (n) => padT + (1 - (Math.min(yHi, Math.max(yLo, Math.log10(Math.max(1, n)))) - yLo) / (yHi - yLo)) * plotH;
    geom = { padL, padT, plotW, plotH, stripH, t0, span };
    ctx.font = FONT; ctx.textBaseline = 'middle';

    // grid + axes
    for (const [v, lab] of [[2, '$100'], [3, '$1K'], [4, '$10K'], [5, '$100K'], [6, '$1M']]) {
      const y = padT + (1 - (v - yLo) / (yHi - yLo)) * plotH;
      ctx.strokeStyle = C.grid; ctx.setLineDash([2, 4]); ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(w - padR, y); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = C.dim2; ctx.textAlign = 'right'; ctx.fillText(lab, padL - 6, y);
    }
    const step = st.range > 30 ? 15 : 5;
    ctx.textAlign = 'center';
    for (let m = 0; m <= st.range; m += step) {
      const x = X(now - m * 60000);
      ctx.strokeStyle = C.grid; ctx.beginPath(); ctx.moveTo(x, padT); ctx.lineTo(x, padT + plotH); ctx.stroke();
      ctx.fillStyle = C.dim2; ctx.fillText(m ? `-${m}m` : t('fn.now'), Math.min(w - 18, Math.max(padL + 10, x)), h - axisH / 2);
    }

    // bottom strip: totals per bucket (shorts up, longs down)
    const bmin = st.range > 30 ? 5 : 1, nb = Math.round(st.range / bmin), bw = plotW / nb;
    buckets = Array.from({ length: nb }, (_, i) => ({ i, l: 0, s: 0, nl: 0, ns: 0, from: t0 + i * bmin * 60000, mins: bmin }));
    for (const q of data) {
      if (q.ts < t0) break;
      if (highlight && q.pair !== highlight) continue;
      const b = buckets[Math.min(nb - 1, Math.floor((q.ts - t0) / (bmin * 60000)))];
      if (q.side === 'long') { b.l += q.notional; b.nl++; } else { b.s += q.notional; b.ns++; }
    }
    const bmax = Math.max(1, ...buckets.map((b) => Math.max(b.l, b.s)));
    const mid = padT + plotH + 8 + stripH / 2;
    geom.mid = mid; geom.bw = bw;
    ctx.strokeStyle = C.grid; ctx.beginPath(); ctx.moveTo(padL, mid); ctx.lineTo(w - padR, mid); ctx.stroke();
    let hoverBucket = null;
    if (mouse && mouse.y > padT + plotH + 4 && mouse.x >= padL) hoverBucket = buckets[Math.min(nb - 1, Math.floor((mouse.x - padL) / bw))];
    for (const b of buckets) {
      const x = padL + b.i * bw + 1, su = (b.s / bmax) * (stripH / 2 - 1), lu = (b.l / bmax) * (stripH / 2 - 1);
      const a = hoverBucket && hoverBucket !== b ? 0.35 : 0.8;
      ctx.fillStyle = hexA(C.green, a); ctx.fillRect(x, mid - su, Math.max(1, bw - 2), su);
      ctx.fillStyle = hexA(C.red, a); ctx.fillRect(x, mid, Math.max(1, bw - 2), lu);
    }
    ctx.textAlign = 'right'; ctx.fillStyle = C.dim2; ctx.fillText(bmin + 'm', padL - 6, mid);

    // bubbles
    const cl = cluster(data, now);
    points = cl.map((c) => ({ ...c, x: X(c.ts), y: Y(c.notional), r: Math.min(22, 2 + Math.sqrt(c.notional) / 28) }));
    hoverPt = null;
    if (mouse && mouse.y <= padT + plotH + 4) {
      let bd = Infinity;
      for (const p of points) {
        const d = Math.hypot(p.x - mouse.x, p.y - mouse.y);
        if (d < p.r + 6 && d < bd) { bd = d; hoverPt = p; }
      }
    }
    const focus = hoverPt ? hoverPt.pair : highlight;
    for (const p of points) {
      const col = p.side === 'long' ? C.red : C.green;
      const dim = focus && p.pair !== focus;
      const age = (now - p.ts) / 1000;
      ctx.globalAlpha = dim ? 0.1 : 0.5 + 0.4 * Math.max(0, 1 - (now - p.ts) / span);
      ctx.fillStyle = col;
      if (!dim && p.notional >= 1e5) { ctx.shadowColor = col; ctx.shadowBlur = 12; } else ctx.shadowBlur = 0;
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;
      if (!dim && (p.pair === sel || p === hoverPt)) {
        ctx.globalAlpha = 1; ctx.strokeStyle = p === hoverPt ? C.white : C.cyan; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r + 2.5, 0, Math.PI * 2); ctx.stroke(); ctx.lineWidth = 1;
      }
      if (!dim && age < 4) {
        ctx.globalAlpha = 1 - age / 4; ctx.strokeStyle = col; ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.arc(p.x, p.y, p.r + age * 6, 0, Math.PI * 2); ctx.stroke(); ctx.lineWidth = 1;
      }
    }
    ctx.globalAlpha = 1;

    // labels for the big ones, largest first, skipping overlaps
    const placed = [];
    ctx.textAlign = 'left'; ctx.font = 'bold ' + FONT;
    for (const p of points.slice().reverse()) {
      if (p.notional < 5e4 || (focus && p.pair !== focus)) continue;
      const txt = `${F.base(p.pair)} ${F.usd(p.notional, 1)}`;
      const tw = ctx.measureText(txt).width;
      let x = p.x + p.r + 4;
      if (x + tw > w - padR) x = p.x - p.r - 4 - tw;
      const box = { x, y: p.y - 7, w: tw, h: 14 };
      if (placed.some((b) => !(box.x > b.x + b.w || box.x + box.w < b.x || box.y > b.y + b.h || box.y + box.h < b.y))) continue;
      placed.push(box);
      ctx.fillStyle = 'rgba(5,10,22,.75)'; ctx.fillRect(box.x - 2, box.y, box.w + 4, box.h);
      ctx.fillStyle = p.side === 'long' ? '#ff8aa0' : '#7ff0c6'; ctx.fillText(txt, box.x, p.y);
      if (placed.length >= 10) break;
    }
    ctx.font = FONT;

    // crosshair + tooltip
    if (mouse && mouse.x >= padL && mouse.x <= w - padR) {
      ctx.strokeStyle = 'rgba(238,244,255,.25)'; ctx.setLineDash([3, 3]);
      ctx.beginPath(); ctx.moveTo(mouse.x, padT); ctx.lineTo(mouse.x, padT + plotH + stripH + 8); ctx.stroke(); ctx.setLineDash([]);
      const tsAt = t0 + ((mouse.x - padL) / plotW) * span;
      const lab = F.hms(tsAt), lw = ctx.measureText(lab).width + 8;
      ctx.fillStyle = C.cyan; ctx.fillRect(mouse.x - lw / 2, h - axisH, lw, axisH);
      ctx.fillStyle = '#04121c'; ctx.textAlign = 'center'; ctx.fillText(lab, mouse.x, h - axisH / 2); ctx.textAlign = 'left';
    }
    if (hoverPt) {
      const p = hoverPt, side = t(p.side === 'long' ? 'fn.liq.long' : 'fn.liq.short');
      cv.style.cursor = 'pointer';
      showTip(`<div class="tt-h">${F.esc(F.base(p.pair))} <span class="${p.side === 'long' ? 'dn' : 'up'}">${F.esc(side)}</span></div>` +
        `<div class="tt-r"><span>${F.esc(t('lq.tt.total'))}</span><b>${F.usd(p.notional)}</b></div>` +
        `<div class="tt-r"><span>${F.esc(t('lq.tt.orders'))}</span><b>${p.n}</b></div>` +
        `<div class="tt-r"><span>${F.esc(t('lq.tt.px'))}</span><b>${p.lo === p.hi ? F.price(p.lo) : F.price(p.lo) + ' – ' + F.price(p.hi)}</b></div>` +
        `<div class="tt-r"><span>${F.esc(t('lq.tt.time'))}</span><b>${p.n > 1 ? F.hms(p.t1) + ' – ' : ''}${F.hms(p.ts)}</b></div>` +
        `<div class="tt-f">${F.esc(t('lq.tt.click'))}</div>`, mouse.x, mouse.y);
    } else if (hoverBucket) {
      const b = hoverBucket;
      cv.style.cursor = '';
      showTip(`<div class="tt-h">${F.hms(b.from)} · ${b.mins}m</div>` +
        `<div class="tt-r"><span class="dn">${F.esc(t('fn.liq.long'))}</span><b>${F.usd(b.l)} · ${b.nl}</b></div>` +
        `<div class="tt-r"><span class="up">${F.esc(t('fn.liq.short'))}</span><b>${F.usd(b.s)} · ${b.ns}</b></div>`, mouse.x, mouse.y);
    } else {
      cv.style.cursor = '';
      tip.style.display = 'none';
    }
    if (!points.length) {
      ctx.fillStyle = C.dim; ctx.textAlign = 'center'; ctx.fillText(t('lq.empty'), padL + plotW / 2, padT + plotH / 2); ctx.textAlign = 'left';
    }
  }

  return { draw, setHighlight };
}
