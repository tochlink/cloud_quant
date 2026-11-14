// Pseudo-3D "vol cone": last 60 minutes of 1m closes run into a forward cone of
// ±1σ / ±2σ realised-volatility bands (30 min ahead). Liquidations on the
// selected contract drop through the funnel as sparks.
import { fitCanvas, C, hexA } from './charts.js';
import { price as fmtPrice, usd } from './fmt.js';

const FONT = '10px "JetBrains Mono", Menlo, Consolas, monospace';
const FZ = 0.42;   // half depth of the floor grid

export function createFunnel(cv) {
  const sparks = [];
  const fit = { key: '', S: 1, cx: 0, cy: 0 };

  function liq(p, notional, side) {
    sparks.push({ p, notional, side, t0: performance.now(), z: (Math.random() - 0.5) * 0.9 });
    if (sparks.length > 40) sparks.shift();
  }

  /** data: { closes:[{t,c}] (oldest→newest, ≤60), last, sigma1m, labels:{now, wait}, reserveTop (px kept free for the overlay list) } */
  function draw(now, data) {
    const { ctx, w, h } = fitCanvas(cv);
    ctx.font = FONT;
    if (!data.last || data.closes.length < 5 || !(data.sigma1m > 0)) {
      ctx.fillStyle = C.dim; ctx.textAlign = 'center'; ctx.fillText(data.labels.wait, w / 2, h / 2); ctx.textAlign = 'left';
      return;
    }
    const yaw = -0.62 + 0.12 * Math.sin(now / 5200), pitch = 0.3 + 0.05 * Math.sin(now / 7300);
    const cyw = Math.cos(yaw), syw = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
    const D = 4.2;
    // unit projection (scale 1, origin 0); the scene is then fitted to the canvas
    const U = (x, y, z, cyw_ = cyw, syw_ = syw, cp_ = cp, sp_ = sp) => {
      const X = x - 0.1;
      const x1 = X * cyw_ - z * syw_, z1 = X * syw_ + z * cyw_;
      const y1 = y * cp_ - z1 * sp_, z2 = y * sp_ + z1 * cp_;
      const f = D / (D + z2);
      return [x1 * f, -y1 * f * 0.9];
    };
    // QTW: fit the whole scene (floor grid, history, ±2σ cone, labels) into the canvas.
    // The old fixed scale left most of a tall / wide panel empty and pushed the cone
    // to one side. The box is computed at the mean camera angle so it does not breathe.
    const top = Math.max(8, data.reserveTop || 0);
    const fitKey = w + 'x' + h + 'x' + top;
    if (fit.key !== fitKey) {
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      // what is actually visible: history wall (z = 0), the forward cone (|r| ≤ 0.72),
      // the floor under them, at both ends of the camera sway
      const pts = [];
      for (const x of [-1.25, -0.6, 0]) for (const y of [-0.95, 0.72]) pts.push([x, y, 0]);
      for (const x of [0.3, 0.95]) for (let i = 0; i < 12; i++) { const a = (i / 12) * Math.PI * 2; pts.push([x, Math.cos(a) * 0.72 * x, Math.sin(a) * 0.65 * x]); }
      for (const x of [-1.3, 1.0]) for (const z of [-FZ, FZ]) pts.push([x, -0.95, z]);
      for (const sw of [-1, 1]) {
        const yw = -0.62 + 0.12 * sw, pt = 0.3 + 0.05 * sw;
        for (const [px, py, pz] of pts) {
          const [u, v] = U(px, py, pz, Math.cos(yw), Math.sin(yw), Math.cos(pt), Math.sin(pt));
          x0 = Math.min(x0, u); x1 = Math.max(x1, u); y0 = Math.min(y0, v); y1 = Math.max(y1, v);
        }
      }
      const padL = 14, padR = 96, padB = 22;   // right: ±1σ price labels, bottom: time axis
      const sc = Math.max(10, Math.min((w - padL - padR) / (x1 - x0), (h - top - padB) / (y1 - y0)));
      fit.key = fitKey; fit.S = sc;
      fit.cx = padL + ((w - padL - padR) - sc * (x1 - x0)) / 2 - sc * x0;
      fit.cy = top + ((h - top - padB) - sc * (y1 - y0)) / 2 - sc * y0;
    }
    const P = (x, y, z) => { const [u, v] = U(x, y, z); return [fit.cx + u * fit.S, fit.cy + v * fit.S]; };
    const last = data.last, sig = data.sigma1m;
    let dev = 0;
    for (const k of data.closes) dev = Math.max(dev, Math.abs(k.c / last - 1));
    const span = Math.max(dev * 1.15, 2.2 * sig * Math.sqrt(30), 0.0012);
    const Y = (p) => ((p / last - 1) / span) * 0.78;
    const XH = (minAgo) => -1.25 * (minAgo / 60);
    const XF = (minAhead) => 0.95 * (minAhead / 30);
    const floor = -0.95;
    const line = (pts, col, lw, dash) => {
      ctx.beginPath(); pts.forEach((q, i) => (i ? ctx.lineTo(q[0], q[1]) : ctx.moveTo(q[0], q[1])));
      ctx.strokeStyle = col; ctx.lineWidth = lw; ctx.setLineDash(dash || []); ctx.stroke(); ctx.setLineDash([]);
    };

    // floor grid
    for (let gx = -1.3; gx <= 1.01; gx += 0.1) line([P(gx, floor, -FZ), P(gx, floor, FZ)], 'rgba(60,90,150,.2)', 1);
    for (let gz = -FZ; gz <= FZ + 0.01; gz += FZ / 3) line([P(-1.3, floor, gz), P(1.0, floor, gz)], 'rgba(60,90,150,.2)', 1);

    // history with curtain
    const n = data.closes.length, nowT = data.closes[n - 1].t;
    const hist = data.closes.map((k) => [XH((nowT - k.t) / 60), Y(k.c)]);
    hist.push([0, 0]);
    hist.forEach(([x, y], i) => { if (i % 2 === 0) line([P(x, y, 0), P(x, floor, 0)], 'rgba(69,212,255,.07)', 1); });
    ctx.shadowColor = C.cyan; ctx.shadowBlur = 10;
    const hp = hist.map(([x, y]) => P(x, y, 0));
    const grad = ctx.createLinearGradient(hp[0][0], 0, hp[hp.length - 1][0], 0);
    grad.addColorStop(0, hexA(C.cyan, 0.15)); grad.addColorStop(1, hexA(C.green, 1));
    line(hp, grad, 1.8);
    ctx.shadowBlur = 0;

    // cone rings
    const ring = (mAhead, k, col, lw, dash) => {
      const x = XF(mAhead), r = Math.abs(Y(last * (1 + k * sig * Math.sqrt(mAhead))));
      const pts = [];
      for (let i = 0; i <= 48; i++) { const a = (i / 48) * Math.PI * 2; pts.push(P(x, Math.cos(a) * r, Math.sin(a) * r * 0.9)); }
      line(pts, col, lw, dash);
      return r;
    };
    for (let m = 3; m <= 30; m += 3) ring(m, 1, hexA(C.cyan, 0.08 + (m / 30) * 0.3), 1);
    ring(30, 2, hexA(C.violet, 0.45), 1, [3, 4]);
    ctx.shadowColor = C.cyan; ctx.shadowBlur = 12;
    const rEnd = ring(30, 1, hexA(C.cyan, 0.9), 1.6);
    ctx.shadowBlur = 0;
    // generatrices
    for (const a of [0, Math.PI / 2, Math.PI, Math.PI * 1.5]) {
      const pts = [];
      for (let m = 0; m <= 30; m += 2) { const r = Math.abs(Y(last * (1 + sig * Math.sqrt(m)))); pts.push(P(XF(m), Math.cos(a) * r, Math.sin(a) * r * 0.9)); }
      line(pts, hexA(C.cyan, 0.3), 1);
    }

    // liquidation sparks
    for (let i = sparks.length - 1; i >= 0; i--) {
      const s = sparks[i], age = (now - s.t0) / 4500;
      if (age >= 1) { sparks.splice(i, 1); continue; }
      const y0 = Math.max(-0.9, Math.min(0.9, Y(s.p)));
      const y = y0 - age * age * (y0 - floor);
      const q = P(age * 0.25, y, s.z), col = s.side === 'long' ? C.red : C.green;
      const rad = 2 + Math.min(7, Math.log10(Math.max(10, s.notional)) - 1);
      ctx.globalAlpha = 1 - age; ctx.fillStyle = col; ctx.shadowColor = col; ctx.shadowBlur = 12;
      ctx.beginPath(); ctx.arc(q[0], q[1], rad, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;
      if (age < 0.5) { ctx.fillStyle = col; ctx.fillText(usd(s.notional, 1), q[0] + rad + 3, q[1] - 2); }
      ctx.globalAlpha = 1;
    }

    // current price dot
    const c0 = P(0, 0, 0), pulse = 1 + 0.25 * Math.sin(now / 260);
    const g = ctx.createRadialGradient(c0[0], c0[1], 0, c0[0], c0[1], 20 * pulse);
    g.addColorStop(0, 'rgba(255,255,255,.95)'); g.addColorStop(0.25, hexA(C.green, 0.5)); g.addColorStop(1, hexA(C.green, 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(c0[0], c0[1], 20 * pulse, 0, Math.PI * 2); ctx.fill();

    // labels
    ctx.fillStyle = C.white; ctx.font = 'bold ' + FONT;
    ctx.fillText(fmtPrice(last), c0[0] - 20, c0[1] - 16);
    ctx.font = FONT;
    const up = P(XF(30), rEnd, 0), dn = P(XF(30), -rEnd, 0);
    ctx.fillStyle = C.cyan;
    ctx.fillText('+1σ ' + fmtPrice(last * (1 + sig * Math.sqrt(30))), up[0] + 6, up[1] - 4);
    ctx.fillText('−1σ ' + fmtPrice(last * (1 - sig * Math.sqrt(30))), dn[0] + 6, dn[1] + 12);
    ctx.fillStyle = C.dim2;
    const ax = (x, txt) => { const q = P(x, floor, FZ + 0.02); ctx.fillText(txt, q[0] - 12, q[1] + 12); };
    ax(XH(60), '-60m'); ax(XH(30), '-30m'); ax(0, data.labels.now); ax(XF(30), '+30m');

    // hover: nearest point of the price history
    const hv = cv._hover;
    if (!hv) return null;
    let bi = -1, bd = Infinity;
    hp.forEach((q, i) => { const d = Math.abs(q[0] - hv.x) + Math.abs(q[1] - hv.y) * 0.25; if (d < bd) { bd = d; bi = i; } });
    if (bi < 0 || bd > 60) return null;
    const q = hp[bi];
    ctx.strokeStyle = 'rgba(238,244,255,.35)'; ctx.setLineDash([3, 3]);
    ctx.beginPath(); ctx.moveTo(q[0], q[1]); ctx.lineTo(...P(hist[bi][0], floor, 0)); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = C.white; ctx.shadowColor = C.cyan; ctx.shadowBlur = 10;
    ctx.beginPath(); ctx.arc(q[0], q[1], 3.5, 0, Math.PI * 2); ctx.fill(); ctx.shadowBlur = 0;
    return bi < n ? { t: data.closes[bi].t * 1000, c: data.closes[bi].c, now: false } : { t: null, c: last, now: true };
  }

  return { draw, liq };
}
