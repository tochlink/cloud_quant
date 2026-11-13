/* 指标页：更多技术指标 + 多空证据分（参考证据，不参与下单）。依赖 app.js 的全局助手（加载顺序：本文件在 app.js 之前，只在调用时引用）。 */
const IND_SYMS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"]; // 官方 8 个（OKX / Gate 都有现货与 USDT 永续）
const IND_TFS = [["1m", "1分钟"], ["5m", "5分钟"], ["10m", "10分钟"], ["1h", "1小时"], ["4h", "4小时"], ["1d", "日线"]];
const IND_IVSEC = { "1m": 60, "5m": 300, "10m": 600, "1h": 3600, "4h": 14400, "1d": 86400 };
const IND_OVERLAYS = {
  ma: ["均线 SMA50 / 150 · MA100", [["sma50", "SMA50", "#2cc4c9"], ["sma150", "SMA150", "#6c5ce7"], ["ma100", "MA100", "#f0a030", "dash"]]],
  ema: ["EMA 12 / 26", [["ema12", "EMA12", "#2cc4c9"], ["ema26", "EMA26", "#e58fb0"]]],
  boll: ["布林带 (20,2)", [["bb_up", "上轨", "#8a7cf0", "thin"], ["bb_mid", "中轨", "#f0a030", "dash"], ["bb_lo", "下轨", "#8a7cf0", "thin"]]],
  dc: ["唐奇安 20 / 55", [["dc20_hi", "20 高", "#2cc4c9", "thin"], ["dc20_lo", "20 低", "#2cc4c9", "thin"], ["dc55_hi", "55 高", "#6c5ce7", "dash"], ["dc55_lo", "55 低", "#6c5ce7", "dash"]]],
  st: ["超级趋势 (10,3)", [["st_line", "超级趋势", "#25b07a"]]],
  ich: ["一目均衡表", [["ich_tenkan", "转换线", "#2cc4c9"], ["ich_kijun", "基准线", "#e5536b"], ["ich_span_a", "先行 A", "#25b07a", "dash"], ["ich_span_b", "先行 B", "#f0a030", "dash"]]],
  vwap: ["VWAP 当日均价", [["vwap", "VWAP", "#f0a030"]]],
  none: ["不叠加", []],
};
const IND_SUBS = {
  score: { name: "证据分", prec: 2, levels: [0.25, -0.25], lines: [["score", "证据分", "#6c5ce7", "hist"]] },
  macd: { name: "MACD", prec: 4, lines: [["macd_hist", "柱", "#999", "hist"], ["macd", "DIF", "#2cc4c9"], ["macd_sig", "DEA", "#f0a030"]] },
  rsi: { name: "RSI 14", prec: 1, levels: [70, 55, 45, 30], lines: [["rsi14", "RSI", "#6c5ce7"]] },
  kdj: { name: "KDJ", prec: 1, levels: [80, 20], lines: [["kdj_k", "K", "#2cc4c9"], ["kdj_d", "D", "#f0a030"], ["kdj_j", "J", "#e58fb0"]] },
  pctb: { name: "布林 %B", prec: 2, levels: [1, 0.6, 0.4, 0], lines: [["bb_pctb", "%B", "#8a7cf0"]] },
  bbw: { name: "布林带宽 %", prec: 2, lines: [["bb_bw", "带宽", "#8a7cf0"]] },
  adx: { name: "ADX / DI", prec: 1, levels: [20], lines: [["adx", "ADX", "#6c5ce7"], ["pdi", "+DI", "#25b07a"], ["mdi", "−DI", "#e5536b"]] },
  cci: { name: "CCI 20", prec: 0, levels: [100, -100], lines: [["cci20", "CCI", "#2cc4c9"]] },
  wr: { name: "威廉 %R", prec: 1, levels: [-20, -40, -60, -80], lines: [["wr14", "%R", "#e58fb0"]] },
  obv: { name: "OBV 能量潮", prec: 0, lines: [["obv", "OBV", "#2cc4c9"], ["obv_ma20", "20 均线", "#f0a030"]] },
  mfi: { name: "MFI 14", prec: 1, levels: [80, 60, 40, 20], lines: [["mfi14", "MFI", "#25b07a"]] },
  volz: { name: "成交量 Z", prec: 2, levels: [2], lines: [["vol_z", "Z", "#999", "hist"]] },
  atr: { name: "ATR%", prec: 2, lines: [["atr_pct", "ATR%", "#f0a030"]] },
};
/* 点击某个指标：图上切到它对应的叠加 / 副图 */
const IND_VIEW = { ma_cross: ["ma"], trend100: ["ma"], ema: ["ema"], macd: [null, "macd"], rsi: [null, "rsi"], kdj: [null, "kdj"], boll: ["boll", "pctb"],
  bbw: ["boll", "bbw"], atr: [null, "atr"], adx: [null, "adx"], cci: [null, "cci"], wr: [null, "wr"], obv: [null, "obv"], mfi: [null, "mfi"], vwap: ["vwap"],
  dc20: ["dc"], dc55: ["dc"], supertrend: ["st"], ichimoku: ["ich"], volz: [null, "volz"] };
const tagCls = (t) => (t === "偏多" ? "long" : t === "偏空" ? "short" : "flat");
const scoreCls = (x) => (x >= 0.25 ? "pos" : x <= -0.25 ? "neg" : "");
const sc2 = (x) => (x == null || !isFinite(x) ? "—" : (x > 0 ? "+" : x < 0 ? "−" : "") + Math.abs(x).toFixed(2));

function indState() {
  const st = S.status.settings;
  S.ind = S.ind || { sym: "BTCUSDT", venue: st.venue, mkt: "spot", iv: "4h", overlay: "ma", sub: "score", filter: "all" };
  return S.ind;
}
async function pageIndicators() {
  const I = indState();
  const syms = IND_SYMS;
  $("#page").innerHTML = `
  <div class="fit ind-page">
    <div class="panel ind-bar">
      <select class="sel5" id="indSym" aria-label="币种">${syms.map((x) => `<option value="${x}" ${x === I.sym ? "selected" : ""}>${base(x)}</option>`).join("")}</select>
      <div class="seg seg5" id="indVen" role="group" aria-label="交易所"><button data-v="gate">Gate</button><button data-v="okx">OKX</button></div>
      <div class="seg seg5" id="indMkt" role="group" aria-label="市场"><button data-m="spot">现货</button><button data-m="perp">永续</button></div>
      <div class="seg seg5 iv-seg" id="indIv" role="group" aria-label="周期">${IND_TFS.map(([v, l]) => `<button data-iv="${v}" title="${v === "10m" ? "由官方 1 分钟 K 线聚合" : "交易所官方 K 线"}${v === "4h" ? "（策略主方向周期）" : ""}">${l}</button>`).join("")}</div>
      <span class="ind-sp"></span>
      <span class="ind-note" id="indSrc">加载中…</span>
    </div>
    <div class="ind-grid">
      <div class="panel ind-chart featured">
        <div class="ind-ch"><h3 id="indTitle">指标图</h3><label class="ind-lab">叠加<select class="sel5" id="indOv" aria-label="主图叠加">${Object.entries(IND_OVERLAYS).map(([k, [n]]) => `<option value="${k}">${n}</option>`).join("")}</select></label></div>
        <div class="ind-wrap"><div class="chart-box ind-box" id="indChart"><div class="empty">加载中…</div></div>
          <label class="ind-lab ind-sublab">副图<select class="sel5" id="indSub" aria-label="副图指标">${Object.entries(IND_SUBS).map(([k, x]) => `<option value="${k}">${x.name}</option>`).join("")}</select></label></div>
        <div class="ind-legend" id="indLegend"></div>
      </div>
      <div class="ind-side">
        <div class="panel ind-score" id="indScore"><div class="empty">计算中…</div></div>
        <div class="panel ind-list">
          <div class="ind-lh"><h3>指标明细</h3><div class="tabs5" id="indFilter"><button data-f="all">全部</button><button data-f="偏多">偏多</button><button data-f="偏空">偏空</button><button data-f="中性">中性</button></div></div>
          <div class="ind-rows" id="indRows"></div>
          <div id="indPager"></div>
        </div>
      </div>
    </div>
  </div>`;
  $("#indSym").onchange = (e) => { I.sym = e.target.value; indLoad(true); };
  document.querySelectorAll("#indVen [data-v]").forEach((b) => (b.onclick = () => { I.venue = b.dataset.v; indLoad(true); }));
  document.querySelectorAll("#indMkt [data-m]").forEach((b) => (b.onclick = () => { I.mkt = b.dataset.m; indLoad(true); }));
  document.querySelectorAll("#indIv [data-iv]").forEach((b) => (b.onclick = () => { I.iv = b.dataset.iv; indLoad(false); }));
  $("#indOv").onchange = (e) => { I.overlay = e.target.value; indDraw(); };
  $("#indSub").onchange = (e) => { I.sub = e.target.value; indDraw(); };
  document.querySelectorAll("#indFilter [data-f]").forEach((b) => (b.onclick = () => { I.filter = b.dataset.f; if (S.pg.ind) S.pg.ind.i = 0; indRenderRows(); }));
  indTipBind();
  if (!S.signals) api("/api/signals?quotes=false").then((r) => { S.signals = r; indRenderScore(); }).catch(() => {});
  indLoad(true);
}
function indSyncCtl() {
  const I = S.ind;
  document.querySelectorAll("#indVen [data-v]").forEach((b) => b.classList.toggle("on", b.dataset.v === I.venue));
  document.querySelectorAll("#indMkt [data-m]").forEach((b) => b.classList.toggle("on", b.dataset.m === I.mkt));
  document.querySelectorAll("#indIv [data-iv]").forEach((b) => b.classList.toggle("on", b.dataset.iv === I.iv));
  document.querySelectorAll("#indFilter [data-f]").forEach((b) => b.classList.toggle("on", b.dataset.f === I.filter));
  if ($("#indOv")) $("#indOv").value = I.overlay;
  if ($("#indSub")) $("#indSub").value = I.sub;
  if ($("#indSym")) $("#indSym").value = I.sym;
}
async function indLoad(withMatrix) {
  const I = S.ind; if (!I || !$("#indChart")) return;
  indSyncCtl();
  const q = `symbol=${I.sym}&venue=${I.venue}&market=${I.mkt}`;
  const req = (I._req = (I._req || 0) + 1);
  I._loadedAt = Date.now();
  if (withMatrix) indLoadMatrix();
  try {
    const d = await api(`/api/indicators?${q}&interval=${I.iv}&bars=300`);
    if (req !== I._req || !$("#indChart")) return;
    I.d = d; I.form = d.forming ? { ...d.forming } : null;
    indDraw(); indRenderRows(); indRenderScore();
  } catch (e) { if ($("#indChart")) $("#indChart").innerHTML = `<div class="empty neg">${esc(e.message)}</div>`; }
}
async function indLoadMatrix() {
  const I = S.ind; if (!I) return;
  const key = `${I.sym}:${I.venue}:${I.mkt}`;
  I._mxAt = Date.now();
  try {
    const m = await api(`/api/indicators/matrix?symbol=${I.sym}&venue=${I.venue}&market=${I.mkt}`);
    if (key !== `${S.ind.sym}:${S.ind.venue}:${S.ind.mkt}`) return;
    I.mx = m; indRenderScore();
  } catch (e) { I.mx = { error: e.message }; indRenderScore(); }
}
function indDraw() {
  const I = S.ind, d = I && I.d, el = $("#indChart"); if (!d || !el) return;
  indSyncCtl();
  const [ovName, ovRows] = IND_OVERLAYS[I.overlay] || IND_OVERLAYS.none;
  const sb = IND_SUBS[I.sub] || IND_SUBS.score;
  I.chart = BigCharts.indicators(el, d, { overlay: I.overlay, sub: I.sub, overlays: Object.fromEntries(Object.entries(IND_OVERLAYS).map(([k, v]) => [k, v[1]])), subs: IND_SUBS });
  if (I.form) indPaintForming();
  $("#indTitle").textContent = `${base(d.symbol)} ${d.market === "perp" ? "永续" : "现货"} · ${d.interval_cn} · ${VN[d.venue]}`;
  $("#indLegend").innerHTML = ovRows.map(([, n, c]) => `<span><i style="background:${c}"></i>${esc(n)}</span>`).join("") +
    `<span class="muted">副图：${esc(sb.name)}${sb.levels ? "（虚线 = 判断阈值）" : ""}</span><span class="muted">只用已收盘 K 线计算 · 北京时间</span>`;
  indRenderSrc();
}
function indRenderSrc() {
  const I = S.ind, d = I && I.d, el = $("#indSrc"); if (!d || !el) return;
  const age = I._liveAt ? Math.round((Date.now() - I._liveAt) / 1000) : null;
  el.innerHTML = `<i class="dot-live ${age != null && age < 30 ? "on" : ""}"></i>${age != null && age < 30 ? `实时 · ${esc(I._liveKind || "WebSocket")}` : "收盘后更新"} · ${esc(d.data_source || "")}${d.aggregated_from ? " · 由 " + esc(d.aggregated_from) + " 聚合" : ""}`;
  el.title = `${d.source_host || ""} · 拉取于 ${tFull(d.fetched_at)}`;
}
/* 实时：SSE 每次推送都检查（事件驱动，无定时轮询）。当前根只在图上跳动；收盘后重新拉取已收盘 K 线并重算指标 */
function indLive() {
  const I = S.ind, L = S.live, c = I && I.chart, d = I && I.d;
  if (!c || !d || !L || !$("#indChart")) return;
  const F = L.venue === I.venue ? L.forming : (L.forming_alt && L.forming_alt.venue === I.venue ? L.forming_alt.forming : null);
  if (!F) return;
  const iv = IND_IVSEC[I.iv], next = c._lastClosed + iv;
  const f = F[`${I.iv}:${I.sym}:${I.mkt}`], f1 = F[`1m:${I.sym}:${I.mkt}`];
  const closedNew = (f && f.time > next) || (f1 && f1.time >= next + iv) || (f && f.closed && f.time >= next);
  if (closedNew) { if (Date.now() - (I._loadedAt || 0) > 8000) indLoad(false); return; }
  if (f1 && I._m1 != null && f1.time > I._m1 && Date.now() - (I._mxAt || 0) > 55000) indLoadMatrix(); // 每根 1 分钟收盘：多周期矩阵跟着刷新
  if (f1) I._m1 = f1.time;
  let bar = null;
  if (f && f.time === next) bar = { time: next, open: f.open, high: f.high, low: f.low, close: f.close, src: f.source };
  else if (f1 && f1.time >= next && f1.time < next + iv) {
    const b0 = I.form && I.form.time === next ? I.form : { time: next, open: f1.open, high: f1.high, low: f1.low, close: f1.close };
    bar = { time: next, open: b0.open, high: Math.max(b0.high, f1.high), low: Math.min(b0.low, f1.low), close: f1.close, src: f1.source };
  }
  if (!bar) return;
  I.form = { time: bar.time, open: bar.open, high: bar.high, low: bar.low, close: bar.close };
  I._liveAt = Date.now(); I._liveKind = /_ws$/.test(bar.src || "") ? "WebSocket" : "REST 兜底";
  indPaintForming();
  indRenderSrc();
}
function indPaintForming() {
  const I = S.ind, c = I.chart; if (!c || !I.form || I.form.time <= c._lastClosed) return;
  try { c._candle.update({ time: I.form.time, open: I.form.open, high: I.form.high, low: I.form.low, close: I.form.close }); } catch (_) {}
}
function indCards() {
  const I = S.ind; const cs = (I.d && I.d.cards) || [];
  return I.filter === "all" ? cs : cs.filter((x) => x.tag === I.filter);
}
function indRenderRows() {
  const I = S.ind, host = $("#indRows"); if (!host || !I.d) return;
  indSyncCtl();
  const cs = indCards();
  const st = pgState("ind", cs.length, fitRows(host, 34, 0, 3));
  host.innerHTML = cs.slice(st.start, st.end).map((x) => `<div class="ind-row ${x.available ? "" : "na"}" data-k="${x.key}" tabindex="0" role="button" aria-label="${esc(x.name)}：${esc(x.tag)}">
      <div class="ind-nm"><b>${esc(x.name)}</b><span class="ind-g">${esc(x.group)}${x.context_only ? " · 背景" : x.weight !== 1 ? ` · 权重 ${x.weight}` : ""}</span></div>
      <div class="ind-val num" title="${esc(x.value)}">${esc(x.value)}</div>
      <span class="pill ${tagCls(x.tag)}">${esc(x.tag)}</span>
      <span class="info ind-i" tabindex="0" data-tip="${esc(x.reason)}" aria-label="${esc(x.name)} 说明">${ic("info")}</span>
    </div>`).join("") || `<div class="empty">没有${esc(I.filter)}的指标</div>`;
  const pg = $("#indPager"); if (pg) { pg.innerHTML = pagerHtml("ind", st); bindPager("ind", indRenderRows); }
  host.querySelectorAll(".ind-row").forEach((r) => (r.onclick = (e) => { if (e.target.closest(".ind-i")) return; indShow(r.dataset.k); }));
  requestAnimationFrame(() => refitByActualRows(host, "ind", ".ind-row", indRenderRows, 2));
}
function indShow(key) {
  const I = S.ind, v = IND_VIEW[key];
  if (v) { if (v[0]) I.overlay = v[0]; if (v[1]) I.sub = v[1]; indDraw(); return; }
  const x = (I.d.cards || []).find((c) => c.key === key); if (!x) return;
  modal(`<h3>${esc(x.name)} <span class="pill ${tagCls(x.tag)}">${esc(x.tag)}</span></h3><div class="note" style="margin:8px 0">当前值：<b>${esc(x.value)}</b> · 分组 ${esc(x.group)} · 权重 ${x.weight}</div><p>${esc(x.reason)}</p>
    <div class="note">数据来自 ${VN[I.venue]} 官方公共接口；这一项不画在 K 线图上。</div><div class="acts"><button class="btn" data-close>关闭</button></div>`, (m) => (m.querySelector("[data-close]").onclick = closeModal));
}
function indStrategyRow() {
  const I = S.ind, rows = (S.signals && S.signals.rows) || [];
  const r = rows.find((x) => x.symbol === I.sym);
  if (!r) return { html: `<span class="muted">${S.signals ? "该币不在当前交易列表里，策略没有信号" : "读取策略信号中…"}</span>`, sig: null };
  const v = r.signal, txt = v > 0 ? "做多" : v < 0 ? "做空" : "空仓";
  const extra = r.btc_regime_block_long && v > 0 ? " · BTC 熊市体制暂停新开多" : "";
  return { html: `<span class="pill ${v > 0 ? "long" : v < 0 ? "short" : "flat"}">${txt}${v ? " · " + (v > 0 ? "现货" : "永续") : ""}</span><span class="muted">${VN[S.status.settings.venue]} · 4 小时 SMA50/150${extra}</span>`, sig: v };
}
function indRenderScore() {
  const I = S.ind, host = $("#indScore"); if (!host || !I) return;
  const d = I.d, sm = d && d.summary, ts = d && d.tech_summary;
  const strat = indStrategyRow();
  const mx = I.mx && I.mx.rows;
  const m4 = mx && mx.find((x) => x.interval === "4h");
  const ref = m4 && m4.score != null ? m4.score : (I.iv === "4h" && ts ? ts.score : null);
  let agree = "—", agCls = "";
  if (strat.sig != null && ref != null) {
    const lab = ref >= 0.25 ? 1 : ref <= -0.25 ? -1 : 0;
    if (strat.sig === 0) { agree = "策略空仓"; }
    else if (lab === 0) { agree = "证据中性"; agCls = "warn"; }
    else if (lab === strat.sig) { agree = "方向一致"; agCls = "long"; }
    else { agree = "方向相反"; agCls = "short"; }
  }
  const pctPos = sm ? Math.round((sm.score + 1) * 50) : 50;
  const tip = `<b>参考证据，不参与下单。</b>每个指标按规则投票：偏多 +1、偏空 −1、中性 0；趋势 / 动量类权重 1，量能与合约类 0.5，布林带宽、ATR 只作背景（权重 0）。证据分 = 加权平均（−1 ~ +1），≥ +0.25 记偏多、≤ −0.25 记偏空。<br><br>研究：把它当成入场「一致性闸门」在 Gate 和 OKX 两年历史上都让收益变差（阈值越严越差），所以策略不用它下单。`;
  host.innerHTML = `
    <div class="isc-top">
      <div class="isc-l"><div class="isc-cap">多空证据 · ${esc(d ? d.interval_cn : "")}<span class="info ind-i" tabindex="0" data-tip="${esc(tip.replace(/<br>/g, "\n").replace(/<[^>]+>/g, ""))}" aria-label="证据分说明">${ic("info")}</span></div>
        <div class="isc-big ${sm ? scoreCls(sm.score) : ""}">${sm ? sc2(sm.score) : "—"}<em>${sm ? esc(sm.label) : ""}</em></div>
        <div class="isc-gauge"><i style="left:${pctPos}%"></i></div>
        <div class="isc-cnt">${sm ? `<span class="pos">偏多 ${sm.bull}</span><span class="neg">偏空 ${sm.bear}</span><span>中性 ${sm.neutral}</span><span class="muted">共 ${sm.n} 项</span>` : ""}<span class="pill info ref-tag">参考证据</span></div>
      </div>
      <div class="isc-r">
        <div class="isc-k">当前策略</div><div class="isc-v">${strat.html}</div>
        <div class="isc-k">对比 4 小时证据</div><div class="isc-v"><span class="pill ${agCls || "flat"}">${esc(agree)}</span>${ref != null ? `<span class="muted">4 小时 ${sc2(ref)}</span>` : ""}</div>
      </div>
    </div>
    <div class="isc-mx">${IND_TFS.map(([iv, lab]) => {
      const x = mx && mx.find((y) => y.interval === iv);
      const s0 = x && x.score != null ? x.score : null;
      return `<button class="mx-c ${iv === I.iv ? "on" : ""} ${s0 != null ? scoreCls(s0) : ""}" data-iv="${iv}" title="${x && x.error ? esc(x.error) : `${lab}：偏多 ${x ? x.bull : "—"} · 偏空 ${x ? x.bear : "—"} · 中性 ${x ? x.neutral : "—"}`}">
        <span class="mx-t">${lab}<span class="book-tag ${iv === "4h" || iv === "1d" ? "bk-long" : "bk-short"}">${iv === "4h" || iv === "1d" ? "长线" : "短线"}</span></span>
        <b>${s0 != null ? sc2(s0) : x && x.error ? "失败" : "…"}</b><span class="mx-l">${x && x.label ? esc(x.label) : ""}</span></button>`;
    }).join("")}</div>`;
  host.querySelectorAll(".mx-c[data-iv]").forEach((b) => (b.onclick = () => { I.iv = b.dataset.iv; indLoad(false); }));
}
/* 指标说明悬停：固定定位的浮层（不被列表裁切，靠边自动翻转） */
function indTipBind() {
  let tip = $("#indTip");
  if (!tip) { tip = document.createElement("div"); tip.id = "indTip"; tip.className = "ind-tip"; tip.setAttribute("role", "tooltip"); document.body.appendChild(tip); }
  const show = (el) => {
    tip.textContent = el.dataset.tip; tip.classList.add("on");
    const r = el.getBoundingClientRect(), W = innerWidth, H = innerHeight, tw = tip.offsetWidth, th = tip.offsetHeight;
    let x = r.left + r.width / 2 - tw / 2; x = Math.max(8, Math.min(x, W - tw - 8));
    let y = r.bottom + 8; if (y + th > H - 8) y = r.top - th - 8;
    tip.style.transform = `translate(${Math.round(x)}px,${Math.round(Math.max(8, y))}px)`;
  };
  const page = $("#page");
  page.onmouseover = (e) => { const el = e.target.closest(".ind-i"); if (el) show(el); };
  page.onmouseout = (e) => { if (e.target.closest(".ind-i")) tip.classList.remove("on"); };
  page.onfocusin = (e) => { const el = e.target.closest(".ind-i"); if (el) show(el); };
  page.onfocusout = () => tip.classList.remove("on");
}
