/* QTW 前端（无构建步骤的原生 JS 单页应用） */
const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const S = { status: null, dash: null, signals: null, bt: null, page: "dashboard", rSearch: "", txPage: 0, selSym: null };

const ICON = {
  home: '<path d="M4 11l8-7 8 7v8a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z"/>',
  signals: '<rect x="4" y="4" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.5"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.5"/>',
  backtest: '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4M16 3v4M4 10h16M8 15l2.5-2 2.5 2 3-3"/>',
  positions: '<circle cx="12" cy="12" r="8"/><path d="M12 4v8l5.6 5.6M12 12H4"/>',
  trades: '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h6M9 11h6M9 15h3"/>',
  risk: '<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1z"/>',
  help: '<circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1 .9-1 1.6V14M12 17h.01"/>',
  up: '<path d="M7 17L17 7M9 7h8v8"/>', down: '<path d="M7 7l10 10M17 9v8H9"/>',
  arrUp: '<path d="M12 19V5M6 11l6-6 6 6"/>', arrDown: '<path d="M12 5v14M6 13l6 6 6-6"/>',
  left: '<path d="M19 12H5M11 6l-6 6 6 6"/>', right: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  play: '<path d="M7 5l12 7-12 7z"/>', stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
  dl: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>', key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M17 6l3 3"/>',
};
const ic = (k, cls = "") => `<svg viewBox="0 0 24 24" class="${cls}">${ICON[k]}</svg>`;
const NAV = [
  ["dashboard", "home", "总览", "总览"], ["signals", "signals", "信号", "信号 / 进出场"], ["backtest", "backtest", "回测", "回测"], ["positions", "positions", "持仓", "持仓"],
  ["trades", "trades", "成交", "成交"], ["risk", "risk", "风控", "风控 / 自动交易"], ["settings", "settings", "设置", "行情源 / API / 实盘"], ["help", "help", "帮助", "帮助"],
];
const COIN = { BTC: "#f7931a", ETH: "#627eea", BNB: "#e0a800", SOL: "linear-gradient(135deg,#9945ff,#14f195)", XRP: "#23292f", ADA: "#0033ad", DOGE: "#c2a633", AVAX: "#e84142", LTC: "#345d9d", LINK: "#2a5ada", TRX: "#d8222a", DOT: "#e6007a" };
function coin(sym, cls = "") {
  const b = sym.replace(/USDT$/, "");
  let bg = COIN[b];
  if (!bg) { let h = 0; for (const c of b) h = (h * 31 + c.charCodeAt(0)) % 360; bg = `hsl(${h} 55% 45%)`; }
  return `<div class="coin ${cls}" style="background:${bg}">${esc(b.slice(0, 4))}</div>`;
}
const f2 = (x, d = 2) => (x == null || !isFinite(x) ? "—" : Number(x).toLocaleString("zh-CN", { minimumFractionDigits: d, maximumFractionDigits: d }));
const fp = (x, d = 6) => (x == null || !isFinite(x) ? "—" : Number(x).toPrecision(d).replace(/\.?0+$/, ""));
const pct = (x, d = 2) => (x == null || !isFinite(x) ? "—" : (x * 100).toFixed(d) + "%");
const sgn = (x, d = 2) => { if (x == null || !isFinite(x)) return "—"; if (Math.abs(x) < 0.5 * 10 ** -d) x = 0; return (x > 0 ? "+" : x < 0 ? "" : "±") + f2(x, d); };
const cls = (x) => (x > 0 ? "pos" : x < 0 ? "neg" : "");
const t = (iso) => (iso ? PT.short(iso) : "—");
const tFull = (iso, sec) => (iso ? PT.full(iso, sec) : "—");
/* 后端文案里的 ISO / 旧 PST / CST+8 时间统一改写成 “MM-DD HH:mm 北京时间” */
const ptText = (s) => String(s ?? "")
  .replace(/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})/g, (m) => PT.short(m))
  .replace(/\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})? P[SD]T/g, (m) => {
    const d = new Date(m.replace(" PST", " GMT-0800").replace(" PDT", " GMT-0700"));
    return isNaN(d) ? m : PT.short(d);
  })
  .replace(/\d{4}-(\d{2})-(\d{2}) (\d{2}):(\d{2})(?::\d{2})? (?:CST\+8|北京时间)/g, "$1-$2 $3:$4 北京时间");
const sideCn = (s) => ({ long: "做多", short: "做空", flat: "空仓" }[s] || s);
const mktCn = (m) => ({ spot: "现货", perp: "USDT 永续" }[m] || m);
const VN = { okx: "OKX", gate: "Gate.io" };
const base = (sym) => sym.replace(/USDT$/, "");

function toast(msg, err) { const el = $("#toast"); el.textContent = msg; el.className = "toast show" + (err ? " err" : ""); clearTimeout(el._t); el._t = setTimeout(() => (el.className = "toast"), 4200); }
async function api(path, opt = {}) {
  const o = { method: opt.method || "GET", headers: { "Content-Type": "application/json" } };
  if (opt.body !== undefined) o.body = JSON.stringify(opt.body);
  const r = await fetch(path, o);
  let j = null; try { j = await r.json(); } catch (_) {}
  if (!r.ok) throw new Error((j && (j.detail || j.message)) || `HTTP ${r.status}`);
  return j;
}
function modal(html, onMount) { $("#modalCard").innerHTML = html; $("#modal").classList.remove("hidden"); onMount && onMount($("#modalCard")); const f = $("#modalCard [data-ok], #modalCard .btn"); f && f.focus(); }
function closeModal() { $("#modal").classList.add("hidden"); }
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeModal(); });
function confirmBox(title, body, okText, danger) {
  return new Promise((res) => modal(`<h3>${title}</h3><div class="note" style="font-size:13px">${body}</div><div class="acts"><button class="btn ghost" data-x>取消</button><button class="btn ${danger ? "danger" : ""}" data-ok>${okText}</button></div>`,
    (m) => { m.querySelector("[data-x]").onclick = () => { closeModal(); res(false); }; m.querySelector("[data-ok]").onclick = () => { closeModal(); res(true); }; }));
}
/* 带感叹号的说明：鼠标悬停 / 键盘聚焦时展开格式化说明 */
const infoTip = (html, label = "说明") => `<span class="info" tabindex="0" role="button" aria-label="${label}">!<span class="pop" role="tooltip">${html}</span></span>`;

/* ---------- 外壳 ---------- */
function renderNav() {
  $("#sidebar").innerHTML = NAV.map(([id, icon, label, tip]) => `<button class="nav-item ${S.page === id ? "active" : ""}" data-go="${id}" aria-label="${label}" ${S.page === id ? 'aria-current="page"' : ""}>${ic(icon)}<span class="tip">${tip || label}</span></button>`).join("");
  $("#sidebar").querySelectorAll("[data-go]").forEach((b) => (b.onclick = () => (location.hash = "#/" + b.dataset.go)));
}
function greet() {
  const h = PT.hour();
  const g = h < 5 ? "夜深了" : h < 11 ? "早上好" : h < 13 ? "中午好" : h < 18 ? "下午好" : "晚上好";
  S.greeting = `${g}，kean`;
  if (S.page === "dashboard") $("#greet").textContent = S.greeting;
}
function renderTitle() {
  const n = NAV.find((x) => x[0] === S.page);
  $("#greet").textContent = S.page === "dashboard" ? S.greeting || "你好，kean" : n[2];
  $("#pageSub").textContent = (S.page === "dashboard" ? "" : `${S.greeting || "kean"} · `) + SUBS[S.page];
}
function renderMode() {
  const st = S.status; if (!st) return;
  const live = st.mode === "live", v = st.settings.venue;
  const b = $("#modeBadge");
  b.className = "stat-pill " + (live ? "live" : "paper");
  b.querySelector("span").textContent = live ? `实盘已开启 · ${VN[v]}` : "纸面模式";
  b.title = live ? "实盘已开启：订单会真实发送到交易所。点击查看运行状态" : "纸面模式：只在本地账本记账，不向交易所下单。点击查看运行状态";
  $("#shell").classList.toggle("live-on", live);
  document.querySelectorAll("[data-venue]").forEach((x) => {
    x.classList.toggle("on", x.dataset.venue === v); x.setAttribute("aria-pressed", x.dataset.venue === v);
    x.disabled = live; x.title = live ? "实盘开启时不能在这里切换交易所，请先到「设置」关闭实盘" : `使用 ${VN[x.dataset.venue]} 官方公共行情（仍为纸面）`;
  });
  const w = st.worker;
  $("#bellDot").className = "dot" + (w.last_error ? " warn" : "");
  $("#bellDot").style.display = w.running || w.last_error ? "" : "none";
  renderLivePill();
}
/* 行情源切换：只改公共行情来源，绝不开启实盘 */
async function setVenue(v) {
  if (!S.status || v === S.status.settings.venue) return;
  if (S.status.mode === "live") { toast("实盘开启中：请先到「设置」关闭实盘，再切换交易所", true); return; }
  try {
    await api("/api/settings", { method: "PUT", body: { venue: v } });
    toast(`行情源已切换为 ${VN[v]} · 仍为纸面模式，不下真实单`);
    S.signals = null; S.chart = null;
    await refreshAll();
    if (!["dashboard", "positions"].includes(S.page)) await PAGES[S.page]();
    api("/api/signals").then((r) => { S.signals = r; renderRight(); if (S.page === "dashboard") pageDashboard(); }).catch(() => {});
  } catch (e) { toast("切换失败：" + e.message, true); }
}
document.querySelectorAll("[data-venue]").forEach((b) => (b.onclick = () => setVenue(b.dataset.venue)));
async function runCycle(btn) {
  const b = btn || $("#runNowBtn"), orig = b.innerHTML; b.disabled = true; b.innerHTML = '<span class="spin"></span><span>运行中…</span>';
  try { const r = await api("/api/cycle", { method: "POST" }); toast(r.events.length ? r.events.join("；") : "已跑完一轮：无需调仓"); await refreshAll(); }
  catch (err) { toast("执行失败：" + err.message, true); }
  finally { b.disabled = false; b.innerHTML = orig; }
}
$("#runNowBtn").onclick = (e) => runCycle(e.currentTarget);
async function killSwitch() {
  if (!(await confirmBox("紧急停止", "将立即：<br>① 停止后台自动交易；② 关闭实盘开关并切回纸面；③ 按最新公共价格平掉<b>全部纸面持仓</b>。<br><br>本操作不会向交易所发送任何订单。", "立即停止并平仓", true))) return;
  try { const r = await api("/api/kill", { method: "POST" }); toast(r.events.length ? "已平仓：" + r.events.join("；") : "已停止，当前无持仓"); await refreshAll(); if (S.page === "risk") pageRisk(); }
  catch (e) { toast(e.message, true); }
}
$("#killBtn").onclick = killSwitch;
$("#alertGo").onclick = () => { setRail(false); location.hash = "#/signals"; };
const setRail = (open) => { $("#shell").classList.toggle("rail-open", open); $("#railBtn").setAttribute("aria-expanded", open); };
$("#railBtn").onclick = () => setRail(!$("#shell").classList.contains("rail-open"));
$("#railClose").onclick = () => setRail(false);
$("#railBackdrop").onclick = () => setRail(false);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") { setRail(false); closeModal(); } });
$("#rSearchBtn").onclick = () => { const i = $("#rSearch"); i.classList.toggle("hidden"); if (!i.classList.contains("hidden")) i.focus(); else { i.value = ""; S.rSearch = ""; renderRight(); } };
$("#rSearch").oninput = (e) => { S.rSearch = e.target.value.trim().toUpperCase(); renderRight(); };
$("#bellBtn").onclick = () => showStatusModal();
$("#modeBadge").onclick = () => showStatusModal();
$("#noticeBtn").onclick = () => showNotices();
function goSignal(sym, mkt) {
  S.selSym = sym; if (mkt && mkt !== "-") S.chartMkt = mkt;
  setRail(false);
  if (S.page === "signals") { selectSignal(sym); } else location.hash = "#/signals";
}

function showStatusModal() {
  const st = S.status, w = st.worker;
  modal(`<h3>运行状态</h3><dl class="kvlist">
    <dt>交易模式</dt><dd><b class="${st.mode === "live" ? "neg" : "pos"}">${st.mode === "live" ? "实盘（会真实下单）" : "纸面（只记账，不下单）"}</b></dd>
    <dt>行情源</dt><dd>${VN[st.settings.venue]} 官方公共行情</dd>
    <dt>自动交易</dt><dd><b>${w.running ? "运行中" : "已停止"}</b>${w.running ? ` · 每 ${st.settings.worker.interval_sec} 秒 · 下次约 ${w.next_run_in_sec ?? "—"} 秒后` : ""}</dd>
    <dt>上次执行</dt><dd>${tFull(w.last_run, true)}${w.last_error ? `<br><span class="neg">上次错误：${esc(w.last_error)}</span>` : ""}</dd>
    <dt>实盘闸门</dt><dd>${st.live_gate_open ? '<b class="neg">已打开</b>' : "关闭"}${st.live_block_reasons.length ? `<div class="muted" style="margin-top:4px">未满足：${st.live_block_reasons.map(esc).join("；")}</div>` : ""}</dd>
  </dl><div class="acts"><button class="btn ghost" data-close>关闭</button><button class="btn" data-risk>去风控页</button></div>`,
  (m) => { m.querySelector("[data-close]").onclick = closeModal; m.querySelector("[data-risk]").onclick = () => { closeModal(); location.hash = "#/risk"; }; });
}
function showNotices() {
  const r = S.dash?.worker?.last_result;
  const ev = r ? [...(r.events || []), ...Object.entries(r.errors || {}).map(([k, v]) => `${k}：${v}`)] : [];
  modal(`<h3>系统消息</h3><div class="note" style="font-size:13px;line-height:1.8">${ev.length ? ev.map((x) => "• " + esc(ptText(x))).join("<br>") : "最近一次自动周期没有新消息。"}
  <br><br>提示：这是系统化纸面 / 研究工具，不构成投资建议；实盘交易可能亏损全部本金。</div><div class="acts"><button class="btn" data-close>知道了</button></div>`, (m) => (m.querySelector("[data-close]").onclick = closeModal));
}

/* ---------- 右侧面板 ---------- */
const CHEV = '<svg class="chev" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>';
function renderRight() {
  const d = S.dash; if (!d) return;
  const q = S.rSearch;
  let html = "";
  if (d.positions.length) {
    $("#rTitle").textContent = "持仓";
    $("#railBtnLbl").textContent = `持仓 ${d.positions.length}`;
    $("#rSub").textContent = `${d.positions.length} 个纸面持仓 · 点击查看该币信号与 K 线`;
    html = d.positions.filter((p) => !q || p.symbol.includes(q)).sort((a, b) => b.weight - a.weight).map((p) => `
      <button class="r-row" data-sym="${p.symbol}" data-mkt="${p.market}" title="查看 ${base(p.symbol)} 的信号与 K 线">${coin(p.symbol)}<div><div class="nm">${base(p.symbol)}<span class="muted" style="font-weight:500"> /USDT</span></div>
      <div class="ds"><span class="side-tag ${p.side}">${sideCn(p.side)}</span> ${mktCn(p.market)}</div></div>
      <div class="rt">${pct(p.weight, 1)}<div class="ds ${cls(p.upnl)}">${sgn(p.upnl)}</div></div>${CHEV}</button>`).join("");
  } else {
    $("#rTitle").textContent = "关注币种";
    $("#railBtnLbl").textContent = "关注币种";
    $("#rSub").textContent = "当前空仓 · 点击查看信号与 K 线";
    const rows = S.signals?.rows || S.status.settings.symbols.map((s) => ({ symbol: s }));
    html = rows.filter((r) => !q || r.symbol.includes(q)).map((r) => {
      const lq = S.live && S.live.prices[r.symbol]; const m = r.market && r.market !== "-" ? r.market : "spot"; const v = lq && lq[m] ? lq[m].price : r.ref_price;
      return `<button class="r-row" data-sym="${r.symbol}" data-mkt="${r.signal_market || ""}" title="查看 ${base(r.symbol)} 的信号与 K 线">${coin(r.symbol)}<div><div class="nm">${base(r.symbol)}<span class="muted" style="font-weight:500"> /USDT</span></div>
      <div class="ds">${r.advice ? `<span class="side-tag ${r.side}">${sideCn(r.side)}</span> ${r.market !== "-" ? r.market_cn : ""}` : r.error ? "数据不可用" : "加载中…"}</div></div>
      <div class="rt num">${v ? fp(v) : ""}<div class="ds">${lq ? (m === "perp" ? "永续标记" : "现货最新") : ""}</div></div>${CHEV}</button>`;
    }).join("");
  }
  $("#rList").innerHTML = html || '<div class="empty">无匹配</div>';
  $("#rList").querySelectorAll("[data-sym]").forEach((el) => (el.onclick = () => goSignal(el.dataset.sym, el.dataset.mkt)));
  const st = S.status;
  let msg;
  if (st.mode === "live") msg = `⚠️ 实盘已开启<small>订单将真实发送到 ${VN[st.settings.venue]}，随时可按“紧急停止”。</small>`;
  else if (d.max_drawdown < -0.1) msg = `纸面回撤已达 ${pct(d.max_drawdown, 1)}<small>请检查风控参数，必要时紧急停止。</small>`;
  else if (S.signals) {
    const rows = S.signals.rows.filter((r) => !r.error);
    const L = rows.filter((r) => r.signal > 0).length, Sh = rows.filter((r) => r.signal < 0).length, F = rows.length - L - Sh;
    const pend = rows.filter((r) => r.state === "entry_pending").length;
    msg = `最新信号：${L} 多 · ${Sh} 空 · ${F} 空仓<small>${pend ? `${pend} 个等待入场 · ` : ""}基于 ${t(rows[0]?.as_of)} 收盘 K 线</small>`;
  } else msg = `${st.worker.running ? "自动交易运行中" : "自动交易未开启"}<small>默认纸面模式，可在风控页开启。</small>`;
  $("#rAlertText").innerHTML = msg;
}

/* ---------- 总览 ---------- */
const HEROWAVE = `<svg class="deco" viewBox="0 0 600 220" preserveAspectRatio="none"><path d="M330 0H600V90C540 140 500 40 440 80S360 70 330 0Z" fill="#5ee0d6" opacity=".22"/><circle cx="590" cy="210" r="120" fill="#6c5ce7" opacity=".35"/></svg>`;
function txRow(f) {
  const pnl = Number(f.realized_pnl_usdt), open = f.action === "open", buy = f.side === "buy";
  const title = `${base(f.symbol)} ${open ? "开" : "平"}${f.market === "spot" ? "多" : "空"}`;
  const amt = open ? `<b class="num">${f2(f.notional_usdt)}</b><small>名义 USDT</small>` : `<b class="num ${cls(pnl)}">${sgn(pnl)}</b><small>已实现 USDT</small>`;
  return `<button class="tx" data-sym="${f.symbol}" data-mkt="${f.market}" title="查看 ${base(f.symbol)} 的信号与 K 线">${coin(f.symbol)}
    <div class="tx-mid"><div class="ttl">${esc(title)} <span class="muted">· ${mktCn(f.market)}</span></div><div class="ds">${t(f.time)} · 价格 ${fp(f.price)} · ${esc(ptText(f.reason))}</div></div>
    <span class="badge ${buy ? "buy" : "sell"}">${buy ? "买入" : "卖出"}</span><div class="amt">${amt}</div>${CHEV}</button>`;
}
function sigRowAsTx(r) {
  return `<button class="tx" data-sym="${r.symbol}" data-mkt="${r.signal_market || ""}" title="查看 ${base(r.symbol)} 的信号与 K 线">${coin(r.symbol)}
    <div class="tx-mid"><div class="ttl">${base(r.symbol)} <span class="muted">· ${r.market !== "-" ? r.market_cn : "—"}</span></div><div class="ds">${esc(ptText(r.entry_timing))}</div></div>
    <span class="badge ${r.side}">${sideCn(r.side)}</span><div class="amt">${r.target_notional_usdt ? `<b class="num">${f2(r.target_notional_usdt)}</b><small>建议名义</small>` : "<b>—</b>"}</div>${CHEV}</button>`;
}
function pageDashboard() {
  const d = S.dash, st = S.status, v = st.settings.venue;
  const fills = d.recent_fills.slice(0, 6);
  const sigs = (S.signals?.rows || []).filter((r) => !r.error).slice(0, 5);
  const list = fills.length ? fills.map(txRow).join("") : sigs.length ? sigs.map(sigRowAsTx).join("") : '<div class="empty">尚无成交。点击右上角「跑一轮」执行一次系统化周期。</div>';
  const longN = d.positions.filter((p) => p.side === "long").reduce((a, p) => a + p.notional, 0);
  const shortN = d.positions.filter((p) => p.side === "short").reduce((a, p) => a + p.notional, 0);
  const cash = Math.abs(d.cash_free) < 0.005 ? 0 : d.cash_free;
  const realizedPnl = d.total_pnl - d.unrealized;
  const eqs = d.ledger.map((x) => x.equity); if (eqs.length) eqs.push(d.equity);
  const w = d.worker || st.worker;
  const curDD = d.drawdown.length ? d.drawdown[d.drawdown.length - 1] : 0;
  const cum = d.pnl_by_trade.reduce((a, x) => (a.push((a.at(-1) || 0) + x), a), []);
  const stat = (lbl, val, sub, c = "", extra = "") => `<div class="stat ${extra}"><div class="s-lbl">${lbl}</div><div class="s-val num ${c}">${val}</div><div class="s-sub">${sub}</div></div>`;
  $("#page").innerHTML = `
  <div class="dash">
    <section class="hero">${HEROWAVE}
      <div class="hero-main">
        <div class="h-lbl">纸面权益 · USDT</div>
        <div class="h-val num">${f2(d.equity)}</div>
        <div class="h-chg"><span class="chg ${d.total_pnl >= 0 ? "up" : "down"}">${sgn(d.total_pnl)} · ${d.total_return >= 0 ? "+" : ""}${pct(d.total_return)}</span><span>相对起始 ${f2(d.starting_equity, 0)} USDT</span></div>
      </div>
      <div class="hero-spark">${MiniCharts.spark(eqs)}<div class="cap">账本权益走势 · ${d.ledger.length} 个记录点</div></div>
    </section>
    <section class="stats">
      ${stat("可用现金", f2(cash), cash < 0 ? `<span class="explain">空头价格上涨后，持仓名义（${f2(d.gross, 0)}）已超过权益。这是亏损空头的正常记账，不是错误；回落前不会再开新仓。</span>` : "权益 − 持仓名义，可用于新开仓", cash < 0 ? "neg" : "", cash < 0 ? "warn" : "")}
      ${stat("持仓敞口", f2(d.gross, 0), `${d.positions.length} 个持仓 · 净敞口 ${sgn(d.net, 0)}`)}
      ${stat("未实现盈亏", sgn(d.unrealized), `已实现 ${sgn(realizedPnl)}（含手续费）`, cls(d.unrealized))}
    </section>
    <section class="panel tx-panel">
      <div class="sec-title"><div><h3>${fills.length ? "最近成交" : "当前信号预览"}</h3><div class="note">${fills.length ? `本周 ${d.week.fills} 笔 · 已实现 <span class="pos">+${f2(d.week.gains)}</span> / <span class="neg">${f2(d.week.losses)}</span> USDT · 点击查看该币 K 线` : "尚无成交 · 以下为系统化信号"}</div></div>
        <button class="link" data-go="${fills.length ? "trades" : "signals"}">${fills.length ? "全部成交" : "全部信号"} →</button></div>
      <div class="tx-list">${list}</div>
    </section>
    <section class="facts">
      <div class="tile"><div class="tt">最大回撤</div><div class="tv num ${d.max_drawdown < -0.1 ? "neg" : ""}">${pct(d.max_drawdown, 1)}</div><div class="tu">当前距高点 ${pct(curDD, 1)}</div><div class="tc">${MiniCharts.bars(d.drawdown.filter((_, i, a) => i % Math.max(1, Math.floor(a.length / 18)) === 0))}</div></div>
      <div class="tile"><div class="tt">胜率</div><div class="tv num">${d.win_rate == null ? "—" : pct(d.win_rate, 0)}</div><div class="tu">${d.closed_trades ? `${d.closed_trades} 笔已平仓 · 累计已实现` : "尚无平仓，持仓离场后统计"}</div><div class="tc">${cum.length > 1 ? MiniCharts.line(cum) : ""}</div></div>
      <div class="tile donut"><div class="tt">敞口构成</div>
        <div class="tc">${MiniCharts.donut([{ v: longN, c: "#5ee0d6" }, { v: shortN, c: "#4b3aa6" }, { v: Math.max(0, cash), c: "#ece8fd" }])}</div>
        <div class="legend"><div><i style="background:#5ee0d6"></i>现货多 ${f2(longN, 0)}</div><div><i style="background:#4b3aa6"></i>永续空 ${f2(shortN, 0)}</div><div><i style="background:#ece8fd"></i>现金 ${f2(Math.max(0, cash), 0)}</div></div></div>
      <div class="tile"><div class="tt">自动交易</div><div class="tv"><span class="pill ${w.running ? "long" : "flat"}">${w.running ? "运行中" : "已停止"}</span></div>
        <div class="tu" style="margin-top:8px">${w.running ? `每 ${st.settings.worker.interval_sec} 秒一轮 · 下次约 ${w.next_run_in_sec ?? "—"} 秒后` : "可在风控页开启"}<br>上次 ${t(w.last_run)}</div>
        <button class="btn ghost sm tile-act" data-go="risk">风控与自动交易 →</button></div>
    </section>
    <div class="note foot">系统化纸面 / 研究工具，不构成投资建议；实盘交易可能亏损全部本金。数据来自 ${VN[v]} 官方公共行情 · 更新于 ${tFull(d.time)}。</div>
  </div>`;
  bindGo();
  document.querySelectorAll("#page .tx[data-sym]").forEach((el) => (el.onclick = () => goSignal(el.dataset.sym, el.dataset.mkt)));
}
function bindGo() { document.querySelectorAll("#page [data-go]").forEach((el) => (el.onclick = () => (location.hash = "#/" + el.dataset.go))); }

/* ---------- 信号 / 进出场 ---------- */
const IV_SEC = { "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400 };
async function pageSignals() {
  const s = S.status.settings.strategy;
  $("#page").innerHTML = `
    <div class="panel chart-panel">
      <div class="chart-head">
        <div><h3 id="chartTitle">K 线与均线</h3><div class="note" id="chartSrc">加载中…</div></div>
        <div class="chart-ctl">
          <div class="seg" id="mktSeg" role="group" aria-label="市场"><button data-m="spot">现货</button><button data-m="perp">USDT 永续</button></div>
          <div class="seg" id="rangeSeg" role="group" aria-label="显示范围"><button data-r="7">1 周</button><button data-r="30">1 月</button><button data-r="all">全部</button></div>
        </div>
      </div>
      <div class="chart-box" id="candleChart"><div class="empty">加载中…</div></div>
      <div class="chart-legend"><span><i style="background:#2cc4c9"></i>快线 SMA${s.fast_ma}</span><span><i style="background:#6c5ce7"></i>慢线 SMA${s.slow_ma}</span><span>▲▼ 收盘确认的均线交叉</span><span class="muted">时间为北京时间 · 图表 TradingView Lightweight Charts™</span></div>
    </div>
    <div class="sec-title sig-title"><div><h3>当前信号与进出场建议</h3><div class="note">策略 ${esc(s.rule_id)}：${s.interval} 已收盘 K 线上 SMA${s.fast_ma} / SMA${s.slow_ma} 判断方向。做多用现货，做空用 USDT 永续（1 倍）。点击卡片在上方图表查看。</div></div>
      <a class="link" href="/api/export/signals.csv" title="下载全部信号 CSV">下载 CSV</a></div>
    <div class="sig-grid" id="sigGrid"><div class="empty">正在从 ${VN[S.status.settings.venue]} 公共行情计算信号…</div></div>`;
  document.querySelectorAll("#mktSeg [data-m]").forEach((b) => (b.onclick = () => { S.chartMkt = b.dataset.m; loadCandles(); }));
  document.querySelectorAll("#rangeSeg [data-r]").forEach((b) => (b.onclick = () => { S.chartRange = b.dataset.r; applyRange(); }));
  try { if (!S.signals) S.signals = await api("/api/signals"); } catch (e) { $("#sigGrid").innerHTML = `<div class="empty neg">信号计算失败：${esc(e.message)}</div>`; return; }
  renderRight();
  const rows = S.signals.rows;
  S.selSym = S.selSym && rows.some((r) => r.symbol === S.selSym) ? S.selSym : rows.find((r) => !r.error)?.symbol;
  const selRow = rows.find((r) => r.symbol === S.selSym);
  S.chartMkt = S.chartMkt || (selRow && selRow.signal_market) || "spot";
  renderSigGrid();
  loadCandles();
}
const STATE = { holding: ["持有中", "info"], entry_pending: ["待入场", "warn"], blocked: ["止损后观望", "flat"], flat: ["空仓观望", "flat"] };
const sigCn = (x) => (x > 0 ? "做多" : x < 0 ? "做空" : "空仓");
function renderSigGrid() {
  const g = $("#sigGrid"); if (!g || !S.signals) return;
  const open = new Set([...g.querySelectorAll("details[open]")].map((x) => x.dataset.sym));
  g.innerHTML = S.signals.rows.map((r) => r.error ? `<div class="sig">${coin(r.symbol)}<div class="note neg" style="margin-top:8px">${esc(r.symbol)}：${esc(r.error)}</div></div>` : `
    <article class="sig ${r.symbol === S.selSym ? "sel" : ""}" data-sym="${r.symbol}" tabindex="0" aria-label="${base(r.symbol)} 信号，点击在图表查看">
      <div class="hd">${coin(r.symbol, "lg")}<div><div class="nm">${base(r.symbol)}<span class="muted" style="font-weight:500">/USDT</span></div>
        <div class="px">${r.ref_price_kind === "mark" ? "永续标记价" : r.ref_price_kind === "last" ? "现货最新价" : "收盘价"} <b class="num" data-px="${r.symbol}:${r.market === "-" ? "spot" : r.market}">${fp(r.ref_price)}</b></div></div>
        <div class="verdict"><span class="badge lg ${r.side}">${sideCn(r.side)}</span><small>${r.market !== "-" ? r.market_cn : "不持仓"}</small></div></div>
      <div class="kv">
        <div><small>建议仓位</small><b class="num">${r.target_notional_usdt ? f2(r.target_notional_usdt, 0) + " U" : "—"}</b><em>${r.target_notional_usdt ? "占权益 " + pct(r.target_weight, 1) : "不开仓"}</em></div>
        <div><small>止损价</small><b class="num">${r.stop_price ? fp(r.stop_price) : "—"}</b><em>${r.risk_usdt ? "最多亏 " + f2(r.risk_usdt) + " U" : "—"}</em></div>
        <div><small>状态</small><b><span class="pill ${STATE[r.state][1]}">${STATE[r.state][0]}</span></b><em>${r.conflict ? "现货/永续冲突" : "&nbsp;"}</em></div>
      </div>
      <div class="tm"><p><i>入场</i><span>${esc(ptText(r.entry_timing))}</span></p><p><i>离场</i><span>${esc(ptText(r.exit_timing))}</span></p></div>
      <details data-sym="${r.symbol}" ${open.has(r.symbol) ? "open" : ""}><summary>详情</summary><div class="tm">
        <p><i>均线</i><span>快线 ${fp(r.sma_fast)} / 慢线 ${fp(r.sma_slow)}</span></p>
        <p><i>分市场</i><span>现货 ${sigCn(r.spot_signal)} · 永续 ${sigCn(r.perp_signal)}${r.conflict ? " → 冲突时空仓" : ""}</span></p>
        <p><i>仓位上限</i><span>${({ risk: "5% 单笔风险", weight: "20% 单币权重", gross: "总敞口 1×", none: "—" })[r.capped_by]}</span></p>
        <p><i>时间</i><span>信号截至 ${t(r.as_of)} 收盘 · 下次检查 ${t(r.next_check)}</span></p>
        <p><i>数据</i><span class="src">${esc(r.data_source)} · ${esc(r.source_host)} · 拉取 ${t(r.fetched_at)}${r.warning ? ` · <span class="neg">${esc(r.warning)}</span>` : ""}</span></p></div></details>
    </article>`).join("");
  g.querySelectorAll(".sig[data-sym]").forEach((el) => {
    el.onclick = (e) => { if (e.target.closest("details")) return; selectSignal(el.dataset.sym); };
    el.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); selectSignal(el.dataset.sym); } };
  });
}
function selectSignal(sym) {
  S.selSym = sym;
  const rr = S.signals?.rows.find((x) => x.symbol === sym); if (rr && rr.signal_market && rr.signal_market !== "-") S.chartMkt = rr.signal_market;
  document.querySelectorAll(".sig[data-sym]").forEach((x) => x.classList.toggle("sel", x.dataset.sym === sym));
  loadCandles();
  $("#page").scrollTo({ top: 0, behavior: "smooth" });
}
async function loadCandles() {
  const el = $("#candleChart"); if (!el || !S.selSym) return;
  const m = S.chartMkt || "spot", iv = S.status.settings.strategy.interval;
  document.querySelectorAll("#mktSeg [data-m]").forEach((b) => b.classList.toggle("on", b.dataset.m === m));
  $("#chartTitle").textContent = `${base(S.selSym)}/USDT · ${m === "perp" ? "USDT 永续" : "现货"} · ${iv} K 线`;
  const req = (S._candleReq = (S._candleReq || 0) + 1);
  try {
    const d = await api(`/api/candles?symbol=${S.selSym}&bars=300&market=${m}`);
    if (req !== S._candleReq || !document.body.contains(el)) return;
    S.chart = BigCharts.candles(el, d); S.chart._sym = S.selSym; S.chart._mkt = m; S.chart._iv = IV_SEC[iv] || 14400; S.chart._src = `${d.data_source} · ${d.source_host}`; S.chart._n = d.candles.length;
    S.chart._loadedAt = Date.now();
    applyRange(); applyForming(); renderChartSrc();
  } catch (e) { el.innerHTML = `<div class="empty neg">${esc(e.message)}</div>`; }
}
function applyRange() {
  const c = S.chart, r = S.chartRange || "30";
  document.querySelectorAll("#rangeSeg [data-r]").forEach((b) => b.classList.toggle("on", b.dataset.r === r));
  if (!c || !c._n) return;
  if (r === "all") { c.timeScale().fitContent(); return; }
  const bars = Math.round((+r * 86400) / c._iv);
  c.timeScale().setVisibleLogicalRange({ from: Math.max(0, c._n - bars), to: c._n + 2 });
}
function renderChartSrc() {
  const c = S.chart, el = $("#chartSrc"); if (!c || !el) return;
  const live = c._liveAt ? `实时更新于 ${PT.clock(new Date(c._liveAt))}:${String(new Date(c._liveAt).getSeconds()).padStart(2, "0")} 北京时间（${c._liveKind}）` : "等待实时推送…";
  el.innerHTML = `<span class="live-dot ${c._liveAt && Date.now() - c._liveAt < 30000 ? "on" : ""}"></span>${live} · ${c._n} 根已收盘 K 线来自 ${esc(c._src)}`;
}

/* ---------- 回测 ---------- */
async function pageBacktest() {
  const s = S.status.settings;
  $("#page").innerHTML = `
  <div class="panel" style="margin-bottom:18px"><div class="sec-title"><h3>回测参数</h3><span class="note">使用交易所真实公共历史 K 线 · 第 t 根收盘信号在第 t+1 根开盘成交（无前视）</span></div>
    <div class="bt-form">
      <label class="field">交易所<select id="btVenue"><option value="okx">OKX</option><option value="gate">Gate.io</option></select></label>
      <label class="field">K 线根数 (${s.strategy.interval})<input id="btBars" type="number" value="1500" min="200" max="5000"/></label>
      <label class="field">快线 SMA<input id="btFast" type="number" value="${s.strategy.fast_ma}"/></label>
      <label class="field">慢线 SMA<input id="btSlow" type="number" value="${s.strategy.slow_ma}"/></label>
      <label class="field">ATR 止损倍数<input id="btAtr" type="number" step="0.5" value="${s.strategy.atr_stop_mult}"/></label>
      <button class="btn" id="btRun" style="height:42px">${ic("play")}运行回测</button>
    </div></div>
  <div id="btOut">${S.bt?.summary ? "" : '<div class="empty">设置参数后点击“运行回测”。默认标的池 8 个主流币，首次拉取历史数据约需 20–40 秒。</div>'}</div>`;
  $("#btVenue").value = s.venue;
  $("#btRun").onclick = runBacktest;
  if (S.bt?.summary) renderBt();
  else { try { const l = await api("/api/backtest/latest"); if (l.summary) { S.bt = l; renderBt(); } } catch (_) {} }
}
async function runBacktest() {
  const b = $("#btRun"); b.disabled = true; b.innerHTML = '<span class="spin"></span> 回测中…';
  try {
    S.bt = await api("/api/backtest", { method: "POST", body: { venue: $("#btVenue").value, bars: +$("#btBars").value, fast_ma: +$("#btFast").value, slow_ma: +$("#btSlow").value, atr_stop_mult: +$("#btAtr").value } });
    renderBt(); toast("回测完成，CSV 已生成");
  } catch (e) { toast("回测失败：" + e.message, true); }
  finally { b.disabled = false; b.innerHTML = ic("play") + "运行回测"; }
}
function renderBt() {
  const r = S.bt, m = r.summary;
  const M = (k, v, c = "", f = false) => `<div class="metric ${f ? "feature" : ""}"><small>${k}</small><b class="num ${c}">${v}</b></div>`;
  $("#btOut").innerHTML = `
  <div class="metrics" style="margin-bottom:18px">
    ${M("总收益", pct(m.total_return), "", true)}${M("期末权益 (USDT)", f2(m.ending_equity_usdt))}${M("最大回撤", pct(m.max_drawdown), "neg")}${M("夏普比率（年化）", m.sharpe == null ? "—" : m.sharpe.toFixed(2))}
    ${M("胜率", pct(m.win_rate, 1))}${M("盈亏比", m.profit_factor == null ? "—" : m.profit_factor.toFixed(2))}${M("已平 / 持仓中", `${m.closed_trades} / ${m.open_trades}`)}${M(esc(m.benchmark), pct(m.benchmark_return), cls(m.benchmark_return))}
  </div>
  <div class="panel" style="padding:12px;margin-bottom:18px"><div class="sec-title" style="margin:4px 8px 8px"><h3>权益曲线与回撤</h3><span class="note">#${m.run_id ?? ""} ${esc((m.venue || "").toUpperCase())} · ${esc(m.interval)} · ${tFull(m.start_time)} → ${tFull(m.end_time)} · ${m.bars} 根 · 手续费 ${m.fee_bps} bps · 止损离场 ${m.stop_exits} 次<br>数据：${esc(m.data_source)} · ${esc(m.source_host)} · 拉取 ${tFull(m.fetched_at)} · 做多用${esc(m.long_prices)}，做空用${esc(m.short_prices)}${m.excluded_symbols ? " · 排除 " + esc(m.excluded_symbols) : ""}</span></div><div class="chart-box" id="eqChart"></div></div>
  <div class="panel"><div class="sec-title"><h3>回测成交（${r.trades.length}）</h3><div style="display:flex;gap:8px">
    <a class="btn ghost sm" href="/api/export/backtest_summary.csv">${ic("dl")}指标 CSV</a><a class="btn ghost sm" href="/api/export/backtest_equity.csv">${ic("dl")}权益 CSV</a><a class="btn ghost sm" href="/api/export/backtest_trades.csv">${ic("dl")}成交 CSV</a></div></div>
    <div class="tbl-wrap"><table class="tbl"><thead><tr><th>标的</th><th>方向</th><th>入场时间</th><th>入场价</th><th>离场时间</th><th>离场价</th><th>名义</th><th>盈亏</th><th>收益率</th><th>持有根数</th><th>离场原因</th></tr></thead><tbody>
    ${r.trades.slice().reverse().map((x) => `<tr><td><b>${x.symbol}</b></td><td><span class="pill ${x.side}">${sideCn(x.side)} · ${mktCn(x.market)}</span></td><td>${tFull(x.entry_time)}</td><td class="num">${fp(x.entry_price)}</td><td>${x.exit_time ? tFull(x.exit_time) : "—"}</td><td class="num">${fp(x.exit_price)}</td><td class="num">${f2(x.notional_usdt)}</td><td class="num ${cls(x.pnl_usdt)}">${sgn(x.pnl_usdt)}</td><td class="num ${cls(x.return_pct)}">${pct(x.return_pct)}</td><td class="num">${x.bars_held}</td><td>${esc(x.exit_reason)}</td></tr>`).join("")}
    </tbody></table></div>
    <div class="note" style="margin-top:10px">说明：全部为交易所官方公共接口的真实历史 K 线（做多=现货，做空=USDT 永续）；未计资金费率与滑点；历史表现不代表未来收益。生成于 ${tFull(r.generated_at)}，已存入 SQLite。</div></div>`;
  BigCharts.equity($("#eqChart"), r.equity);
}

/* ---------- 持仓 ---------- */
function pagePositions() {
  const d = S.dash;
  $("#page").innerHTML = `<div class="metrics" style="margin-bottom:18px"><div class="metric feature"><small>纸面权益</small><b class="num">${f2(d.equity)}</b></div><div class="metric"><small>可用现金</small><b class="num">${f2(d.cash_free)}</b></div><div class="metric"><small>总敞口 / 净敞口</small><b class="num">${f2(d.gross, 0)} / ${sgn(d.net, 0)}</b></div><div class="metric"><small>未实现盈亏</small><b class="num ${cls(d.unrealized)}">${sgn(d.unrealized)}</b></div></div>
  <div class="panel"><div class="sec-title"><h3>当前纸面持仓（${d.positions.length}）</h3><a class="btn ghost sm" href="/api/export/paper_positions.csv">${ic("dl")}导出 CSV</a></div>
  ${d.positions.length ? `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>标的</th><th>方向</th><th>数量</th><th>入场价</th><th>入场时间</th><th>最新价</th><th>止损价</th><th>名义</th><th>权重</th><th>未实现</th></tr></thead><tbody>
  ${d.positions.map((p) => `<tr><td><div style="display:flex;gap:10px;align-items:center">${coin(p.symbol)}<b>${p.symbol}</b></div></td><td><span class="pill ${p.side}">${sideCn(p.side)} · ${mktCn(p.market)}</span></td><td class="num">${fp(p.qty)}</td><td class="num">${fp(p.entry_price)}</td><td>${tFull(p.entry_time)}</td><td class="num">${fp(p.mark_price)}<br><small class="muted">${esc(p.mark_source || "—")}</small></td><td class="num">${fp(p.stop_price)}</td><td class="num">${f2(p.notional)}</td><td class="num">${pct(p.weight, 1)}</td><td class="num ${cls(p.upnl)}">${sgn(p.upnl)}</td></tr>`).join("")}</tbody></table></div>`
  : '<div class="empty">当前空仓。开启自动交易或点击右上角「跑一轮」执行一次系统化周期。</div>'}
  <div class="note" style="margin-top:10px">纸面账本持久化保存在 data/qtw.sqlite（重启不丢失；CSV 仅为导出）。永续空头按 1 倍保证金计，占用等额现金。</div></div>`;
}

/* ---------- 成交 ---------- */
async function pageTrades() {
  $("#page").innerHTML = '<div class="empty">加载中…</div>';
  const [fills, orders] = await Promise.all([api("/api/fills"), api("/api/orders")]);
  $("#page").innerHTML = `<div class="panel" style="margin-bottom:18px"><div class="sec-title"><h3>纸面成交（${fills.length}）</h3><div style="display:flex;gap:8px"><a class="btn ghost sm" href="/api/export/paper_fills.csv">${ic("dl")}成交 CSV</a><a class="btn ghost sm" href="/api/export/paper_ledger.csv">${ic("dl")}账本 CSV</a></div></div>
  ${fills.length ? `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>#</th><th>时间</th><th>标的</th><th>市场</th><th>买卖</th><th>开/平</th><th>数量</th><th>价格</th><th>价格来源</th><th>名义</th><th>手续费</th><th>已实现</th><th>原因</th></tr></thead><tbody>
  ${fills.map((f) => `<tr><td>${f.fill_id}</td><td>${tFull(f.time)}</td><td><b>${f.symbol}</b></td><td>${mktCn(f.market)}</td><td class="${f.side === "buy" ? "pos" : "neg"}">${f.side === "buy" ? "买入" : "卖出"}</td><td>${f.action === "open" ? "开仓" : "平仓"}</td><td class="num">${fp(+f.qty)}</td><td class="num">${fp(+f.price)}</td><td>${esc(f.price_kind)}</td><td class="num">${f2(+f.notional_usdt)}</td><td class="num">${f2(+f.fee_usdt, 4)}</td><td class="num ${cls(+f.realized_pnl_usdt)}">${sgn(+f.realized_pnl_usdt, 4)}</td><td>${esc(f.reason)}</td></tr>`).join("")}</tbody></table></div>` : '<div class="empty">暂无成交</div>'}</div>
  <div class="panel"><div class="sec-title"><h3>订单路由日志</h3><span class="note">纸面 = 仅记账；实盘被拦截时会列出未满足的闸门</span></div>
  ${orders.length ? `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>时间</th><th>模式</th><th>交易所</th><th>标的</th><th>动作</th><th>数量</th><th>参考价</th><th>状态</th><th>说明</th></tr></thead><tbody>
  ${orders.map((o) => `<tr><td>${tFull(o.time)}</td><td>${o.mode === "live" ? '<span class="pill short">实盘</span>' : '<span class="pill info">纸面</span>'}</td><td>${esc(o.venue.toUpperCase())}</td><td>${esc(o.symbol)}</td><td>${esc(o.action)}</td><td class="num">${fp(+o.qty)}</td><td class="num">${fp(+o.ref_price)}</td><td>${esc(o.status)}</td><td style="white-space:normal;max-width:320px">${esc(o.detail)}</td></tr>`).join("")}</tbody></table></div>` : '<div class="empty">暂无记录</div>'}</div>`;
}

/* ---------- 风控 / 自动交易 ---------- */
function pageRisk() {
  const s = S.status.settings, w = S.status.worker;
  $("#page").innerHTML = `
  <div class="grid risk-top">
    <div class="panel"><div class="sec-title"><h3>自动交易 <span class="muted" style="font-weight:500;font-size:13px">纸面执行</span>${infoTip("<b>后台循环每隔设定秒数：</b><ol><li>拉取 OKX / Gate 官方公共行情</li><li>用已收盘 K 线计算信号</li><li>检查止损</li><li>在<b>纸面账本</b>按最新价调仓</li></ol>实盘只有在「设置」页通过全部闸门后才会发单。", "自动交易说明")}</h3>
        <span class="pill ${w.running ? "long" : "flat"}">${w.running ? "运行中" : "已停止"}</span></div>
      <div class="worker-row">
        <label class="field" style="width:150px">检查间隔（秒）<input id="wInt" type="number" min="60" value="${s.worker.interval_sec}"/></label>
        <button class="btn ${w.running ? "stop" : "go"}" id="wToggle" aria-pressed="${w.running}">${w.running ? ic("stop") + "停止自动交易" : ic("play") + "开启自动交易"}</button>
        <button class="btn ghost" id="cycleNow" title="手动跑一轮系统化周期（纸面）">${ic("play")}跑一轮</button>
      </div>
      <div class="note" style="margin-top:12px">上次执行：${tFull(w.last_run, true)}${w.running ? ` · 下次约 ${w.next_run_in_sec ?? "—"} 秒后` : ""}${w.last_error ? `<br><span class="neg">错误：${esc(w.last_error)}</span>` : ""}</div>
    </div>
    <div class="panel danger-panel"><div class="sec-title"><h3>紧急操作</h3></div>
      <div class="danger-acts">
        <div class="da"><button class="btn danger" id="killBig">${ic("stop")}紧急停止</button>${infoTip("<b>紧急停止（Kill Switch）</b><ul><li>停止后台自动交易</li><li>关闭实盘开关，切回纸面</li><li>按最新公共价<b>平掉全部纸面持仓</b></li></ul>不会向交易所发送任何订单。点击后还会再确认一次。", "紧急停止说明")}</div>
        <div class="da"><button class="btn ghost danger-ghost" id="resetPaper">重置纸面账本</button>${infoTip("<b>重置纸面账本</b><ul><li>清空全部纸面持仓、成交与账本历史</li><li>恢复起始资金（当前 " + f2(s.risk.starting_equity_usdt, 0) + " USDT）</li><li>需先停止自动交易</li></ul>点击后还会再确认一次。", "重置说明")}</div>
      </div></div>
  </div>
  <div class="panel" style="margin-top:18px"><div class="sec-title"><h3>风控规则</h3><span class="note">上限只能调低，不能调高</span></div>
    <div class="grid form4">
      <label class="field">起始纸面资金 (USDT)<input id="rEq" type="number" value="${s.risk.starting_equity_usdt}"/><span class="hint">重置账本后生效</span></label>
      <label class="field">单笔最大风险<input id="rRisk" type="number" step="0.005" max="0.05" value="${s.risk.max_risk_per_trade}"/><span class="hint">≤ 0.05（5%）</span></label>
      <label class="field">单币最大权重<input id="rW" type="number" step="0.01" max="0.2" value="${s.risk.max_weight_per_name}"/><span class="hint">≤ 0.20（20%）</span></label>
      <label class="field">手续费假设 (bps)<input id="rFee" type="number" step="0.5" value="${s.fees.taker_bps}"/><span class="hint">默认 taker 4 bps</span></label>
    </div>
    <div style="display:flex;gap:28px;margin-top:16px;flex-wrap:wrap;align-items:center">
      <label class="toggle"><input type="checkbox" id="rSpot" ${s.risk.allow_spot_long ? "checked" : ""}/><span class="tr"></span>允许现货做多</label>
      <label class="toggle"><input type="checkbox" id="rPerp" ${s.risk.allow_perp_short ? "checked" : ""}/><span class="tr"></span>允许永续做空</label>
      <span class="note">固定：永续 1 倍杠杆 · 总敞口 ≤ 1× 权益</span>
    </div></div>
  <div class="panel" style="margin-top:18px"><div class="sec-title"><h3>策略参数 · ${esc(s.strategy.rule_id)}</h3></div>
    <div class="grid form5">
      <label class="field">K 线周期<select id="sInt">${["15m", "1h", "4h", "1d"].map((x) => `<option ${x === s.strategy.interval ? "selected" : ""}>${x}</option>`).join("")}</select></label>
      <label class="field">快线 SMA<input id="sFast" type="number" value="${s.strategy.fast_ma}"/></label>
      <label class="field">慢线 SMA<input id="sSlow" type="number" value="${s.strategy.slow_ma}"/></label>
      <label class="field">ATR 周期<input id="sAtrP" type="number" value="${s.strategy.atr_period}"/></label>
      <label class="field">ATR 止损倍数<input id="sAtr" type="number" step="0.5" value="${s.strategy.atr_stop_mult}"/></label>
    </div></div>
  <div class="panel" style="margin-top:18px"><div class="sec-title"><h3>标的池（USDT 交易对）</h3></div>
    <div class="chips" id="chips"></div>
    <div style="display:flex;gap:10px;margin-top:14px"><input id="addSym" class="r-search" style="margin:0;width:220px" placeholder="例如 LINK 或 LINKUSDT" aria-label="添加交易对"/><button class="btn ghost sm" id="addSymBtn">添加</button></div></div>
  <div class="savebar" id="saveBar"><span class="note" id="saveHint">修改上面的参数后，点「保存设置」才会生效。</span><button class="btn" id="saveRisk">保存设置</button></div>`;
  let syms = [...s.symbols];
  const dirty = () => { $("#saveBar").classList.add("dirty"); $("#saveHint").textContent = "有未保存的修改"; };
  const chips = () => { $("#chips").innerHTML = syms.map((x) => `<span class="c">${coin(x)}${x}<button data-rm="${x}" title="移除 ${x}" aria-label="移除 ${x}">×</button></span>`).join(""); document.querySelectorAll("[data-rm]").forEach((b) => (b.onclick = () => { syms = syms.filter((x) => x !== b.dataset.rm); chips(); dirty(); })); };
  chips();
  document.querySelectorAll("#page .panel input:not(#addSym), #page .panel select").forEach((i) => i.addEventListener("input", dirty));
  const add = () => { let v = $("#addSym").value.trim().toUpperCase().replace(/[-_/]/g, ""); if (!v) return; if (!v.endsWith("USDT")) v += "USDT"; if (!syms.includes(v)) { syms.push(v); dirty(); } $("#addSym").value = ""; chips(); };
  $("#addSymBtn").onclick = add; $("#addSym").onkeydown = (e) => { if (e.key === "Enter") add(); };
  $("#saveRisk").onclick = async () => {
    const b = $("#saveRisk"); b.disabled = true;
    try {
      await api("/api/settings", { method: "PUT", body: { symbols: syms, worker: { interval_sec: +$("#wInt").value },
        risk: { starting_equity_usdt: +$("#rEq").value, max_risk_per_trade: +$("#rRisk").value, max_weight_per_name: +$("#rW").value, allow_spot_long: $("#rSpot").checked, allow_perp_short: $("#rPerp").checked },
        fees: { taker_bps: +$("#rFee").value },
        strategy: { interval: $("#sInt").value, fast_ma: +$("#sFast").value, slow_ma: +$("#sSlow").value, atr_period: +$("#sAtrP").value, atr_stop_mult: +$("#sAtr").value } } });
      toast("设置已保存"); S.signals = null; await refreshAll(); pageRisk();
    } catch (e) { toast("保存失败：" + e.message, true); b.disabled = false; }
  };
  $("#wToggle").onclick = async (e) => {
    const b = e.currentTarget; b.disabled = true;
    try {
      if (S.status.worker.running) { await api("/api/worker/stop", { method: "POST" }); toast("自动交易已停止"); }
      else { await api("/api/settings", { method: "PUT", body: { worker: { interval_sec: +$("#wInt").value } } }); await api("/api/worker/start", { method: "POST" }); toast("自动交易已开启（纸面执行）"); }
      await refreshAll(); pageRisk();
    } catch (er) { toast(er.message, true); b.disabled = false; }
  };
  $("#cycleNow").onclick = (e) => runCycle(e.currentTarget);
  $("#killBig").onclick = killSwitch;
  $("#resetPaper").onclick = async () => { if (!(await confirmBox("重置纸面账本", "将清空全部纸面持仓、成交与账本历史，并恢复起始资金。", "确认重置", true))) return; try { await api("/api/paper/reset", { method: "POST" }); toast("纸面账本已重置"); refreshAll(); } catch (e) { toast(e.message, true); } };
}

/* ---------- API / 设置 ---------- */
const KEYWAVE = `<svg class="deco" viewBox="0 0 400 170" preserveAspectRatio="none"><path d="M0 0H400V50C340 90 300 20 240 50S140 150 60 110 0 90 0 90Z" fill="#5ee0d6" opacity=".85"/></svg>`;
function pageSettings() {
  const st = S.status, s = st.settings, v = st.vault, live = st.mode === "live";
  const kc = (ex, name) => `<div class="keycard">${KEYWAVE}<h4>${name}</h4><div class="st">${v[ex].configured ? "已加密保存（AES / Fernet）" : "未配置 · 不影响行情、回测与纸面交易"}</div>
     <div class="masked">${v[ex].configured ? esc(v[ex].api_key_masked) : "•••• •••• •••• ••••"}</div><div class="st">Secret ${v[ex].secret_set ? "已保存（不可回显）" : "未保存"}${ex === "okx" ? ` · Passphrase ${v.okx.passphrase_set ? "已保存" : "未保存"}` : ""}</div></div>`;
  $("#page").innerHTML = `
  <div class="panel"><div class="sec-title"><h3>行情源</h3></div>
    <div class="venue-row"><div class="venue big" role="group" aria-label="行情源">${["okx", "gate"].map((x) => `<button type="button" data-v2="${x}" class="${s.venue === x ? "on" : ""}" ${live ? "disabled" : ""}>${VN[x]}</button>`).join("")}</div>
    <div class="note">信号、K 线和纸面账本的计价都来自这里选择的交易所官方<b>公共</b>行情，不需要 API Key，切换后仍是纸面模式。${live ? '<br><span class="neg">实盘开启时不能切换，请先在下方关闭实盘。</span>' : "只有在下方实盘开关通过全部闸门后，才会用它下真实单。"}</div></div></div>
  <div class="grid two-col" style="margin-top:18px">
    <div class="panel">
      ${kc("okx", "OKX API 密钥")}
      <div class="grid" style="margin-top:16px">
        <label class="field">API Key<input id="okKey" autocomplete="off" placeholder="${v.okx.configured ? "留空 = 保持不变" : "粘贴 API Key"}"/></label>
        <label class="field">Secret Key<input id="okSec" type="password" autocomplete="new-password" placeholder="${v.okx.secret_set ? "留空 = 保持不变" : "粘贴 Secret"}"/></label>
        <label class="field">Passphrase<input id="okPass" type="password" autocomplete="new-password" placeholder="${v.okx.passphrase_set ? "留空 = 保持不变" : "创建 API 时设置的口令"}"/></label>
        <label class="toggle"><input type="checkbox" id="okDemo" ${s.live.okx_demo ? "checked" : ""}/><span class="tr"></span>使用 OKX 模拟盘环境</label>
        <div class="form-acts"><button class="btn" data-save="okx">${ic("key")}加密保存</button><button class="btn ghost" data-test="okx">只读连接测试</button><button class="btn ghost danger-ghost" data-del="okx">删除密钥</button></div>
      </div></div>
    <div class="panel">
      ${kc("gate", "Gate.io API 密钥")}
      <div class="grid" style="margin-top:16px">
        <label class="field">API Key<input id="gtKey" autocomplete="off" placeholder="${v.gate.configured ? "留空 = 保持不变" : "粘贴 API Key"}"/></label>
        <label class="field">Secret Key<input id="gtSec" type="password" autocomplete="new-password" placeholder="${v.gate.secret_set ? "留空 = 保持不变" : "粘贴 Secret"}"/></label>
        <label class="toggle"><input type="checkbox" id="gtTest" ${s.live.gate_testnet ? "checked" : ""}/><span class="tr"></span>使用 Gate 合约测试网（现货无测试网）</label>
        <div class="note">建议创建 API 时只勾选“交易 + 读取”，<b>不要开启提现权限</b>，并绑定 IP 白名单。</div>
        <div class="form-acts"><button class="btn" data-save="gate">${ic("key")}加密保存</button><button class="btn ghost" data-test="gate">只读连接测试</button><button class="btn ghost danger-ghost" data-del="gate">删除密钥</button></div>
      </div></div>
  </div>
  <div class="note" style="margin:12px 4px 0">密钥以 Fernet（AES-128 + HMAC）加密保存在 <b>data/secrets.enc</b>；主密钥来源：<b>${st.vault.key_source === "passphrase" ? "环境变量 QTW_MASTER_PASSPHRASE（scrypt 派生，不落盘）" : "本地密钥文件 data/vault.key（权限 600）"}</b>。密钥不写入数据库、CSV 或日志，页面只显示掩码。${st.vault.error ? `<br><span class="neg">${esc(st.vault.error)}</span>` : ""}</div>
  <div class="live-box" style="margin-top:18px">
    <h4>⚠️ 实盘交易开关（默认关闭）</h4>
    <div class="note" style="color:#7b3141">实盘交易可能亏损全部资金。本工具是系统化研究 / 纸面工具，不构成投资建议。开启需同时满足：模式=实盘、开关打开、输入确认语、启动时设置 <b>QTW_ALLOW_LIVE_ORDERS=1</b>、对应交易所密钥完整。任何一项不满足，订单只会被记录为“blocked”。</div>
    <div style="display:flex;gap:14px;align-items:end;margin-top:14px;flex-wrap:wrap">
      <label class="field" style="flex:1;min-width:280px">确认语（请完整输入：${esc(st.confirm_phrase_required)}）<input id="livePhrase" autocomplete="off" placeholder="${esc(st.confirm_phrase_required)}"/></label>
      ${st.settings.live.live_enabled ? '<button class="btn" id="liveOff">关闭实盘，回到纸面</button>' : '<button class="btn danger" id="liveOn">开启实盘模式</button>'}
    </div>
    <ul class="reasons">${st.live_block_reasons.length ? st.live_block_reasons.map((r) => `<li>${esc(r)}</li>`).join("") : "<li><b>全部闸门已通过：订单会真实发送！</b></li>"}</ul>
  </div>`;
  document.querySelectorAll("[data-v2]").forEach((b) => (b.onclick = () => setVenue(b.dataset.v2)));
  document.querySelectorAll("[data-save]").forEach((b) => (b.onclick = async () => {
    const ex = b.dataset.save;
    const body = ex === "okx" ? { api_key: $("#okKey").value, secret: $("#okSec").value, passphrase: $("#okPass").value } : { api_key: $("#gtKey").value, secret: $("#gtSec").value };
    try {
      await api(`/api/keys/${ex}`, { method: "PUT", body });
      await api("/api/live", { method: "PUT", body: { okx_demo: $("#okDemo").checked, gate_testnet: $("#gtTest").checked, confirm_phrase: S.status.settings.live.confirm_phrase } });
      toast("已加密保存（页面不会回显完整密钥）"); await refreshStatus(); pageSettings();
    } catch (e) { toast(e.message, true); }
  }));
  document.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => { if (!(await confirmBox("删除密钥", `删除本地保存的 ${VN[b.dataset.del]} 密钥？`, "删除", true))) return; await api(`/api/keys/${b.dataset.del}`, { method: "DELETE" }); toast("已删除"); await refreshStatus(); pageSettings(); }));
  document.querySelectorAll("[data-test]").forEach((b) => (b.onclick = async () => { try { const r = await api(`/api/keys/${b.dataset.test}/test`, { method: "POST" }); toast(r.message, !r.ok); } catch (e) { toast(e.message, true); } }));
  $("#liveOn") && ($("#liveOn").onclick = async () => {
    if (!(await confirmBox("开启实盘模式？", "开启后，自动交易产生的调仓会尝试向交易所发送<b>真实订单</b>（仍需启动时设置 QTW_ALLOW_LIVE_ORDERS=1）。确定继续？", "我已了解风险，开启", true))) return;
    try { await api("/api/live", { method: "PUT", body: { mode: "live", live_enabled: true, confirm_phrase: $("#livePhrase").value.trim() } }); toast("实盘模式已开启"); await refreshStatus(); pageSettings(); } catch (e) { toast(e.message, true); }
  });
  $("#liveOff") && ($("#liveOff").onclick = async () => { await api("/api/live", { method: "PUT", body: { mode: "paper", live_enabled: false } }); toast("已回到纸面模式"); await refreshStatus(); pageSettings(); });
}

/* ---------- 帮助 ---------- */
function pageHelp() {
  const st = S.status.settings, s = st.strategy;
  $("#page").innerHTML = `<div class="panel help">
  <section class="lead"><h4 style="margin-top:0">这是什么</h4><p>面向 kean 的系统化加密货币交易控制台：只用 OKX / Gate.io 官方<b>公共</b>行情（<b>无需 API Key</b>）做信号、回测与纸面交易；配置密钥后可在严格闸门下接入实盘。所有价格都来自交易所实时接口，<b>不使用任何模拟 / 伪造数据</b>，请求失败会直接报错。<b>这是系统化纸面 / 研究工具，不构成投资建议；实盘交易可能亏损全部本金。</b></p></section>
  <section><h4>顶部栏</h4><ul><li><b>纸面模式 / 实盘已开启</b>：当前交易模式，点击查看运行状态。</li><li><b>实时 · OKX</b>：行情连接状态（实时 / 部分重连 / 恢复中 / REST 兜底 / 数据延迟 / 中断），点击看每条连接。</li><li><b>行情源 OKX | Gate</b>：只切换公共行情来源，始终保持纸面。开启实盘只能在「设置」页完成。</li><li><b>跑一轮</b>：立即执行一次系统化周期（纸面调仓）。</li></ul></section>
  <section><h4>策略 · ${esc(s.rule_id)}</h4><ul>
  <li>现货与 USDT 永续<b>各自</b>在自己已收盘的 ${s.interval} K 线上计算 SMA${s.fast_ma} / SMA${s.slow_ma}。</li>
  <li>现货看多且永续不看空 → <b>做多·现货</b>；永续看空且现货不看多 → <b>做空·USDT 永续</b>（1 倍）；两者冲突或无信号 → 空仓。</li>
  <li>离场：收盘出现反向或归零信号，或价格触及 <b>${s.atr_stop_mult}×ATR${s.atr_period}</b> 止损；止损后等信号方向改变才再入场。</li></ul></section>
  <section><h4>仓位与风控</h4><ul><li>风险预算 = 权益 × ${pct(st.risk.max_risk_per_trade, 0)}；名义 = 风险预算 ÷ 止损百分比。</li><li>单币名义 ≤ 权益 × ${pct(st.risk.max_weight_per_name, 0)}；总敞口 ≤ 1× 权益，同时入场按比例缩放。</li><li>永续空头按 1 倍保证金占用现金；空头价格上涨时名义会超过权益，可用现金显示为负属正常记账，此时不会开新仓。</li></ul></section>
  <section><h4>页面</h4><ul><li><b>总览</b>：权益、现金 / 敞口 / 未实现、最近成交、回撤与胜率。</li><li><b>信号</b>：K 线实时图与每个币的做多 / 做空 / 空仓建议、仓位、止损。</li><li><b>回测</b>：真实历史 K 线回测与 CSV 导出。</li><li><b>持仓 / 成交</b>：纸面账本与订单日志。</li><li><b>风控</b>：自动交易开关、紧急停止、参数与标的池。</li><li><b>设置</b>：行情源、加密密钥、实盘闸门。</li></ul></section>
  <section><h4>数据与时间</h4><ul><li>所有时间按 <b>Asia/Shanghai（北京时间）</b> 显示。</li><li>数据库：<code>data/qtw.sqlite</code>；API 密钥只存在加密文件 <code>data/secrets.enc</code>。</li><li>CSV 导出：<code>output/</code> 与 <code>output/backtest/</code>。图表：TradingView Lightweight Charts™。</li></ul></section>
  <section><h4>局限</h4><ul><li>回测未计资金费率与滑点；历史表现不代表未来。</li><li>实盘模式没有与交易所持仓对账；实盘前请先在 OKX 模拟盘 / Gate 合约测试网验证。</li><li>按 <code>Esc</code> 关闭弹窗 / 右侧抽屉。</li></ul></section></div>`;
}

/* ---------- 实时推送（SSE：后端订阅 OKX / Gate 官方公共 WebSocket） ---------- */
function applyForming() {
  const c = S.chart, L = S.live; if (!c || !L || !c._candle || !document.body.contains($("#candleChart"))) return;
  if (L.venue !== S.status.settings.venue) return;
  const f = L.forming[`${L.interval}:${c._sym}:${c._mkt}`];
  if (!f) return;
  if (f.time > c._last + c._iv && Date.now() - (c._loadedAt || 0) > 20000) { loadCandles(); return; } // 上一根已收盘：重新拉取以更新均线与标记
  if (f.time >= c._last) {
    try { c._candle.update({ time: f.time, open: f.open, high: f.high, low: f.low, close: f.close }); c._last = f.time; c._liveAt = Date.now(); c._liveKind = /_ws$/.test(f.source || "") ? "WebSocket" : "REST"; } catch (_) {}
  }
  renderChartSrc();
}
/* 行情状态：实时 / 部分重连 / 恢复中 / REST 兜底 / 数据延迟 / 中断 */
function liveState() {
  const L = S.live, st = S.status;
  const src = L ? { mode: L.stream.mode, conns: L.connections, venue: L.venue, n: L.stream.quotes_ws_fresh, rest: L.stream.quotes_rest_fresh }
    : st && st.stream ? { mode: st.stream.mode, conns: st.stream.connections, venue: st.settings.venue, n: st.stream.quotes_ws_fresh, rest: st.stream.quotes_rest_fresh } : null;
  if (!src) return ["wait", "行情连接中…"];
  const V = VN[src.venue] || src.venue;
  if (S.esDown) return ["warn", `重连中 · ${V}`];
  if (L && S.liveAt && Date.now() - S.liveAt > 30000) return ["bad", `数据延迟 · ${Math.round((Date.now() - S.liveAt) / 1000)} 秒无更新`];
  const mine = (src.conns || []).filter((c) => c.name.startsWith(src.venue));
  if (src.mode === "ws") return mine.length && mine.every((c) => c.status === "connected") ? ["ok", `实时 · ${V}`] : ["warn", `实时 · ${V} 部分重连`];
  // WS sockets reconnecting / quote gap filled by REST — not a full REST-only fallback
  if (src.mode === "recovering") return ["warn", `恢复中 · ${V}`];
  if (src.mode === "rest") return ["warn", `REST 兜底 · ${V}`];
  return ["bad", `行情中断 · ${V}`];
}
function renderLivePill() {
  const el = $("#livePill"); if (!el) return;
  const [c, txt] = liveState();
  el.className = "stat-pill " + c; el.querySelector("span").textContent = txt;
}
function applyLive() {
  const L = S.live; if (!L) return;
  renderLivePill();
  if (S.dash && L.paper) {
    Object.assign(S.dash, { equity: L.paper.equity, unrealized: L.paper.unrealized, gross: L.paper.gross, net: L.paper.net,
      total_pnl: L.paper.total_pnl, total_return: L.paper.total_pnl / S.dash.starting_equity });
    S.dash.cash_free = Math.abs(L.paper.equity - L.paper.gross) < 0.005 ? 0 : L.paper.equity - L.paper.gross;
    S.dash.positions.forEach((p) => { const q = L.paper.positions[p.symbol]; if (q) Object.assign(p, { mark_price: q.mark, mark_time: q.mark_time, upnl: q.upnl, weight: q.weight, notional: q.notional }); });
  }
  if (S.signals && L.venue === S.status?.settings.venue) S.signals.rows.forEach((r) => { const q = L.prices[r.symbol]; const m = r.market === "-" ? "spot" : r.market; if (q && q[m]) r.ref_price = q[m].price; });
  document.querySelectorAll("[data-px]").forEach((el) => {
    const [sym, m] = el.dataset.px.split(":"); const q = L.prices[sym] && L.prices[sym][m];
    if (q) { const tx = fp(q.price); if (el.textContent !== tx) { el.textContent = tx; el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); } }
  });
  renderRight();
  applyForming();
  const now = Date.now();
  if ((S.page === "dashboard" || S.page === "positions") && now - (S._lastLiveRender || 0) > 5000 && !$("#modal:not(.hidden)") && !document.querySelector("#page :hover:is(button,a)")) {
    S._lastLiveRender = now; PAGES[S.page]();
  }
}
function connectLive() {
  try {
    const es = new EventSource("/api/stream");
    es.addEventListener("tick", (e) => { try { S.live = JSON.parse(e.data); S.liveAt = Date.now(); S.esDown = false; applyLive(); } catch (_) {} });
    es.onopen = () => { S.esDown = false; renderLivePill(); };
    es.onerror = () => { S.esDown = true; renderLivePill(); };
  } catch (_) {}
}
$("#livePill").onclick = () => {
  const L = S.live, conns = L ? L.connections : S.status?.stream?.connections || [], sm = L ? L.stream : S.status?.stream || {};
  modal(`<h3>实时行情连接</h3><div class="note" style="margin-bottom:8px">官方公共接口，无需 API Key。当前行情源：<b>${VN[S.status.settings.venue]}</b></div><div class="conn-list">${conns.map((c) => `<div><b class="${c.status === "connected" ? "ok" : "bad"}">●</b> ${esc(c.name)} · ${c.status === "connected" ? "已连接" : esc(c.status)}${c.last_msg ? ` · 最后消息 ${tFull(c.last_msg, true)}` : ""}${c.reconnects ? ` · 累计重连 ${c.reconnects} 次` : ""}<br><span class="src">${esc(c.url)}</span>${c.last_error ? `<br><span class="src neg">${esc(c.last_error)}</span>` : ""}</div>`).join("") || "暂无连接信息"}</div>
   <div class="note" style="margin-top:10px">模式 ${sm.mode ?? "—"} · WebSocket 新鲜报价 ${sm.quotes_ws_fresh ?? "—"} 个 · REST 兜底 ${sm.quotes_rest_fresh ?? "—"} 个。价格超过 20 秒无 WS 更新时自动改用官方 REST；重连窗口内标为「恢复中」而非误报 REST；获取失败只报错，不会编造价格。${Object.keys(sm.rest_errors || {}).length ? "<br><span class='neg'>REST 错误：" + Object.entries(sm.rest_errors).slice(0, 4).map(([k, v]) => esc(k + " " + v)).join("；") + "</span>" : ""}</div>
   <div class="acts"><button class="btn" data-close>关闭</button></div>`, (m) => (m.querySelector("[data-close]").onclick = closeModal));
};

/* ---------- 路由与刷新 ---------- */
const PAGES = { dashboard: pageDashboard, signals: pageSignals, backtest: pageBacktest, positions: pagePositions, trades: pageTrades, risk: pageRisk, settings: pageSettings, help: pageHelp };
const SUBS = { dashboard: "系统化纸面 / 研究工具 · 不构成投资建议", signals: "实时 K 线与每个币的进出场建议", backtest: "真实公共历史 K 线 · 无前视回测", positions: "持久化纸面持仓", trades: "成交明细与订单路由日志", risk: "自动交易、紧急停止与风控参数", settings: "行情源、API 密钥（加密保存）与实盘闸门", help: "使用说明与风险提示" };
async function refreshStatus() { S.status = await api("/api/status"); renderMode(); }
async function refreshDash() { S.dash = await api("/api/dashboard"); }
async function refreshAll() {
  try { await Promise.all([refreshStatus(), refreshDash()]); } catch (e) { toast("无法连接后端：" + e.message, true); return; }
  renderRight();
  if (["dashboard", "positions"].includes(S.page)) PAGES[S.page]();
}
async function route() {
  S.page = (location.hash.replace("#/", "") || "dashboard").split("?")[0];
  if (!PAGES[S.page]) S.page = "dashboard";
  if (S.page !== "signals") S.chart = null;
  renderNav(); renderTitle();
  if (!S.status || !S.dash) await refreshAll();
  try { await PAGES[S.page](); } catch (e) { $("#page").innerHTML = `<div class="empty neg">${esc(e.message)}</div>`; }
  $("#page").scrollTop = 0;
}
window.addEventListener("hashchange", route);
greet(); setInterval(greet, 60000);
route().then(() => api("/api/signals").then((r) => { S.signals = r; renderRight(); if (S.page === "dashboard") pageDashboard(); }).catch(() => {}));
if (!new URLSearchParams(location.search).has("nolive")) connectLive(); // nolive 仅用于无头截图
setInterval(renderLivePill, 5000);
setInterval(() => { if (S.page === "signals") renderChartSrc(); }, 1000);
setInterval(async () => { await refreshAll(); }, 30000);
setInterval(async () => { try { S.signals = await api("/api/signals"); renderRight(); if (S.page === "signals") renderSigGrid(); } catch (_) {} }, 120000);
