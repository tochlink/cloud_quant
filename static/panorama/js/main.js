import { t, setLang, getLang, onLang, applyDom } from './i18n.js';
import { rest, GateWS, SPOT_WS, PERP_WS } from './gate.js';
import * as F from './fmt.js';
import { C, drawCandles, drawSpark, drawBars, drawBasis, drawFlow, drawDist } from './charts.js';
import { createLiqChart } from './liqchart.js';
import { createShell } from './shell3d.js';
import { createFunnel } from './funnel.js';
import { createPulse } from './pulse3d.js';
import { createHeatmap } from './heatmap.js';
import { createPicker } from './picker.js';
import { createTz } from './tz.js';
import { showTip, hideTip, tr, hoverable } from './tip.js';

const $ = (id) => document.getElementById(id);

// ---------------------------------------------------------------- config
const STABLE = new Set(['USDC', 'FDUSD', 'TUSD', 'DAI', 'USDE', 'PYUSD', 'USD1', 'BUSD', 'USDD', 'USDP', 'EUR', 'EURC',
  'EURT', 'EURI', 'GUSD', 'UST', 'USTC', 'USDJ', 'XAUT', 'PAXG', 'RLUSD', 'USDS', 'USDQ', 'USDR', 'FRAX', 'LUSD', 'SUSD',
  'USDX', 'USD0', 'USDG', 'BFUSD', 'USDF', 'USDB', 'USDTB', 'AUSD', 'SUSDE', 'CUSD', 'ZUSD', 'DUSD', 'GHO', 'CRVUSD', 'MIM']);
const LEVERAGED = /\d+[LS]$/;
const FOCUS_N = 40;     // coins on the shell (spot tickers via WS)
const TRADE_N = 16;     // coins whose spot trades are streamed
const PERP_N = 10;      // perps whose tickers + trades are streamed
// Whale fills use a per-coin, adaptive threshold: an order is a whale when it is
// in the coin's own top 0.5% of recent taker orders, at least 8× its median order,
// and above a small floor. Measured on Gate.io: the old fixed $10K / $50K bar
// only ever caught BTC / ETH; this spreads whales across all monitored coins.
const WHALE_Q = 0.995;
const WHALE_MEDX = 8;
const WHALE_FLOOR = { spot: 1_000, perp: 2_000 };
const WHALE_KEEP = 800;            // orders remembered per market + coin
const WHALE_AGE = 30 * 60_000;     // … and only from the last 30 minutes
const WHALE_MIN_N = 60;            // below this, estimate from 24h volume
const HEAT_N = 60;      // tiles on the heatmap
const PULSE_N = 64;     // bars on the header ring
const DIST_BINS = [
  [-Infinity, -20, '≤-20'], [-20, -10, '-20'], [-10, -5, '-10'], [-5, -2, '-5'], [-2, 0, '-2'],
  [0, 2, '0'], [2, 5, '+2'], [5, 10, '+5'], [10, 20, '+10'], [20, Infinity, '≥20'],
];
const INPUTS = [
  { kind: 'coin', sym: 'BTC_USDT', color: C.cyan },
  { kind: 'coin', sym: 'ETH_USDT', color: C.blue },
  { kind: 'coin', sym: 'SOL_USDT', color: C.violet },
  { kind: 'basis', color: C.amber },
  { kind: 'fund', color: C.green },
  { kind: 'lsr', color: C.pink },
];

// ---------------------------------------------------------------- state
const S = {
  sel: 'BTC_USDT',
  offset: 0,
  spotAll: new Map(),   // pair -> {pair, base, last, chg, qv, high, low}
  futAll: new Map(),    // contract -> {last, mark, index, funding, chg, oi, vol, q}
  focus: [],
  mk: null, fm: null,
  candles: [], book: null,
  fut: { next: 0, stats: [], fund: [] },
  tape: [], flow: [], whales: [], liqs: [], basis: [],
  whaleCount: 0, liqSeen: { long: 0, short: 0 },
  hist: new Array(60).fill(0), secTrades: 0,
  rate: new Map(), rateCur: new Map(),
  spark: new Map(),
  lat: { spot: NaN, fut: NaN },
  wire: [], frames: 0, framesPrev: 0, fps: 0,
  conn: { rest: '', spot: '', fut: '' },
  ver: { tape: 0, whales: 0, liqs: 0, dv: 0 },
  top: [], dist: [], median: NaN, dv: null, fundInterval: new Map(),
  liqAll: [], liqStats: null, // market-wide liquidations, newest first (last ~65 min)
  kv: { int: '1m', step: 6, offset: 0, maxOffset: 0 }, kl: [], // K-line view + candles for non-1m intervals
  wirePaused: false, bookHover: null, rtt: NaN,
};
let spotWS, futWS, shell, funnel, pulse, heat, picker, liqChart, tzSw, selToken = 0;
const inputs = [];

// ---------------------------------------------------------------- REST pollers
async function pollSpotAll() {
  try {
    const arr = await rest('/spot/tickers');
    S.conn.rest = 'open';
    let vol = 0, up = 0, dn = 0, n = 0, sum = 0, wsum = 0;
    const movers = [];
    for (const x of arr) {
      const pair = x.currency_pair;
      if (!pair.endsWith('_USDT')) continue;
      const b = pair.slice(0, -5), last = +x.last, qv = +x.quote_volume || 0, chg = +x.change_percentage || 0;
      const rec = S.spotAll.get(pair) || { pair, base: b };
      Object.assign(rec, { last, chg, qv, high: +x.high_24h, low: +x.low_24h });
      S.spotAll.set(pair, rec);
      if (STABLE.has(b) || LEVERAGED.test(b) || !last || !qv) continue;
      n++; vol += qv; sum += chg; wsum += chg * qv;
      if (chg > 0) up++; else if (chg < 0) dn++;
      if (qv >= 300_000) movers.push(rec);
    }
    movers.sort((a, b) => b.chg - a.chg);
    S.mk = { vol, up, dn, n, avg: sum / n, wavg: wsum / vol, gainers: movers.slice(0, 8), losers: movers.slice(-8).reverse() };
    const live = [...S.spotAll.values()].filter((r) => !STABLE.has(r.base) && !LEVERAGED.test(r.base) && r.last > 0 && r.qv > 0);
    S.dist = DIST_BINS.map(([lo, hi, label], i) => {
      const inBin = live.filter((r) => (i === 4 ? r.chg > -2 && r.chg < 0 : (r.chg > lo && r.chg <= hi) || (lo === 0 && r.chg === 0)));
      return { label, lo, hi, sign: lo >= 0 ? 1 : -1, n: inBin.length, top: inBin.sort((a, b) => b.qv - a.qv).slice(0, 5) };
    });
    const chgs = live.map((r) => r.chg).sort((a, b) => a - b);
    const mid = chgs.length >> 1;
    S.median = !chgs.length ? NaN : chgs.length % 2 ? chgs[mid] : (chgs[mid - 1] + chgs[mid]) / 2;
    S.top = live.sort((a, b) => b.qv - a.qv);
    pulse && pulse.setData(S.top.slice(0, PULSE_N).map((r) => ({ sym: r.pair, label: r.base, chg: r.chg })), up / Math.max(1, up + dn));
    heat && heat.setData(S.top.slice(0, HEAT_N).map((r) => ({ sym: r.pair, rec: r })));
    if (S.focus.length) shell && shell.setClusters(clusterList());
  } catch (e) {
    S.conn.rest = 'closed';
  }
}

async function pollFutAll() {
  try {
    const arr = await rest('/futures/usdt/tickers');
    S.conn.rest = 'open';
    let oi = 0, vol = 0, fw = 0;
    for (const x of arr) {
      const q = +x.quanto_multiplier || 0, mark = +x.mark_price;
      const rec = S.futAll.get(x.contract) || { contract: x.contract };
      Object.assign(rec, {
        q, last: +x.last, mark, index: +x.index_price, funding: +x.funding_rate,
        chg: +x.change_percentage, size: +x.total_size, oi: (+x.total_size) * q * mark, vol: +x.volume_24h_quote || 0,
      });
      S.futAll.set(x.contract, rec);
      if (Number.isFinite(rec.oi)) { oi += rec.oi; fw += rec.funding * rec.oi; }
      vol += rec.vol;
    }
    S.fm = { oi, vol, funding: oi ? fw / oi : NaN, n: arr.length };
    const recs = [...S.futAll.values()].filter((r) => Number.isFinite(r.oi) && Number.isFinite(r.funding));
    const liquid = recs.filter((r) => r.oi >= 1_000_000);
    S.dv = {
      oiTop: liquid.slice().sort((a, b) => b.oi - a.oi).slice(0, 12),
      fHi: liquid.slice().sort((a, b) => b.funding - a.funding).slice(0, 6),
      fLo: liquid.slice().sort((a, b) => a.funding - b.funding).slice(0, 6),
      pos: recs.filter((r) => r.funding > 0).length,
      neg: recs.filter((r) => r.funding < 0).length,
    };
    S.ver.dv++;
  } catch (e) {
    S.conn.rest = 'closed';
  }
}

async function pollSelPerp(token) {
  const sym = S.sel;
  if (!S.futAll.has(sym)) return;
  try {
    const [stats, contract] = await Promise.all([
      rest('/futures/usdt/contract_stats', { contract: sym, interval: '5m', limit: 24 }),
      rest('/futures/usdt/contracts/' + sym),
    ]);
    if (token !== selToken) return;
    S.fut.stats = stats.sort((a, b) => a.time - b.time);
    S.fut.next = +contract.funding_next_apply || 0;
  } catch (e) { /* keep previous */ }
}

async function pollFunding(token) {
  const sym = S.sel;
  if (!S.futAll.has(sym)) return;
  try {
    const arr = await rest('/futures/usdt/funding_rate', { contract: sym, limit: 30 });
    if (token !== selToken) return;
    S.fut.fund = arr.map((x) => ({ t: x.t, r: +x.r })).sort((a, b) => a.t - b.t);
  } catch (e) { /* ignore */ }
}

// ---------------------------------------------------------------- focus / shell
function computeFocus() {
  const list = [...S.spotAll.values()]
    .filter((r) => !STABLE.has(r.base) && !LEVERAGED.test(r.base) && r.qv > 0 && r.last > 0)
    .sort((a, b) => b.qv - a.qv)
    .map((r) => r.pair);
  const focus = list.slice(0, FOCUS_N);
  for (const c of INPUTS) if (c.sym && S.spotAll.has(c.sym) && !focus.includes(c.sym)) focus.splice(focus.length - 1, 1, c.sym);
  S.focus = focus;
}

function clusterList() {
  const recs = S.focus.map((p) => S.spotAll.get(p)).filter(Boolean);
  const lv = recs.map((r) => Math.log10(Math.max(1, r.qv)));
  const lo = Math.min(...lv), hi = Math.max(...lv);
  return recs.map((r, i) => ({ sym: r.pair, chg: r.chg, last: r.last, qv: r.qv, volNorm: hi > lo ? (lv[i] - lo) / (hi - lo) : 1 }));
}

// ---------------------------------------------------------------- websockets
function connectWS() {
  spotWS = new GateWS(SPOT_WS, 'spot', { onMessage: onSpot, onStatus: (s) => { S.conn.spot = s; sysWire('spot', s); } });
  futWS = new GateWS(PERP_WS, 'futures', { onMessage: onFut, onStatus: (s) => { S.conn.fut = s; sysWire('fut', s); } });
  S.focus.forEach((p) => spotWS.subscribe('spot.tickers', [p]));
  S.focus.slice(0, TRADE_N).forEach((p) => spotWS.subscribe('spot.trades', [p]));
  S.focus.filter((p) => S.futAll.has(p)).slice(0, PERP_N).forEach((p) => {
    futWS.subscribe('futures.tickers', [p]);
    futWS.subscribe('futures.trades', [p]);
  });
  futWS.subscribe('futures.public_liquidates', ['!all']);
  spotWS.connect();
  futWS.connect();
}

function selSubs(sym, on) {
  const fn = on ? 'subscribe' : 'unsubscribe';
  spotWS[fn]('spot.tickers', [sym]);
  spotWS[fn]('spot.trades', [sym]);
  spotWS[fn]('spot.order_book', [sym, '20', '100ms']);
  spotWS[fn]('spot.candlesticks', ['1m', sym]);
  if (S.kv.int !== '1m') spotWS[fn]('spot.candlesticks', [S.kv.int, sym]);
  if (S.futAll.has(sym)) {
    futWS[fn]('futures.tickers', [sym]);
    futWS[fn]('futures.trades', [sym]);
  }
}

async function selectSymbol(sym) {
  if (!sym || !S.spotAll.has(sym)) return;
  if (spotWS && S.sel && S.sel !== sym) selSubs(S.sel, false);
  const changed = S.sel !== sym || !S.candles.length;
  S.sel = sym;
  const token = ++selToken;
  if (changed) {
    S.candles = []; S.kl = []; S.kv.offset = 0; S.book = null; S.tape = []; S.flow = []; S.basis = [];
    S.fut = { next: 0, stats: [], fund: [] };
    S.ver.tape++;
  }
  selSubs(sym, true);
  document.querySelectorAll('.sym-name').forEach((el) => { el.textContent = F.base(sym); });
  shell && shell.setSelected(sym);
  heat && heat.setSelected(sym);
  try {
    if (S.kv.int !== '1m') loadKline(sym, S.kv.int, token);
    const raw = await rest('/spot/candlesticks', { currency_pair: sym, interval: '1m', limit: 400 });
    if (token !== selToken) return;
    const fromRest = raw.map((a) => ({ t: +a[0], v: +a[1], c: +a[2], h: +a[3], l: +a[4], o: +a[5] }));
    // keep any live candle that arrived over WS while REST was in flight
    const live = S.candles.filter((k) => k.t > fromRest[fromRest.length - 1].t);
    S.candles = fromRest.concat(live);
  } catch (e) { /* WS will fill in */ }
  pollSelPerp(token);
  pollFunding(token);
}

// Push latency = local receive time (server-clock corrected) − server push time.
// Only trade / book channels are used: Gate batches ticker pushes (~0.5 s).
const LAT_CH = /\.(trades|order_book|book_ticker)$/;
const latBuf = { spot: [], fut: [] };
const skew = []; // server push time − local receive time
function latency(kind, m) {
  if (!m.time_ms || m.event !== 'update' || !LAT_CH.test(m.channel)) return;
  const now = Date.now();
  skew.push(m.time_ms - now);
  if (skew.length > 300) skew.shift();
  const b = latBuf[kind];
  b.push(now + S.offset - m.time_ms);
  if (b.length > 61) b.shift();
  const sorted = b.slice().sort((x, y) => x - y);
  S.lat[kind] = sorted[sorted.length >> 1];
}

// The one-off /spot/time calibration can fail or be skewed by a slow proxy, and
// some machines' clocks are hours off. Every frame carries the server push time,
// so max(time_ms − now) ≈ true offset − fastest latency: if that disagrees with
// the current offset by more than 2 s, trust it instead.
// NTP-style sync against /spot/time: the sample with the shortest round trip wins;
// error is at most half that round trip. A healthy local clock is left alone.
async function syncClock() {
  let best = null;
  for (let i = 0; i < 3; i++) {
    try {
      const t0 = Date.now(), r = await rest('/spot/time'), t1 = Date.now();
      if (!best || t1 - t0 < best.rtt) best = { rtt: t1 - t0, off: r.server_time - (t0 + t1) / 2 };
    } catch (e) { /* try again */ }
  }
  if (!best) return;
  S.rtt = best.rtt;
  const off = Math.abs(best.off) > Math.max(500, best.rtt) ? best.off : 0;
  if (Math.abs(off - S.offset) > 250) { S.offset = off; latBuf.spot.length = 0; latBuf.fut.length = 0; }
}

function calibrateClock() {
  if (skew.length < 30) return;
  let best = -Infinity;
  for (const v of skew) if (v > best) best = v;
  // max(skew) = true offset − fastest one-way latency; add back an estimate of that latency
  best += Number.isFinite(S.rtt) ? S.rtt / 2 : 60;
  if (Math.abs(best - S.offset) > 2000) {
    S.offset = best;
    latBuf.spot.length = 0; latBuf.fut.length = 0;
    S.lat.spot = NaN; S.lat.fut = NaN;
  }
}

function onSpot(m) {
  S.frames++;
  latency('spot', m);
  wireLog('spot', m);
  const r = m.result;
  if (m.event !== 'update' || !r) return;
  switch (m.channel) {
    case 'spot.tickers': {
      const rec = S.spotAll.get(r.currency_pair);
      if (!rec) return;
      Object.assign(rec, { last: +r.last, chg: +r.change_percentage, qv: +r.quote_volume, high: +r.high_24h, low: +r.low_24h });
      shell && shell.updateTicker(r.currency_pair, rec.chg, rec.last);
      pulse && pulse.update(r.currency_pair, rec.chg);
      break;
    }
    case 'spot.trades':
      onTrade('spot', r.currency_pair, r.side, +r.price, +r.amount, +r.create_time_ms);
      break;
    case 'spot.order_book':
      if (r.s === S.sel) S.book = { bids: r.bids.map((x) => [+x[0], +x[1]]), asks: r.asks.map((x) => [+x[0], +x[1]]) };
      break;
    case 'spot.candlesticks': {
      const cut = r.n.indexOf('_'), int = r.n.slice(0, cut), pair = r.n.slice(cut + 1);
      if (pair !== S.sel) return;
      const k = { t: +r.t, o: +r.o, h: +r.h, l: +r.l, c: +r.c, v: +r.v };
      if (int === '1m') pushCandle(S.candles, k);
      if (int === S.kv.int && int !== '1m') pushCandle(S.kl, k);
      break;
    }
  }
}

function pushCandle(arr, k) {
  const lastK = arr[arr.length - 1];
  if (lastK && lastK.t === k.t) arr[arr.length - 1] = k;
  else if (!lastK || k.t > lastK.t) { arr.push(k); if (arr.length > 600) arr.shift(); }
}

// ---------------------------------------------------------------- K-line interval / zoom / pan
const chartCandles = () => (S.kv.int === '1m' ? S.candles : S.kl);
async function loadKline(sym, int, token) {
  try {
    const raw = await rest('/spot/candlesticks', { currency_pair: sym, interval: int, limit: 400 });
    if (token !== selToken || int !== S.kv.int) return;
    const rows = raw.map((a) => ({ t: +a[0], v: +a[1], c: +a[2], h: +a[3], l: +a[4], o: +a[5] }));
    const live = S.kl.filter((k) => k.t > rows[rows.length - 1].t);
    S.kl = rows.concat(live);
  } catch (e) { /* WS fills in */ }
}
function setKlInt(int) {
  if (int === S.kv.int) return;
  const old = S.kv.int;
  if (spotWS && old !== '1m') spotWS.unsubscribe('spot.candlesticks', [old, S.sel]);
  S.kv.int = int; S.kv.offset = 0; S.kl = [];
  if (int !== '1m') { spotWS && spotWS.subscribe('spot.candlesticks', [int, S.sel]); loadKline(S.sel, int, selToken); }
  document.querySelectorAll('#kl-int button').forEach((b) => b.classList.toggle('on', b.dataset.v === int));
  renderSpot();
}
function initKlineControls() {
  const cv = $('cv-candles');
  $('kl-int').addEventListener('click', (e) => { const b = e.target.closest('button[data-v]'); if (b) setKlInt(b.dataset.v); });
  hoverable(cv, renderSpot);
  cv.addEventListener('wheel', (e) => {
    e.preventDefault();
    S.kv.step = Math.max(2, Math.min(24, S.kv.step * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
    renderSpot();
  }, { passive: false });
  let drag = null;
  cv.addEventListener('pointerdown', (e) => { drag = { x: e.clientX, off: S.kv.offset }; cv.setPointerCapture(e.pointerId); cv.classList.add('drag'); });
  cv.addEventListener('pointermove', (e) => {
    if (!drag) return;
    S.kv.offset = Math.max(0, Math.min(S.kv.maxOffset, drag.off + (e.clientX - drag.x) / S.kv.step));
    renderSpot();
  });
  const end = () => { drag = null; cv.classList.remove('drag'); };
  cv.addEventListener('pointerup', end);
  cv.addEventListener('pointercancel', end);
  cv.addEventListener('dblclick', () => { S.kv.offset = 0; S.kv.step = 6; renderSpot(); });
}
function whaleRuleTip() {
  const spot = S.focus.slice(0, TRADE_N), perp = S.focus.filter((p) => S.futAll.has(p)).slice(0, PERP_N);
  const coins = [...new Set([...spot, ...perp])];
  const cell = (mkt, list, p) => {
    if (!list.includes(p)) return '<span class="dim">—</span>';
    const w = whaleTh(mkt, p);
    return `<span class="${w.est ? 'est' : ''}">${F.usd(w.th, w.th < 1e4 ? 0 : 1)}</span>`;
  };
  return `<div class="tt-h">${F.esc(t('wh.rule.h'))}</div>` +
    `<ul class="tt-list"><li>${F.esc(t('wh.rule.1'))}</li><li>${F.esc(t('wh.rule.2'))}</li><li>${F.esc(t('wh.cover', { s: spot.length, p: perp.length }))}</li></ul>` +
    `<div class="tt-grid3"><span>${F.esc(t('pk.coin'))}</span><span>${F.esc(t('spot'))}</span><span>${F.esc(t('perp'))}</span>` +
    coins.map((p) => `<b>${F.esc(F.base(p))}</b>${cell('spot', spot, p)}${cell('perp', perp, p)}`).join('') +
    `</div><div class="tt-f"><span class="est">${F.esc(t('wh.rule.estk'))}</span> ${F.esc(t('wh.rule.est'))}</div>`;
}

function candleTip(k) {
  const chg = k.c - k.o, cls = F.cls(chg), d = F.priceDigits(k.o);
  return `<div class="tt-h">${F.esc(F.base(S.sel))} · ${S.kv.int.toUpperCase()} · ${F.dhm(k.t * 1000)}</div>` +
    tr(t('k.o'), F.price(k.o)) + tr(t('k.h'), F.price(k.h)) + tr(t('k.l'), F.price(k.l)) + tr(t('k.c'), F.price(k.c), cls) +
    tr(t('k.chg'), (chg > 0 ? '+' : '') + F.price(chg, d), cls) + tr(t('k.pct'), F.pct((chg / k.o) * 100), cls) +
    tr(t('k.amp'), (((k.h - k.l) / k.o) * 100).toFixed(2) + '%') + tr(t('k.vol'), F.usd(k.v));
}

function onFut(m) {
  S.frames++;
  latency('fut', m);
  wireLog('fut', m);
  const arr = m.result;
  if (m.event !== 'update' || !Array.isArray(arr)) return;
  switch (m.channel) {
    case 'futures.tickers':
      for (const x of arr) {
        const rec = S.futAll.get(x.contract) || { contract: x.contract, q: 0 };
        if (x.last) rec.last = +x.last;
        if (x.mark_price) rec.mark = +x.mark_price;
        if (x.index_price) rec.index = +x.index_price;
        if (x.funding_rate) rec.funding = +x.funding_rate;
        if (x.change_percentage) rec.chg = +x.change_percentage;
        if (x.total_size && rec.q) rec.oi = +x.total_size * rec.q * (rec.mark || rec.last);
        if (x.funding_interval) S.fundInterval.set(x.contract, +x.funding_interval);
        S.futAll.set(x.contract, rec);
        // QTW: the ticker push carries the next settlement time, so the countdown no
        // longer shows "—" for up to a minute after each settlement, and the funding
        // history is refetched exactly when a settlement happened (no 5-min poll).
        if (x.contract === S.sel && +x.funding_next_apply) {
          const nx = +x.funding_next_apply;
          if (S.fut.next && nx > S.fut.next) pollFunding(selToken);
          S.fut.next = nx;
        }
      }
      break;
    case 'futures.trades':
      for (const x of arr) {
        const q = S.futAll.get(x.contract)?.q || 0, size = +x.size;
        if (!q) continue;
        onTrade('perp', x.contract, size > 0 ? 'buy' : 'sell', +x.price, Math.abs(size) * q, +x.create_time_ms);
      }
      break;
    case 'futures.public_liquidates':
      for (const x of arr) {
        const q = S.futAll.get(x.contract)?.q || 0, size = +x.size, px = +x.price;
        const notional = Math.abs(size) * q * px;
        if (!notional) continue;
        // a negative order size is a forced sell, i.e. a long position being liquidated
        const side = size < 0 ? 'long' : 'short';
        S.liqSeen[side] += notional;
        // WS `time` is in ms; `price` equals REST order_price (checked against /liq_orders)
        addLiq({ ts: +x.time, pair: x.contract, side, px, notional, sz: Math.abs(size) });
        if (x.contract === S.sel) funnel && funnel.liq(px, notional, side);
        shell && shell.pulse(x.contract, Math.min(1.2, 0.3 + Math.log10(Math.max(1, notional)) / 8));
      }
      break;
  }
}

// ---------------------------------------------------------------- liquidations
function addLiq(q) {
  S.liqAll.unshift(q);
  const cut = Date.now() + S.offset - 65 * 60000;
  while (S.liqAll.length && (S.liqAll.length > 4000 || S.liqAll[S.liqAll.length - 1].ts < cut)) S.liqAll.pop();
  S.ver.liqs++;
}

// The live channel only pushes new events, so a quiet market would show an
// empty panel; seed the last ~hour from REST (newest 1000 orders) first.
async function seedLiqs() {
  try {
    const arr = await rest('/futures/usdt/liq_orders', { limit: 1000 });
    // REST `time` is whole seconds while the live push is in ms, so a liquidation that
    // arrived over WS while this request was in flight used to be counted twice.
    // De-duplicate on contract + second + size, and use order_price (the price the
    // live channel reports) so seeded and live bubbles are on the same basis.
    const key = (pair, ts, sz) => pair + '|' + Math.floor(ts / 1000) + '|' + sz;
    const live = new Set(S.liqAll.map((q) => key(q.pair, q.ts, q.sz)));
    const seeded = [];
    for (const x of arr) {
      const q = S.futAll.get(x.contract)?.q || 0, px = +x.order_price || +x.fill_price;
      const sz = Math.abs(+x.order_size || +x.size), notional = sz * q * px;
      if (!notional) continue;
      const ts = x.time * 1000;
      if (live.has(key(x.contract, ts, sz))) continue;
      // order_size < 0 is the forced sell that closes a long
      seeded.push({ ts, pair: x.contract, side: +x.order_size < 0 ? 'long' : 'short', px, notional, sz });
    }
    S.liqAll = S.liqAll.concat(seeded).sort((a, b) => b.ts - a.ts);
    S.ver.liqs++;
  } catch (e) { /* live feed only */ }
}

function liqStats() {
  const cut = Date.now() + S.offset - 3600000;
  let long = 0, short = 0, nl = 0, ns = 0, max = null;
  const by = new Map();
  for (const q of S.liqAll) {
    if (q.ts < cut) break;
    if (q.side === 'long') { long += q.notional; nl++; } else { short += q.notional; ns++; }
    if (!max || q.notional > max.notional) max = q;
    const b = by.get(q.pair) || { pair: q.pair, l: 0, s: 0 };
    if (q.side === 'long') b.l += q.notional; else b.s += q.notional;
    by.set(q.pair, b);
  }
  const top = [...by.values()].sort((a, b) => b.l + b.s - (a.l + a.s)).slice(0, 8);
  S.liqStats = { long, short, nl, ns, max, top };
}

function onTrade(mkt, pair, side, price, amount, ts) {
  const notional = price * amount;
  if (!Number.isFinite(notional)) return;
  S.secTrades++;
  S.rateCur.set(pair, (S.rateCur.get(pair) || 0) + 1);
  if (pair === S.sel) {
    S.tape.unshift({ ts, mkt, side, price, amount, notional });
    if (S.tape.length > 40) S.tape.length = 40;
    S.flow.push({ ts: Date.now(), side, notional });
    S.ver.tape++;
  }
  // Gate reports every maker fill separately; fills of one taker order share
  // symbol, side and timestamp, so merge them before testing the whale threshold.
  const key = mkt + '|' + pair + '|' + side + '|' + Math.floor(ts);
  const agg = pending.get(key);
  if (agg) { agg.notional += notional; agg.amount += amount; agg.price = price; }
  else pending.set(key, { mkt, pair, side, price, amount, notional, ts });
  const k = notional / whaleTh(mkt, pair).th;
  shell && shell.pulse(pair, Math.min(0.25, 0.03 + k * 0.3));
  heat && heat.flash(pair, Math.min(0.5, 0.05 + k * 0.4));
}

// ---------------------------------------------------------------- adaptive whale thresholds
const orderStats = new Map(); // 'spot|BTC_USDT' -> { v: [notional], t: [ms], th, med, n, at, dirty }
function recordOrder(mkt, pair, notional) {
  const key = mkt + '|' + pair;
  let s = orderStats.get(key);
  if (!s) { s = { v: [], t: [], th: 0, med: 0, n: 0, at: 0, dirty: true }; orderStats.set(key, s); }
  s.v.push(notional); s.t.push(Date.now());
  const cut = Date.now() - WHALE_AGE;
  while (s.v.length > WHALE_KEEP || (s.t.length && s.t[0] < cut)) { s.v.shift(); s.t.shift(); }
  s.dirty = true;
}
/** {th, med, n, est} for a market + coin; recomputed at most once a second */
function whaleTh(mkt, pair) {
  const key = mkt + '|' + pair, floor = WHALE_FLOOR[mkt];
  const s = orderStats.get(key);
  if (s && s.v.length >= WHALE_MIN_N) {
    if (s.dirty && Date.now() - s.at > 1000) {
      const a = s.v.slice().sort((x, y) => x - y);
      s.med = a[a.length >> 1];
      s.th = Math.max(floor, a[Math.min(a.length - 1, Math.floor(a.length * WHALE_Q))], s.med * WHALE_MEDX);
      s.n = a.length; s.at = Date.now(); s.dirty = false;
    }
    return { th: s.th, med: s.med, n: s.n, est: false };
  }
  // warm-up (slow coins take minutes to collect samples): be conservative —
  // 2× the floor, ~3 s of the coin's average 24h flow, and 10× the running median
  const vol = mkt === 'spot' ? S.spotAll.get(pair)?.qv : S.futAll.get(pair)?.vol;
  let med = 0;
  if (s && s.v.length >= 10) { const a = s.v.slice().sort((x, y) => x - y); med = a[a.length >> 1]; }
  return { th: Math.max(floor * 2, ((vol || 0) / 86400) * 3, med * 10), med, n: s ? s.v.length : 0, est: true };
}

const pending = new Map();
function flushOrders() {
  for (const o of pending.values()) {
    const w = whaleTh(o.mkt, o.pair), th = w.th;
    recordOrder(o.mkt, o.pair, o.notional);
    if (o.notional < th) continue;
    S.whaleCount++;
    S.whales.unshift({ id: S.whaleCount, ...o, th, med: w.med });
    if (S.whales.length > 14) S.whales.length = 14;
    S.ver.whales++;
    shell && shell.pulse(o.pair, Math.min(1.4, 0.6 + Math.log10(o.notional / th)));
    heat && heat.flash(o.pair, 1);
    pulse && pulse.bump(o.pair, Math.min(1.5, 0.6 + Math.log10(o.notional / th)));
  }
  pending.clear();
}

// ---------------------------------------------------------------- wire inspector
function sysWire(kind, status) {
  pushWire({ ts: Date.now(), cls: 'ch-sys', ch: kind === 'spot' ? 'spot.ws' : 'futures.ws', txt: status });
}
function pushWire(e) {
  S.wire.unshift(e);
  if (S.wire.length > 60) S.wire.length = 60;
}
function wireLog(kind, m) {
  const ch = m.channel || '';
  const r = m.result;
  let txt = '', cls = kind === 'spot' ? 'ch-spot' : 'ch-fut', hl = false;
  if (m.event === 'subscribe' || m.event === 'unsubscribe') txt = `${m.event} ${JSON.stringify(m.payload || '')} → ${r?.status || m.error?.message || ''}`;
  else if (ch.endsWith('.pong')) txt = 'pong';
  else if (m.event !== 'update' || !r) return;
  else if (ch === 'spot.trades') txt = `${r.currency_pair} ${r.side.toUpperCase()} ${r.amount} @ ${r.price}`;
  else if (ch === 'spot.tickers') txt = `${r.currency_pair} ${r.last} ${F.pct(+r.change_percentage)}`;
  else if (ch === 'spot.order_book') txt = `${r.s} bid ${r.bids[0]?.[0]} / ask ${r.asks[0]?.[0]} · L${r.bids.length}`;
  else if (ch === 'spot.candlesticks') txt = `${r.n} o${r.o} h${r.h} l${r.l} c${r.c}`;
  else if (ch === 'futures.trades') { const x = r[0]; txt = `${x.contract} ${x.size > 0 ? 'BUY' : 'SELL'} ${Math.abs(x.size)}c @ ${x.price}`; }
  else if (ch === 'futures.tickers') { const x = r[0]; txt = `${x.contract} mark ${x.mark_price} fr ${x.funding_rate}`; }
  else if (ch === 'futures.public_liquidates') { const x = r[0]; txt = `${x.contract} LIQ ${x.size} @ ${x.price}`; cls = 'ch-liq'; hl = true; }
  else txt = JSON.stringify(r).slice(0, 80);
  pushWire({ ts: m.time_ms || Date.now(), cls, ch, txt, hl });
}

// ---------------------------------------------------------------- per-second sampling
function perSecond() {
  S.hist.push(S.secTrades); S.hist.shift(); S.secTrades = 0;
  S.rate = S.rateCur; S.rateCur = new Map();
  S.fps = S.frames - S.framesPrev; S.framesPrev = S.frames;
  for (const c of INPUTS) {
    if (!c.sym) continue;
    const rec = S.spotAll.get(c.sym);
    if (!rec) continue;
    const arr = S.spark.get(c.sym) || [];
    arr.push(rec.last); if (arr.length > 90) arr.shift();
    S.spark.set(c.sym, arr);
  }
  const sp = S.spotAll.get(S.sel)?.last, fu = S.futAll.get(S.sel);
  if (sp) {
    S.basis.push({
      ts: Date.now() + S.offset,
      bps: fu && fu.last ? ((fu.last - sp) / sp) * 1e4 : NaN,
      prem: fu && fu.index ? ((fu.mark - fu.index) / fu.index) * 1e4 : NaN,
      latS: S.lat.spot, latF: S.lat.fut,
    });
    if (S.basis.length > 150) S.basis.shift();
  }
  const cut = Date.now() - 60000;
  while (S.flow.length && S.flow[0].ts < cut) S.flow.shift();
  $('clock').textContent = F.hms(Date.now() + S.offset);
}

// ---------------------------------------------------------------- rendering
// replace innerHTML only when it actually changed (keeps hover state stable)
function setHtml(id, html) {
  const el = $(id);
  if (el && el._html !== html) { el._html = html; el.innerHTML = html; }
}

function setText(id, txt, cl) {
  const el = $(id);
  if (!el) return;
  if (el.textContent !== txt) el.textContent = txt;
  if (cl !== undefined) { el.classList.toggle('up', cl === 'up'); el.classList.toggle('dn', cl === 'dn'); }
}

function buildInputs() {
  const box = $('inputs');
  box.innerHTML = '';
  inputs.length = 0;
  for (const c of INPUTS) {
    const el = document.createElement('div');
    el.className = 'icard';
    el.style.setProperty('--c', c.color);
    el.innerHTML = '<div class="ic-h"><span class="ic-t"></span><span class="ic-v">—</span></div><div class="ic-s">—</div><canvas></canvas>';
    el.addEventListener('click', () => c.sym && selectSymbol(c.sym));
    box.appendChild(el);
    inputs.push({ ...c, el, tEl: el.querySelector('.ic-t'), vEl: el.querySelector('.ic-v'), sEl: el.querySelector('.ic-s'), cv: el.querySelector('canvas') });
  }
}

function renderInputs() {
  const sym = S.sel, fu = S.futAll.get(sym), b = F.base(sym);
  for (const c of inputs) {
    let title = '', val = '—', sub = '—', series = [], vcl = '', zero = false;
    if (c.kind === 'coin') {
      const rec = S.spotAll.get(c.sym);
      title = F.base(c.sym);
      if (rec) { val = F.price(rec.last); sub = t('in.spot', { chg: F.pct(rec.chg) }); vcl = F.cls(rec.chg); }
      series = S.spark.get(c.sym) || [];
    } else if (c.kind === 'basis') {
      title = t('in.basis');
      const lastB = S.basis[S.basis.length - 1];
      if (lastB && Number.isFinite(lastB.bps)) { val = F.bps(lastB.bps); vcl = F.cls(lastB.bps); }
      sub = fu ? t('in.basis.s', { sym: b }) : t('fn.nofut');
      series = S.basis.map((x) => x.bps); zero = true;
    } else if (c.kind === 'fund') {
      title = t('in.fund');
      if (fu && Number.isFinite(fu.funding)) { val = (fu.funding * 100).toFixed(4) + '%'; vcl = F.cls(fu.funding); }
      sub = fu ? t('in.fund.s', { sym: b, n: S.fut.fund.length }) : t('fn.nofut');
      series = S.fut.fund.map((x) => x.r); zero = true;
    } else if (c.kind === 'lsr') {
      title = t('in.lsr');
      const st = S.fut.stats[S.fut.stats.length - 1];
      if (st) { val = (+st.lsr_account).toFixed(2); vcl = st.lsr_account >= 1 ? 'up' : 'dn'; }
      sub = fu ? t('in.lsr.s', { sym: b }) : t('fn.nofut');
      series = S.fut.stats.map((x) => +x.lsr_account);
    }
    if (c.tEl.textContent !== title) c.tEl.textContent = title;
    if (c.vEl.textContent !== val) c.vEl.textContent = val;
    c.vEl.className = 'ic-v ' + vcl;
    if (c.sEl.textContent !== sub) c.sEl.textContent = sub;
    drawSpark(c.cv, series, c.color, { zero });
  }
}

function renderHeader() {
  const rec = S.spotAll.get(S.sel);
  setText('h-sym', F.base(S.sel));
  setText('h-price', rec ? F.price(rec.last) : '—');
  setText('h-chg', rec ? F.pct(rec.chg) : '—', rec ? F.cls(rec.chg) : '');
  if (S.mk) {
    const br = (S.mk.up / Math.max(1, S.mk.up + S.mk.dn)) * 100;
    setText('h-breadth', br.toFixed(1) + '%', br >= 50 ? 'up' : 'dn');
    setText('h-vol', F.usd(S.mk.vol));
  }
  if (S.fm) setText('h-oi', F.usd(S.fm.oi));
  setText('pk-sym', F.base(S.sel));
  setText('pk-px', rec ? F.price(rec.last) : '—');
  setText('pk-chg', rec ? F.pct(rec.chg) : '—', rec ? F.cls(rec.chg) : '');
  if (S.mk) setText('pl-stat', t('pl.stat', { up: S.mk.up, dn: S.mk.dn }));
  for (const k of ['rest', 'spot', 'fut']) $('c-' + k).className = S.conn[k] || '';
}

function renderOverview() {
  const mk = S.mk, fm = S.fm;
  if (mk) {
    setText('ov-vol', F.usd(mk.vol));
    setText('ov-sub', t('ov.sub', { n: mk.n, avg: F.pct(mk.avg), wavg: F.pct(mk.wavg) }));
    const tot = Math.max(1, mk.up + mk.dn);
    $('ov-bar-up').style.width = (mk.up / tot) * 100 + '%';
    $('ov-bar-dn').style.width = (mk.dn / tot) * 100 + '%';
    setText('ov-up', String(mk.up));
    setText('ov-dn', String(mk.dn));
    const br = (mk.up / tot) * 100;
    setText('ov-breadth', br.toFixed(1) + '%', br >= 50 ? 'up' : 'dn');
    const g = mk.gainers[0], l = mk.losers[0];
    setText('ov-gainer', g ? `${g.base} ${F.pct(g.chg)}` : '—');
    setText('ov-loser', l ? `${l.base} ${F.pct(l.chg)}` : '—');
    setText('ov-median', t('ov.median', { v: F.pct(S.median) }), F.cls(S.median));
    const cvd = $('cv-dist'), di = drawDist(cvd, S.dist);
    if (cvd._hover) {
      const b = S.dist[di];
      if (b) {
        const range = `${Number.isFinite(b.lo) ? (b.lo > 0 ? '+' : '') + b.lo + '%' : '−∞'} ~ ${Number.isFinite(b.hi) ? (b.hi > 0 ? '+' : '') + b.hi + '%' : '+∞'}`;
        showTip(`<div class="tt-h">24H ${range}</div>` + tr(t('ov.tt.pairs'), F.num(b.n)) +
          tr(t('ov.tt.share'), ((b.n / Math.max(1, mk.n)) * 100).toFixed(1) + '%') +
          (b.top.length ? `<div class="tt-f">${F.esc(t('ov.tt.top'))}</div>` + b.top.map((r) => tr(F.esc(r.base), `${F.pct(r.chg)} · ${F.usd(r.qv)}`, F.cls(r.chg))).join('') : ''),
        cvd._hover.cx, cvd._hover.cy);
      } else hideTip();
    }
  }
  if (fm) {
    setText('ov-oi', F.usd(fm.oi));
    setText('ov-pvol', F.usd(fm.vol));
    setText('ov-fund', Number.isFinite(fm.funding) ? (fm.funding * 100).toFixed(4) + '%' : '—', F.cls(fm.funding));
  }
}

function renderBook() {
  const bk = S.book;
  if (!bk || !bk.bids.length || !bk.asks.length) return;
  const ba = bk.asks[0][0], bb = bk.bids[0][0], spread = ba - bb, mid = (ba + bb) / 2;
  setText('ld-spread', t('ld.spread', { v: F.price(spread, F.priceDigits(mid)) }));
  // ladder: as many levels per side as fit the panel
  const lw = document.querySelector('.ladder-wrap');
  const lv = Math.max(3, Math.min(10, Math.floor((lw.clientHeight - 16 - 24) / 2 / 16)));
  const a5 = bk.asks.slice(0, lv).reverse(), b5 = bk.bids.slice(0, lv);
  const m5 = Math.max(...a5.map((x) => x[1]), ...b5.map((x) => x[1]));
  const row = (x, c, m) => `<div class="lr ${c}" data-p="${x[0]}"><i style="width:${((x[1] / m) * 100).toFixed(1)}%"></i><span>${F.price(x[0])}</span><span>${F.amt(x[1])}</span></div>`;
  $('ladder').innerHTML = a5.map((x) => row(x, 'a', m5)).join('') + `<div class="mid">${F.price(mid)}</div>` + b5.map((x) => row(x, 'b', m5)).join('');
  // depth: 8 / 8 with cumulative
  const cum = (arr) => { let s = 0; return arr.map((x) => [x[0], x[1], (s += x[1])]); };
  const asks = cum(bk.asks.slice(0, 8)), bids = cum(bk.bids.slice(0, 8));
  const mc = Math.max(asks[asks.length - 1][2], bids[bids.length - 1][2]);
  const drow = (x, c) => `<div class="drow ${c}" data-p="${x[0]}"><i style="width:${((x[2] / mc) * 100).toFixed(1)}%"></i><span>${F.price(x[0])}</span><span>${F.amt(x[1])}</span><span>${F.amt(x[2])}</span></div>`;
  $('depth-asks').innerHTML = asks.slice().reverse().map((x) => drow(x, 'a')).join('');
  $('depth-bids').innerHTML = bids.map((x) => drow(x, 'b')).join('');
  setText('depth-spread', t('dp.spread', { v: F.price(spread, F.priceDigits(mid)), bps: ((spread / mid) * 1e4).toFixed(2) }));
  if (S.bookHover) bookTip(S.bookHover.cx, S.bookHover.cy);
}

// tooltip for one price level of the depth table / ladder: cumulative size + notional from the best price
function bookTip(cx, cy) {
  const el = document.elementFromPoint(cx, cy)?.closest('.drow, .lr');
  const bk = S.book;
  if (!el || !bk) { hideTip(); return; }
  const p = +el.dataset.p, isAsk = el.classList.contains('a');
  const side = isAsk ? bk.asks : bk.bids, mid = (bk.asks[0][0] + bk.bids[0][0]) / 2;
  let q = 0, n = 0;
  for (const [px, sz] of side) { if (isAsk ? px > p : px < p) break; q += sz; n += px * sz; }
  showTip(`<div class="tt-h">${F.esc(F.base(S.sel))} · <span class="${isAsk ? 'dn' : 'up'}">${F.esc(t(isAsk ? 'dp.tt.ask' : 'dp.tt.bid'))}</span> ${F.price(p)}</div>` +
    tr(t('dp.tt.cumq'), F.amt(q)) + tr(t('dp.tt.cumn'), F.usd(n)) + tr(t('dp.tt.dist'), F.pct(((p - mid) / mid) * 100, 3), isAsk ? 'dn' : 'up'), cx, cy);
}

function renderSpot() {
  const rec = S.spotAll.get(S.sel);
  if (rec) {
    setText('sp-price', F.price(rec.last), F.cls(rec.chg));
    setText('sp-chg', F.pct(rec.chg), F.cls(rec.chg));
    setText('sp-high', F.price(rec.high));
    setText('sp-low', F.price(rec.low));
    setText('sp-qv', F.usd(rec.qv));
  }
  const cv = $('cv-candles');
  const res = drawCandles(cv, chartCandles(), S.kv);
  S.kv.maxOffset = res.maxOffset;
  if (cv._hover) res.k ? showTip(candleTip(res.k), cv._hover.cx, cv._hover.cy) : hideTip();
  drawSpark($('cv-ld'), S.candles.slice(-40).map((k) => k.c), rec && rec.chg < 0 ? C.red : C.green);
}

function renderBasis() {
  const fu = S.futAll.get(S.sel), lb = S.basis[S.basis.length - 1];
  const ms = (v) => (Number.isFinite(v) && Math.abs(v) < 60000 ? Math.max(0, Math.round(v)) + ' ms' : '—');
  setText('bs-lat-s', ms(S.lat.spot));
  setText('bs-lat-f', ms(S.lat.fut));
  setText('bs-basis', lb && Number.isFinite(lb.bps) ? F.bps(lb.bps) + ' bp' : '—', lb ? F.cls(lb.bps) : '');
  setText('bs-prem', lb && Number.isFinite(lb.prem) ? F.bps(lb.prem) + ' bp' : '—', lb ? F.cls(lb.prem) : '');
  setText('bs-mark', fu && fu.mark ? F.price(fu.mark) : '—');
  setText('bs-index', fu && fu.index ? F.price(fu.index) : '—');
  const cvb = $('cv-basis');
  const bi = drawBasis(cvb, S.basis, { basis: t('bs.legend.basis'), prem: t('bs.legend.prem'), lat: t('bs.legend.lat') });
  if (cvb._hover) {
    const p = S.basis[bi];
    if (p) {
      const ms = (v) => (Number.isFinite(v) ? Math.max(0, Math.round(v)) + ' ms' : '—');
      showTip(`<div class="tt-h">${F.esc(F.base(S.sel))} · ${F.hms(p.ts)}</div>` +
        tr(t('bs.basis'), Number.isFinite(p.bps) ? F.bps(p.bps) + ' bp' : '—', F.cls(p.bps)) +
        tr(t('bs.prem'), Number.isFinite(p.prem) ? F.bps(p.prem) + ' bp' : '—', F.cls(p.prem)) +
        tr(t('bs.latS'), ms(p.latS)) + tr(t('bs.latF'), ms(p.latF)), cvb._hover.cx, cvb._hover.cy);
    } else hideTip();
  }
}

function renderWire() {
  const rowsFit = Math.max(6, Math.floor($('wire').clientHeight / 15));
  setText('wi-rate', S.wirePaused ? t('wi.paused') : S.fps + ' msg/s');
  if (!S.wirePaused) $('wire').innerHTML = S.wire.slice(0, rowsFit).map((e) =>
    `<div class="wr${e.hl ? ' hl' : ''}"><span class="ts">${F.hmsms(e.ts)}</span><span class="${e.cls}">${F.esc(e.ch)}</span><span>${F.esc(e.txt)}</span></div>`).join('');
  setText('wi-total', F.num(S.frames));
  setText('wi-bytes', F.bytes((spotWS?.bytes || 0) + (futWS?.bytes || 0)));
  setText('wi-subs', String((spotWS?.subs.size || 0) + (futWS?.subs.size || 0)));
}

let whalesVer = -1;
function renderWhales() {
  setText('wh-th', t('wh.th'));
  setText('hist-now', S.hist[S.hist.length - 1] + '/s');
  const cvh = $('cv-hist'), hb = drawBars(cvh, S.hist, C.amber);
  if (cvh._hover && hb >= 0) {
    const ago = S.hist.length - hb;
    showTip(`<div class="tt-h">${F.hms(Date.now() + S.offset - ago * 1000)} · ${F.esc(t('tt.ago', { s: ago }))}</div>` + tr(t('wh.tt'), S.hist[hb] + '/s'), cvh._hover.cx, cvh._hover.cy);
  }
  if (whalesVer === S.ver.whales) return;
  const box = $('whales');
  const known = new Set([...box.children].map((el) => el.dataset.id));
  if (!S.whales.length) { box.innerHTML = `<div class="wc-s">${F.esc(t('wh.empty'))}</div>`; whalesVer = S.ver.whales; return; }
  if (box.firstElementChild && !box.firstElementChild.dataset.id) box.innerHTML = '';
  // prepend new ones (oldest first so the newest ends on top)
  for (const w of S.whales.slice().reverse()) {
    if (known.has(String(w.id))) continue;
    const el = document.createElement('div');
    el.className = 'wcard ' + w.side;
    el.dataset.id = w.id;
    el.dataset.pair = w.pair;
    const mult = w.med ? Math.round(w.notional / w.med) : 0;
    if (mult) el.title = t('wh.x.t', { x: mult, coin: F.base(w.pair), med: F.usd(w.med, 0) });
    el.innerHTML = `<div class="wc-h"><b>${F.esc(F.base(w.pair))}</b><span class="${w.side === 'buy' ? 'up' : 'dn'}">${F.esc(t(w.side === 'buy' ? 'wh.buy' : 'wh.sell'))} · ${F.esc(t(w.mkt))}</span><em>${F.usd(w.notional, w.notional < 1e4 ? 0 : 2)}</em></div>` +
      `<div class="wc-s"><span>@ ${F.price(w.price)} · ${F.hms(w.ts)}</span>${mult ? `<span class="wc-x">×${mult}</span>` : ''}</div><div class="wc-bar"><i style="width:${Math.min(100, (Math.log10(w.notional / w.th) + 0.15) * 80).toFixed(0)}%"></i></div>`;
    el.addEventListener('click', () => selectSymbol(w.pair));
    box.prepend(el);
    shell && shell.link(w.pair, el);
  }
  while (box.children.length > 14) box.lastElementChild.remove();
  whalesVer = S.ver.whales;
}

let tapeVer = -1;
function renderTape() {
  if (tapeVer !== S.ver.tape) {
    tapeVer = S.ver.tape;
    const thS = whaleTh('spot', S.sel).th, thP = whaleTh('perp', S.sel).th;
    $('tape-body').innerHTML = S.tape.slice(0, 30).map((x) => {
      const th = x.mkt === 'spot' ? thS : thP;
      const sc = x.side === 'buy' ? 'up' : 'dn';
      return `<tr class="${x.notional >= th ? 'big' : ''}"><td>${F.hms(x.ts)}</td><td class="m-${x.mkt}">${F.esc(t(x.mkt))}</td>` +
        `<td class="${sc}">${F.esc(t(x.side === 'buy' ? 'wh.buy' : 'wh.sell'))}</td><td class="${sc}">${F.price(x.price)}</td><td>${F.amt(x.amount)}</td><td>${F.usd(x.notional)}</td></tr>`;
    }).join('');
  }
  const now = Date.now(), buckets = Array.from({ length: 12 }, () => ({ buy: 0, sell: 0 }));
  let buy = 0, sell = 0;
  for (const f of S.flow) {
    const i = 11 - Math.floor((now - f.ts) / 5000);
    if (i < 0 || i > 11) continue;
    buckets[i][f.side] += f.notional;
    if (f.side === 'buy') buy += f.notional; else sell += f.notional;
  }
  const cvf = $('cv-flow'), fi = drawFlow(cvf, buckets);
  if (cvf._hover && fi >= 0) {
    const b = buckets[fi], from = now + S.offset - (12 - fi) * 5000;
    showTip(`<div class="tt-h">${F.esc(F.base(S.sel))} · ${F.hms(from)} – ${F.hms(from + 5000)}</div>` +
      tr(t('tp.tt.buy'), F.usd(b.buy), 'up') + tr(t('tp.tt.sell'), F.usd(b.sell), 'dn') + tr(t('tp.tt.net'), F.usd(b.buy - b.sell), F.cls(b.buy - b.sell)),
    cvf._hover.cx, cvf._hover.cy);
  }
  setText('fl-buy', '▲ ' + F.usd(buy));
  setText('fl-sell', '▼ ' + F.usd(sell));
  const lt = S.tape[0];
  setText('tc-last', lt ? `${F.price(lt.price)}` : '—', lt ? (lt.side === 'buy' ? 'up' : 'dn') : '');
  setText('tc-buy', buy + sell ? ((buy / (buy + sell)) * 100).toFixed(1) + '%' : '—', buy + sell ? (buy >= sell ? 'up' : 'dn') : '');
  setText('tc-vol', F.usd(buy + sell));
  setText('tc-whales', String(S.whaleCount));
}

function sigma1m() {
  const open = Math.floor((Date.now() + S.offset) / 60000) * 60;
  const closed = S.candles.length && S.candles[S.candles.length - 1].t >= open ? S.candles.slice(0, -1) : S.candles;
  const cs = closed.slice(-61);
  if (cs.length < 10) return NaN;
  const r = [];
  for (let i = 1; i < cs.length; i++) r.push(Math.log(cs[i].c / cs[i - 1].c));
  const m = r.reduce((a, b) => a + b, 0) / r.length;
  return Math.sqrt(r.reduce((a, b) => a + (b - m) ** 2, 0) / (r.length - 1));
}

let liqVer = -1;
function renderFunnelPanel() {
  const fu = S.futAll.get(S.sel), now = Date.now() + S.offset;
  if (fu && S.fut.next) {
    setText('fc-fund', F.dur(S.fut.next - now / 1000));
    setText('fc-fund-r', (fu.funding * 100).toFixed(4) + '%', F.cls(fu.funding));
  } else {
    setText('fc-fund', '—');
    setText('fc-fund-r', fu ? '—' : t('fn.nofut'), '');
  }
  const sg = sigma1m();
  setText('fc-vol', Number.isFinite(sg) ? (sg * Math.sqrt(525600) * 100).toFixed(1) + '%' : '—');
  const st = S.fut.stats[S.fut.stats.length - 1];
  if (st) {
    setText('fc-lsr', (+st.lsr_account).toFixed(2), st.lsr_account >= 1 ? 'up' : 'dn');
    setText('fc-lsr-s', `L ${F.num(st.long_users)} / S ${F.num(st.short_users)}`);
    let l = 0, s = 0;
    for (const x of S.fut.stats) { l += +x.long_liq_usd || 0; s += +x.short_liq_usd || 0; }
    setText('fc-liq', F.usd(l + s));
    setText('fc-liq-s', t('fn.liq.split', { l: F.usd(l), s: F.usd(s) }));
  } else {
    for (const id of ['fc-lsr', 'fc-liq']) setText(id, '—', '');
    for (const id of ['fc-lsr-s', 'fc-liq-s']) setText(id, fu ? '—' : t('fn.nofut'));
  }
  if (liqVer !== S.ver.liqs) {
    liqVer = S.ver.liqs;
    $('liq-list').innerHTML = `<div class="lh">${F.esc(t('fn.liq.head'))}</div>` + S.liqAll.slice(0, 5).map((x) =>
      `<div class="lq"><span class="${x.side === 'long' ? 'dn' : 'up'}">${F.esc(F.base(x.pair))} ${F.esc(t(x.side === 'long' ? 'fn.liq.long' : 'fn.liq.short'))}</span> <em>${F.usd(x.notional)}</em> @ ${F.price(x.px)}</div>`).join('');
  }
}

function renderMarquees() {
  const mk = S.mk, fm = S.fm;
  if (!mk) return;
  const it = (r) => `<span class="it" data-pair="${F.esc(r.pair)}">${F.esc(r.base)} <b>${F.price(r.last)}</b><span class="${F.cls(r.chg)}">${F.pct(r.chg)}</span></span>`;
  const majors = S.focus.slice(0, 12).map((p) => S.spotAll.get(p)).filter(Boolean);
  $('mq-top').innerHTML = majors.map(it).join('') +
    `<span class="it ch-sys">${F.esc(t('mq.gain'))} ▲</span>` + mk.gainers.map(it).join('') +
    `<span class="it ch-sys">${F.esc(t('mq.lose'))} ▼</span>` + mk.losers.map(it).join('');
  $('mq-bottom').innerHTML = `<span class="it">${F.esc(t('mq.summary', {
    n: mk.n, up: mk.up, dn: mk.dn, vol: F.usd(mk.vol), oi: fm ? F.usd(fm.oi) : '—', pvol: fm ? F.usd(fm.vol) : '—',
    fund: fm && Number.isFinite(fm.funding) ? (fm.funding * 100).toFixed(4) + '%' : '—',
    liq: F.usd(S.liqSeen.long + S.liqSeen.short), wh: S.whaleCount,
  }))}</span>`;
}

let lqVer = -1;
function renderLiq() {
  const st = S.liqStats;
  if (st) {
    setText('lq-stat', t('lq.stat', { n: F.num(st.nl + st.ns) }));
    setText('lq-long', F.usd(st.long));
    setText('lq-short', F.usd(st.short));
    setText('lq-long-n', t('lq.n', { n: F.num(st.nl) }));
    setText('lq-short-n', t('lq.n', { n: F.num(st.ns) }));
    setText('lq-max', st.max ? F.usd(st.max.notional) : '—', st.max ? (st.max.side === 'long' ? 'dn' : 'up') : '');
    setText('lq-max-s', st.max ? `${F.base(st.max.pair)} · ${t(st.max.side === 'long' ? 'fn.liq.long' : 'fn.liq.short')} · ${F.hms(st.max.ts)}` : '—');
    const tot = st.long + st.short;
    setText('lq-ratio', tot ? `${((st.long / tot) * 100).toFixed(0)}% / ${((st.short / tot) * 100).toFixed(0)}%` : '—');
    $('lq-split-l').style.width = tot ? (st.long / tot) * 100 + '%' : '50%';
    $('lq-split-s').style.width = tot ? (st.short / tot) * 100 + '%' : '50%';
    const mx = st.top[0] ? st.top[0].l + st.top[0].s : 1;
    setHtml('lq-top', st.top.map((b) => `<div class="dv-row lq-row" data-pair="${F.esc(b.pair)}">` +
      `<i class="bar-r" style="width:${((b.l / mx) * 100).toFixed(1)}%"></i><i class="bar-g" style="left:${((b.l / mx) * 100).toFixed(1)}%;width:${((b.s / mx) * 100).toFixed(1)}%"></i>` +
      `<span class="dv-b">${F.esc(F.base(b.pair))}</span><span>${F.usd(b.l + b.s)}</span><span class="${b.l >= b.s ? 'dn' : 'up'}">${((b.l / (b.l + b.s)) * 100).toFixed(0)}%</span></div>`).join(''));
  }
  if (lqVer === S.ver.liqs) return;
  lqVer = S.ver.liqs;
  const fresh = Date.now() + S.offset - 5000;
  $('lq-feed').innerHTML = S.liqAll.slice(0, 10).map((q) => `<div class="lq-item${q.ts > fresh ? ' new' : ''}" data-pair="${F.esc(q.pair)}">` +
    `<span class="ts">${F.hms(q.ts)}</span><b>${F.esc(F.base(q.pair))}</b>` +
    `<span class="lq-tag ${q.side === 'long' ? 'dn' : 'up'}">${F.esc(t(q.side === 'long' ? 'fn.liq.long' : 'fn.liq.short'))}</span>` +
    `<em>${F.usd(q.notional)}</em><span class="px">@ ${F.price(q.px)}</span></div>`).join('') ||
    `<div class="wc-s">${F.esc(t('lq.empty'))}</div>`;
}

let dvVer = -1;
function renderDeriv() {
  const fm = S.fm, dv = S.dv;
  if (!fm || !dv) return;
  setText('dv-count', t('dv.count', { n: fm.n }));
  setText('dv-oi-t', F.usd(fm.oi));
  setText('dv-vol-t', F.usd(fm.vol));
  setText('dv-pos', String(dv.pos));
  setText('dv-neg', String(dv.neg));
  if (dvVer === S.ver.dv) return;
  dvVer = S.ver.dv;
  const maxOi = dv.oiTop[0]?.oi || 1;
  const row = (r, cols, w, cl) => `<div class="dv-row${r.contract === S.sel ? ' sel' : ''}" data-pair="${F.esc(r.contract)}">` +
    `<i class="${cl}" style="width:${(w * 100).toFixed(1)}%"></i><span class="dv-b">${F.esc(F.base(r.contract))}</span>${cols}</div>`;
  $('dv-oi').innerHTML = dv.oiTop.map((r, i) => row(r,
    `<span>${F.usd(r.oi)}</span><span class="${F.cls(r.chg)}">${F.pct(r.chg)}</span>`, r.oi / maxOi, 'bar-c')).join('');
  const apr = (r) => r.funding * (365 * 86400 / (S.fundInterval.get(r.contract) || 28800)) * 100;
  const maxF = Math.max(1e-9, ...dv.fHi.concat(dv.fLo).map((r) => Math.abs(r.funding)));
  const frow = (r) => row(r, `<span class="${F.cls(r.funding)}">${(r.funding * 100).toFixed(4)}%</span><span class="${F.cls(r.funding)}">${apr(r).toFixed(1)}%</span>`,
    Math.abs(r.funding) / maxF, r.funding >= 0 ? 'bar-g' : 'bar-r');
  $('dv-fhi').innerHTML = dv.fHi.map(frow).join('');
  $('dv-flo').innerHTML = dv.fLo.map(frow).join('');
}

function renderHeatHeader() {
  const top = S.top.slice(0, HEAT_N);
  if (!top.length) return;
  setText('hm-note', t('hm.note', { n: top.length }));
  setText('hm-stat', t('hm.stat', { up: top.filter((r) => r.chg > 0).length, dn: top.filter((r) => r.chg < 0).length }));
}

function pickerRows(sort, q) {
  let arr = [...S.spotAll.values()].filter((r) => r.last > 0 && r.qv > 0);
  // searching shows stablecoins too; leveraged tokens (BTC3L…) only when the query has a digit
  arr = q ? arr.filter((r) => r.base.includes(q) && (/\d/.test(q) || !LEVERAGED.test(r.base)))
    : arr.filter((r) => !STABLE.has(r.base) && !LEVERAGED.test(r.base));
  if (sort === 'perp') arr = arr.filter((r) => S.futAll.has(r.pair));
  if (sort === 'up') arr = arr.filter((r) => r.qv >= 100_000).sort((a, b) => b.chg - a.chg);
  else if (sort === 'dn') arr = arr.filter((r) => r.qv >= 100_000).sort((a, b) => a.chg - b.chg);
  else arr.sort((a, b) => b.qv - a.qv);
  if (q) arr.sort((a, b) => (b.base === q) - (a.base === q) || b.base.startsWith(q) - a.base.startsWith(q));
  return { total: arr.length, rows: arr.slice(0, 150).map((r) => ({ ...r, perp: S.futAll.has(r.pair) })) };
}

async function loadFundingIntervals() {
  try {
    const arr = await rest('/futures/usdt/contracts');
    for (const c of arr) if (c.funding_interval) S.fundInterval.set(c.name, +c.funding_interval);
    S.ver.dv++;
  } catch (e) { /* assume 8h */ }
}

function render() {
  renderHeader();
  renderOverview();
  renderBook();
  renderSpot();
  renderBasis();
  renderWire();
  renderInputs();
  renderWhales();
  renderTape();
  renderFunnelPanel();
  renderDeriv();
  renderLiq();
  setText('tp-time-h', `${t('tp.time')} · ${tzSw ? tzSw.short() : 'UTC'}`);
  renderHeatHeader();
  setText('sh-count', t('sh.count', { n: shell ? shell.count() : 0 }));
  $('shell-wait').classList.toggle('hide', !!(shell && shell.count()));
}

// ---------------------------------------------------------------- tooltip
const onHover = (sym, x, y) => showSymTip($('shell-tip'), $('shell-wrap'), sym, x, y);
const onHeatHover = (sym, x, y) => showSymTip($('hm-tip'), document.querySelector('.hm-wrap'), sym, x, y);
function showSymTip(tip, wrap, sym, x, y) {
  if (!sym) { tip.style.display = 'none'; return; }
  const r = S.spotAll.get(sym), fu = S.futAll.get(sym);
  if (!r) return;
  tip.innerHTML = `<div class="tt-h">${F.esc(r.base)} / USDT</div>` +
    `<div class="tt-r"><span>${F.esc(t('sh.tip.price'))}</span><b>${F.price(r.last)}</b></div>` +
    `<div class="tt-r"><span>${F.esc(t('sh.tip.chg'))}</span><b class="${F.cls(r.chg)}">${F.pct(r.chg)}</b></div>` +
    `<div class="tt-r"><span>${F.esc(t('sh.tip.vol'))}</span><b>${F.usd(r.qv)}</b></div>` +
    (fu ? `<div class="tt-r"><span>${F.esc(t('sh.tip.perp'))}</span><b class="${F.cls(fu.funding)}">${(fu.funding * 100).toFixed(4)}%</b></div>` : '');
  tip.style.display = 'block';
  tip.style.left = Math.min(x + 14, wrap.clientWidth - tip.offsetWidth - 6) + 'px';
  tip.style.top = Math.min(y + 14, wrap.clientHeight - tip.offsetHeight - 6) + 'px';
}

// ---------------------------------------------------------------- main loop
function loop(now) {
  pulse && pulse.frame(now);
  heat && heat.draw(now);
  liqChart && liqChart.draw(now, S.liqAll);
  if (shell) {
    const wires = inputs.map((c) => {
      const sym = c.sym || S.sel;
      return { el: c.el, sym, color: c.color, activity: Math.min(1, (S.rate.get(sym) || 0) / 25) };
    });
    shell.frame(now, wires);
  }
  if (funnel) {
    const cs = S.candles.slice(-60);
    const fh = funnel.draw(now, {
      closes: cs.map((k) => ({ t: k.t, c: k.c })),
      last: S.spotAll.get(S.sel)?.last,
      sigma1m: sigma1m(),
      labels: { now: t('fn.now'), wait: t('fn.wait') },
    });
    const cvn = $('cv-funnel');
    if (cvn._hover) {
      const lastPx = S.spotAll.get(S.sel)?.last;
      fh ? showTip(`<div class="tt-h">${F.esc(F.base(S.sel))} · ${fh.now ? F.esc(t('fn.now')) : F.dhm(fh.t)}</div>` +
        tr(t('fn.tt.close'), F.price(fh.c)) + (fh.now ? '' : tr(t('fn.tt.vs'), F.pct(((lastPx - fh.c) / fh.c) * 100), F.cls(lastPx - fh.c))),
      cvn._hover.cx, cvn._hover.cy) : hideTip();
    }
  }
  requestAnimationFrame(loop);
}

// ---------------------------------------------------------------- boot
async function boot() {
  applyDom();
  initPages();
  $('lang-btn').addEventListener('click', () => setLang(getLang() === 'zh' ? 'en' : 'zh'));
  onLang(() => { tzSw && tzSw.label(); whalesVer = -1; tapeVer = -1; liqVer = -1; dvVer = -1; lqVer = -1; $('whales').innerHTML = ''; render(); renderMarquees(); });
  buildInputs();
  // time zone: re-render every list that shows timestamps
  tzSw = createTz($('tz'), {
    getNow: () => Date.now() + S.offset,
    onChange: () => { whalesVer = -1; tapeVer = -1; liqVer = -1; lqVer = -1; $('whales').innerHTML = ''; $('clock').textContent = F.hms(Date.now() + S.offset); render(); },
  });
  funnel = createFunnel($('cv-funnel'));
  heat = createHeatmap($('cv-heat'), { onPick: selectSymbol, onHover: onHeatHover });
  try {
    pulse = createPulse($('cv-pulse'), {
      onPick: selectSymbol,
      onHover: (it, cx, cy) => {
        if (!it) { hideTip(); return; }
        const r = S.spotAll.get(it.sym);
        showTip(`<div class="tt-h">${F.esc(it.label)} / USDT</div>` + tr(t('sh.tip.chg'), F.pct(it.chg), F.cls(it.chg)) +
          (r ? tr(t('sh.tip.price'), F.price(r.last)) + tr(t('sh.tip.vol'), F.usd(r.qv)) : '') + `<div class="tt-f">${F.esc(t('lq.tt.click'))}</div>`, cx, cy);
      },
      onFocus: (it) => {
        $('pl-focus').innerHTML = it ? `${F.esc(it.label)} <span class="${F.cls(it.chg)}">${F.pct(it.chg)}</span>` : '';
      },
    });
  } catch (e) {
    pulse = null;
  }
  initKlineControls();
  $('wh-th').addEventListener('pointermove', (e) => showTip(whaleRuleTip(), e.clientX, e.clientY));
  $('wh-th').addEventListener('pointerleave', hideTip);
  hoverable($('cv-basis'), renderBasis);
  hoverable($('cv-dist'), renderOverview);
  hoverable($('cv-hist'), renderWhales);
  hoverable($('cv-flow'), renderTape);
  hoverable($('cv-funnel'), () => {});
  for (const id of ['depth-asks', 'depth-bids', 'ladder']) {
    $(id).addEventListener('pointermove', (e) => { S.bookHover = { cx: e.clientX, cy: e.clientY }; bookTip(e.clientX, e.clientY); });
    $(id).addEventListener('pointerleave', () => { S.bookHover = null; hideTip(); });
  }
  $('wire').addEventListener('pointerenter', () => { S.wirePaused = true; renderWire(); });
  $('wire').addEventListener('pointerleave', () => { S.wirePaused = false; renderWire(); });
  for (const id of ['mq-top', 'mq-bottom']) {
    $(id).addEventListener('click', (e) => { const x = e.target.closest('[data-pair]'); if (x) selectSymbol(x.dataset.pair); });
  }
  picker = createPicker($('picker'), { getRows: pickerRows, getRec: (p) => S.spotAll.get(p), getSel: () => S.sel, onPick: selectSymbol });
  liqChart = createLiqChart($('lq-chart'), { onPick: selectSymbol, getNow: () => Date.now() + S.offset, getSel: () => S.sel });
  const lqPanel = document.querySelector('.a-lq');
  lqPanel.addEventListener('click', (e) => {
    const row = e.target.closest('.lq-row, .lq-item');
    if (row) selectSymbol(row.dataset.pair);
  });
  // hovering a contract in the side lists highlights its bubbles; pointermove
  // (not over/out) so it keeps working while the lists re-render underneath
  let hl = null;
  lqPanel.querySelectorAll('.lq-side').forEach((side) => {
    side.addEventListener('pointermove', (e) => {
      const row = e.target.closest('.lq-row, .lq-item'), p = row ? row.dataset.pair : null;
      if (p !== hl) { hl = p; liqChart.setHighlight(p); }
    });
    side.addEventListener('pointerleave', () => { hl = null; liqChart.setHighlight(null); });
  });
  document.querySelector('.a-dv').addEventListener('click', (e) => {
    const row = e.target.closest('.dv-row');
    if (row) selectSymbol(row.dataset.pair);
  });
  try {
    shell = createShell($('shell-wrap'), { onPick: selectSymbol, onHover });
  } catch (e) {
    console.error('WebGL shell unavailable', e);
    shell = null;
  }
  // shell skin switcher (torus / globe / galaxy), remembered per browser
  const skinSeg = $('skin-seg');
  const applySkin = (v) => {
    skinSeg.querySelectorAll('button').forEach((b) => b.classList.toggle('on', b.dataset.v === v));
    shell && shell.setSkin(v);
  };
  let skin0 = 'torus';
  try { skin0 = localStorage.getItem('c3.skin') || 'torus'; } catch (e) { /* ignore */ }
  applySkin(['torus', 'globe', 'galaxy'].includes(skin0) ? skin0 : 'torus');
  skinSeg.addEventListener('click', (e) => {
    const b = e.target.closest('button[data-v]');
    if (!b) return;
    applySkin(b.dataset.v);
    try { localStorage.setItem('c3.skin', b.dataset.v); } catch (err) { /* ignore */ }
  });
  requestAnimationFrame(loop);
  setInterval(perSecond, 1000);
  setInterval(calibrateClock, 5000);
  setInterval(liqStats, 1000);
  setInterval(flushOrders, 250);
  setInterval(render, 250);

  await syncClock();
  setInterval(syncClock, 300000);

  // retry until the first market snapshot is in
  while (!S.spotAll.size) {
    await Promise.all([pollSpotAll(), pollFutAll()]);
    if (!S.spotAll.size) await new Promise((res) => setTimeout(res, 5000));
  }
  computeFocus();
  shell && shell.setClusters(clusterList());
  sh_note();
  connectWS();
  seedLiqs();
  await selectSymbol(S.sel);
  renderMarquees();

  loadFundingIntervals();
  setInterval(pollSpotAll, 15000);
  setInterval(pollFutAll, 30000);
  setInterval(() => pollSelPerp(selToken), 60000);
  setInterval(renderMarquees, 45000);
}

// ---------------------------------------------------------------- QTW pages (one viewport)
const PAGE_OF = { 'a-ov': 1, 'a-sp': 1, 'a-bs': 1, 'a-sh': 2, 'a-lq': 3, 'a-hm': 4, 'a-dv': 4, 'a-tp': 5, 'a-fn': 5 };
function setPage(n) {
  n = Math.max(1, Math.min(5, n | 0 || 1));
  $('grid').dataset.page = String(n);
  for (const el of document.querySelectorAll('main.grid > .panel')) {
    const a = [...el.classList].find((c) => PAGE_OF[c]);
    el.classList.toggle('off', PAGE_OF[a] !== n);
  }
  document.querySelectorAll('#pg-tabs button[data-p]').forEach((b) => b.classList.toggle('on', +b.dataset.p === n));
  hideTip();
  try { localStorage.setItem('c3.page', String(n)); } catch (e) { /* ignore */ }
}
function initPages() {
  let n = 1;
  try { n = +localStorage.getItem('c3.page') || 1; } catch (e) { /* ignore */ }
  setPage(n);
  $('pg-tabs').addEventListener('click', (e) => { const b = e.target.closest('button[data-p]'); if (b) setPage(+b.dataset.p); });
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey || /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
    const cur = +$('grid').dataset.page || 1;
    if (/^[1-5]$/.test(e.key)) setPage(+e.key);
    else if (e.key === ']') setPage(cur % 5 + 1);
    else if (e.key === '[') setPage((cur + 3) % 5 + 1);
  });
}

function sh_note() {
  const el = document.querySelector('.ph-note');
  const upd = () => { el.textContent = t('sh.note', { n: S.focus.length }); };
  upd();
  onLang(upd);
}

boot();
