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
  ["dashboard", "home", "总览"], ["signals", "signals", "信号 / 进出场"], ["backtest", "backtest", "回测"], ["positions", "positions", "持仓"],
  ["trades", "trades", "成交"], ["risk", "risk", "风控 / 自动交易"], ["settings", "settings", "API / 设置"], ["help", "help", "帮助"],
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
const t = (iso) => { if (!iso) return "—"; const d = new Date(iso); return isNaN(d) ? iso : d.toLocaleString("zh-CN", { hour12: false, month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); };
const tFull = (iso) => { if (!iso) return "—"; const d = new Date(iso); return isNaN(d) ? iso : d.toLocaleString("zh-CN", { hour12: false }); };
const sideCn = (s) => ({ long: "做多", short: "做空", flat: "空仓" }[s] || s);
const mktCn = (m) => ({ spot: "现货", perp: "USDT 永续" }[m] || m);

function toast(msg, err) { const el = $("#toast"); el.textContent = msg; el.className = "toast show" + (err ? " err" : ""); clearTimeout(el._t); el._t = setTimeout(() => (el.className = "toast"), 3800); }
async function api(path, opt = {}) {
  const o = { method: opt.method || "GET", headers: { "Content-Type": "application/json" } };
  if (opt.body !== undefined) o.body = JSON.stringify(opt.body);
  const r = await fetch(path, o);
  let j = null; try { j = await r.json(); } catch (_) {}
  if (!r.ok) throw new Error((j && (j.detail || j.message)) || `HTTP ${r.status}`);
  return j;
}
function modal(html, onMount) { $("#modalCard").innerHTML = html; $("#modal").classList.remove("hidden"); onMount && onMount($("#modalCard")); }
function closeModal() { $("#modal").classList.add("hidden"); }
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeModal(); });
function confirmBox(title, body, okText, danger) {
  return new Promise((res) => modal(`<h3>${title}</h3><div class="note" style="font-size:13px">${body}</div><div class="acts"><button class="btn ghost" data-x>取消</button><button class="btn ${danger ? "danger" : ""}" data-ok>${okText}</button></div>`,
    (m) => { m.querySelector("[data-x]").onclick = () => { closeModal(); res(false); }; m.querySelector("[data-ok]").onclick = () => { closeModal(); res(true); }; }));
}

/* ---------- 外壳 ---------- */
function renderNav() {
  $("#sidebar").innerHTML = NAV.map(([id, icon, label]) => `<button class="nav-item ${S.page === id ? "active" : ""}" data-go="${id}" aria-label="${label}">${ic(icon)}<span class="tip">${label}</span></button>`).join("");
  $("#sidebar").querySelectorAll("[data-go]").forEach((b) => (b.onclick = () => (location.hash = "#/" + b.dataset.go)));
}
function greet() {
  const h = new Date().getHours();
  const g = h < 5 ? "夜深了" : h < 11 ? "早上好" : h < 13 ? "中午好" : h < 18 ? "下午好" : "晚上好";
  $("#greet").textContent = `${g}，kean`;
}
function renderMode() {
  const st = S.status; if (!st) return;
  const live = st.mode === "live";
  const b = $("#modeBadge");
  b.className = "mode-badge" + (live ? " live" : "");
  b.textContent = live ? `实盘已开启 · ${st.settings.venue.toUpperCase()}` : "纸面模式 · 不下真实订单";
  $("#shell").classList.toggle("live-on", live);
  $("#accountSel").value = live ? st.settings.venue : "paper";
  const w = st.worker;
  $("#bellDot").className = "dot" + (w.last_error ? " warn" : "");
  $("#bellDot").style.display = w.running || w.last_error ? "" : "none";
}
$("#accountSel").onchange = async (e) => {
  const v = e.target.value;
  if (v === "paper") {
    if (S.status.mode === "live") { await api("/api/live", { method: "PUT", body: { mode: "paper", live_enabled: false } }); toast("已切回纸面模式"); }
    await refreshStatus(); return;
  }
  if (v !== S.status.settings.venue) { await api("/api/settings", { method: "PUT", body: { venue: v } }); toast(`行情/交易所已切换为 ${v.toUpperCase()}（仍为纸面模式）`); }
  e.target.value = "paper"; await refreshStatus();
  location.hash = "#/settings";
};
$("#runNowBtn").onclick = async (e) => {
  const b = e.currentTarget, orig = b.innerHTML; b.disabled = true; b.innerHTML = '<span class="spin"></span>';
  try { const r = await api("/api/cycle", { method: "POST" }); toast(r.events.length ? r.events.join("；") : "已执行：无需调仓"); await refreshAll(); }
  catch (err) { toast("执行失败：" + err.message, true); }
  finally { b.disabled = false; b.innerHTML = orig; }
};
$("#killBtn").onclick = async () => {
  if (!(await confirmBox("紧急停止", "将立即：<br>① 停止后台自动交易；② 关闭实盘开关并切回纸面；③ 按最新公共价格平掉<b>全部纸面持仓</b>。<br><br>本操作不会向交易所发送任何订单。", "立即停止并平仓", true))) return;
  try { const r = await api("/api/kill", { method: "POST" }); toast(r.events.length ? "已平仓：" + r.events.join("；") : "已停止，当前无持仓"); await refreshAll(); }
  catch (e) { toast(e.message, true); }
};
$("#alertGo").onclick = () => (location.hash = "#/signals");
const setRail = (open) => $("#shell").classList.toggle("rail-open", open);
$("#railBtn").onclick = () => setRail(!$("#shell").classList.contains("rail-open"));
$("#railBackdrop").onclick = () => setRail(false);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") { setRail(false); closeModal(); } });
$("#rSearchBtn").onclick = () => { const i = $("#rSearch"); i.classList.toggle("hidden"); i.focus(); };
$("#rSearch").oninput = (e) => { S.rSearch = e.target.value.trim().toUpperCase(); renderRight(); };
$("#bellBtn").onclick = () => showStatusModal();
$("#noticeBtn").onclick = () => showNotices();

function showStatusModal() {
  const st = S.status, w = st.worker;
  modal(`<h3>运行状态</h3><div class="note" style="font-size:13px;line-height:1.9">
    模式：<b>${st.mode === "live" ? "实盘" : "纸面"}</b> · 交易所：<b>${st.settings.venue.toUpperCase()}</b><br>
    自动交易：<b>${w.running ? "运行中" : "已停止"}</b>${w.running ? `（每 ${st.settings.worker.interval_sec} 秒，下次约 ${w.next_run_in_sec ?? "—"} 秒后）` : ""}<br>
    上次执行：<b>${tFull(w.last_run)}</b>${w.last_error ? `<br><span class="neg">上次错误：${esc(w.last_error)}</span>` : ""}<br>
    实盘闸门：<b>${st.live_gate_open ? '<span class="neg">已打开</span>' : "关闭"}</b><br>
    ${st.live_block_reasons.length ? "<span class='muted'>未满足：" + st.live_block_reasons.map(esc).join("；") + "</span>" : ""}
  </div><div class="acts"><button class="btn ghost" onclick="closeModal()">关闭</button><button class="btn" onclick="closeModal();location.hash='#/risk'">去风控页</button></div>`);
}
function showNotices() {
  const r = S.dash?.worker?.last_result;
  const ev = r ? [...(r.events || []), ...Object.entries(r.errors || {}).map(([k, v]) => `${k}：${v}`)] : [];
  modal(`<h3>系统消息</h3><div class="note" style="font-size:13px;line-height:1.8">${ev.length ? ev.map((x) => "• " + esc(x)).join("<br>") : "最近一次自动周期没有新消息。"}
  <br><br>提示：这是系统化纸面 / 研究工具，不构成投资建议；实盘交易可能亏损全部本金。</div><div class="acts"><button class="btn" onclick="closeModal()">知道了</button></div>`);
}

/* ---------- 右侧面板 ---------- */
function renderRight() {
  const d = S.dash; if (!d) return;
  const q = S.rSearch;
  let html = "";
  if (d.positions.length) {
    $("#rTitle").textContent = "持仓";
    $("#rSub").textContent = `${d.positions.length} 个持仓 · 更新于 ${t(d.positions[0].mark_time)}`;
    html = d.positions.filter((p) => !q || p.symbol.includes(q)).sort((a, b) => b.weight - a.weight).map((p) => `
      <div class="r-row" data-sym="${p.symbol}">${coin(p.symbol)}<div><div class="nm">${p.symbol.replace("USDT", "")}<span class="muted" style="font-weight:500"> /USDT</span></div>
      <div class="ds">${sideCn(p.side)} · ${mktCn(p.market)}</div></div>
      <div class="rt">${pct(p.weight, 1)}<div class="ds ${cls(p.upnl)}">${sgn(p.upnl)}</div></div></div>`).join("");
  } else {
    $("#rTitle").textContent = "关注币种";
    $("#rSub").textContent = "当前空仓 · 显示系统化信号";
    const rows = S.signals?.rows || S.status.settings.symbols.map((s) => ({ symbol: s }));
    html = rows.filter((r) => !q || r.symbol.includes(q)).map((r) => `
      <div class="r-row" data-sym="${r.symbol}">${coin(r.symbol)}<div><div class="nm">${r.symbol.replace("USDT", "")}<span class="muted" style="font-weight:500"> /USDT</span></div>
      <div class="ds">${r.advice ? `${r.advice} · ${r.market_cn}` : r.error ? "数据不可用" : "加载中…"}</div></div>
      <div class="rt">${(() => { const q = S.live && S.live.prices[r.symbol]; const m = r.market && r.market !== "-" ? r.market : "spot"; const v = q && q[m] ? q[m].price : r.ref_price; return v ? fp(v) : ""; })()}<div class="ds">${S.live && S.live.prices[r.symbol] ? (r.market === "perp" ? "永续标记" : "现货最新") : ""}</div></div></div>`).join("");
  }
  $("#rList").innerHTML = html || '<div class="empty">无匹配</div>';
  $("#rList").querySelectorAll("[data-sym]").forEach((el) => (el.onclick = () => { S.selSym = el.dataset.sym; setRail(false); if (S.page === "signals") pageSignals(); else location.hash = "#/signals"; }));
  // 提醒卡片
  const st = S.status;
  let msg;
  if (st.mode === "live") msg = `⚠️ 实盘已开启<small>订单将真实发送到 ${st.settings.venue.toUpperCase()}，随时可按“紧急停止”。</small>`;
  else if (d.max_drawdown < -0.1) msg = `纸面回撤已达 ${pct(d.max_drawdown, 1)}<small>请检查风控参数，必要时紧急停止。</small>`;
  else if (S.signals) {
    const rows = S.signals.rows.filter((r) => !r.error);
    const L = rows.filter((r) => r.signal > 0).length, Sh = rows.filter((r) => r.signal < 0).length, F = rows.length - L - Sh;
    const pend = rows.filter((r) => r.state === "entry_pending").length;
    msg = `最新系统信号：${L} 多 · ${Sh} 空 · ${F} 空仓<small>${pend ? `${pend} 个标的等待入场；` : ""}截至 ${t(rows[0]?.as_of)} 收盘 K 线</small>`;
  } else msg = `${st.worker.running ? "自动交易运行中" : "自动交易未开启"}<small>默认纸面模式，可在风控页开启。</small>`;
  $("#rAlertText").innerHTML = msg;
}

/* ---------- 总览 ---------- */
const WAVE1 = `<svg class="deco" viewBox="0 0 250 132" preserveAspectRatio="none"><path d="M0 0H250V40C210 70 190 20 150 40S90 110 40 80 0 60 0 60Z" fill="#5ee0d6"/><path d="M120 0H250V20C220 45 200 5 170 18S130 25 120 0Z" fill="#3a2f88" opacity=".55"/></svg>`;
const WAVE2 = `<svg class="deco" viewBox="0 0 250 132" preserveAspectRatio="none"><path d="M0 132L120 10 250 132Z" fill="#4a52a0" opacity=".6"/><path d="M70 132L170 30 250 110V132Z" fill="#565fb3" opacity=".55"/><path d="M150 0 250 90V0Z" fill="#2a2f65" opacity=".6"/></svg>`;
const WAVE3 = `<svg class="deco" viewBox="0 0 250 132" preserveAspectRatio="none"><circle cx="220" cy="10" r="70" fill="#6c5ce7" opacity=".35"/><circle cx="250" cy="120" r="60" fill="#5ee0d6" opacity=".18"/></svg>`;

function txRow(f, lead) {
  const pnl = Number(f.realized_pnl_usdt), open = f.action === "open";
  const dir = f.side === "buy" ? "up" : "down";
  const title = `${f.symbol.replace("USDT", "")} ${open ? "开" : "平"}${f.market === "spot" ? "多" : "空"} · ${mktCn(f.market)}`;
  const amt = open ? `<span>${f2(f.notional_usdt)}</span><small>USDT</small>` : `<span class="${cls(pnl)}">${sgn(pnl)}</span><small>USDT</small>`;
  return `<div class="tx ${lead ? "lead" : ""}">${coin(f.symbol, "lg")}<div><div class="ttl">${esc(title)}</div><div class="ds">${esc(f.reason)} · ${t(f.time)} · ${fp(f.price)} </div></div>
    <div class="amt num">${amt}</div><div class="stoggle ${dir}" title="${f.side === "buy" ? "买入" : "卖出"}"><i>${ic(dir === "up" ? "up" : "down")}</i></div></div>`;
}
function sigRowAsTx(r, lead) {
  const dir = r.signal > 0 ? "up" : r.signal < 0 ? "down" : "flat";
  return `<div class="tx ${lead ? "lead" : ""}">${coin(r.symbol, "lg")}<div><div class="ttl">${r.symbol.replace("USDT", "")} · ${r.advice} · ${r.market_cn}</div><div class="ds">系统信号 · ${esc(r.entry_timing).slice(0, 38)}</div></div>
   <div class="amt num">${r.target_notional_usdt ? f2(r.target_notional_usdt) + "<small>USDT</small>" : "—"}</div><div class="stoggle ${dir}"><i>${ic(dir === "down" ? "down" : "up")}</i></div></div>`;
}
function pageDashboard() {
  const d = S.dash, st = S.status;
  const per = 3, fills = d.recent_fills, pages = Math.max(1, Math.ceil(fills.length / per));
  S.txPage = Math.min(S.txPage, pages - 1);
  const shown = fills.slice(S.txPage * per, S.txPage * per + per);
  const sigs = (S.signals?.rows || []).filter((r) => !r.error).slice(0, 3);
  const list = shown.length ? shown.map((f, i) => txRow(f, i === 0)).join("") : sigs.length ? sigs.map((r, i) => sigRowAsTx(r, i === 0)).join("") : '<div class="empty">尚无成交。点击右上角紫色按钮执行一次系统化周期。</div>';
  const v = st.settings.venue;
  const longN = d.positions.filter((p) => p.side === "long").reduce((a, p) => a + p.notional, 0);
  const shortN = d.positions.filter((p) => p.side === "short").reduce((a, p) => a + p.notional, 0);
  const cash = Math.max(0, d.cash_free);
  $("#page").innerHTML = `
  <div class="dash">
    <div class="cards">
      <div class="bcard c1" data-go="positions">${WAVE1}<div class="chip"></div><div class="lbl">模拟权益 · PAPER EQUITY</div>
        <div class="big num">${f2(d.equity)}</div><div class="row"><div>累计收益<b class="${cls(d.total_pnl)}">${sgn(d.total_pnl)} (${pct(d.total_return)})</b></div><div style="text-align:right">起始<b>${f2(d.starting_equity, 0)}</b></div></div></div>
      <div class="bcard c2" data-go="risk">${WAVE2}<div class="chip"></div><div class="lbl">可用现金 · FREE CASH</div>
        <div class="big num">${f2(Math.abs(d.cash_free) < 0.005 ? 0 : d.cash_free)}</div><div class="row"><div>总敞口<b>${f2(d.gross)}</b></div><div style="text-align:right">净敞口<b>${sgn(d.net)}</b></div></div></div>
      <div class="bcard c3">${WAVE3}<div class="lbl" style="margin-top:0">选择交易所 · 公共行情</div>
        <div class="vsel"><button data-v="okx" class="${v === "okx" ? "on" : ""}">OKX</button><button data-v="gate" class="${v === "gate" ? "on" : ""}">Gate.io</button></div>
        <div class="row" style="margin-top:14px"><div>API 密钥<b>${st.vault[v].configured ? "已加密保存 " + esc(st.vault[v].api_key_masked) : "未配置（不影响纸面）"}</b></div><div style="text-align:right">模式<b>${st.mode === "live" ? "实盘" : "纸面"}</b></div></div></div>
      <div class="addcard" data-go="settings"><div class="plus">+</div>配置 API Key</div>
    </div>
    <div>
      <div class="tx-head"><h3>最近成交</h3><div class="arrows"><button id="txPrev" title="上一页">${ic("left")}</button><button id="txNext" title="下一页">${ic("right")}</button></div></div>
      <div class="week">本周摘要 · 纸面权益</div>
      <div class="big-eq"><div class="flag"></div><div class="v num">${f2(d.equity)}<small>USDT</small></div>
        <div class="ud"><span class="pos">${ic("arrUp")}${f2(d.week.gains)} <small>USDT</small></span><span class="neg">${ic("arrDown")}${f2(Math.abs(d.week.losses))} <small>USDT</small></span></div></div>
      <div class="tx-list">${list}</div>
      ${!shown.length && sigs.length ? '<div class="note" style="margin-top:6px">尚无成交，以上为当前系统化信号预览。</div>' : ""}
    </div>
    <div class="summary">
      <div class="sec-title"><h3>账户快速摘要</h3><button class="link" data-go="trades">查看全部</button></div>
      <div class="tiles">
        <div class="tile"><div class="tt">权益</div><div class="tv num">${f2(d.equity, 1)}</div><div class="tu">USDT</div><div class="go">${ic("up")}</div><div class="tc">${MiniCharts.area(d.ledger.map((x) => x.equity))}</div></div>
        <div class="tile"><div class="tt">盈亏</div><div class="tv num ${cls(d.total_pnl)}">${sgn(d.total_pnl)}</div><div class="tu">USDT · 未实现 ${sgn(d.unrealized)}</div><div class="go" style="color:${d.total_pnl < 0 ? "var(--red)" : ""}">${ic(d.total_pnl < 0 ? "down" : "up")}</div><div class="tc">${MiniCharts.line(d.pnl_by_trade.length > 1 ? d.pnl_by_trade.reduce((a, x) => (a.push((a.at(-1) || 0) + x), a), []) : d.ledger.map((x) => x.equity))}</div></div>
        <div class="tile"><div class="tt">回撤 · 胜率</div><div class="tv num">${pct(d.max_drawdown, 1)}</div><div class="tu">胜率 ${d.win_rate == null ? "—" : pct(d.win_rate, 0)} · ${d.closed_trades} 笔已平</div><div class="go" style="color:var(--violet)">${ic("down")}</div><div class="tc">${MiniCharts.bars(d.drawdown.filter((_, i, a) => i % Math.max(1, Math.floor(a.length / 18)) === 0))}</div></div>
        <div class="tile donut"><div class="tt">敞口</div><div class="go" style="color:var(--violet)">${ic("up")}</div>
          <div class="tc">${MiniCharts.donut([{ v: longN, c: "#5ee0d6" }, { v: shortN, c: "#4b3aa6" }, { v: cash, c: "#ece8fd" }])}</div>
          <div class="legend"><div><i style="background:#5ee0d6"></i>现货多 ${f2(longN, 0)}</div><div><i style="background:#4b3aa6"></i>永续空 ${f2(shortN, 0)}</div><div><i style="background:#ece8fd"></i>现金 ${f2(cash, 0)}</div></div></div>
      </div>
      <div class="note" style="margin-top:14px">系统化纸面 / 研究工具，不构成投资建议；实盘交易可能亏损全部本金。数据来自 ${v.toUpperCase()} 官方公共行情，更新于 ${tFull(d.time)}。</div>
    </div>
  </div>`;
  bindGo();
  $("#txPrev").onclick = () => { S.txPage = Math.max(0, S.txPage - 1); pageDashboard(); };
  $("#txNext").onclick = () => { S.txPage = Math.min(pages - 1, S.txPage + 1); pageDashboard(); };
  document.querySelectorAll(".vsel [data-v]").forEach((b) => (b.onclick = async (e) => {
    e.stopPropagation();
    try { await api("/api/settings", { method: "PUT", body: { venue: b.dataset.v } }); toast(`已切换为 ${b.dataset.v.toUpperCase()} 公共行情`); S.signals = null; await refreshAll(); } catch (er) { toast(er.message, true); }
  }));
}
function bindGo() { document.querySelectorAll("#page [data-go]").forEach((el) => (el.onclick = () => (location.hash = "#/" + el.dataset.go))); }

/* ---------- 信号 / 进出场 ---------- */
async function pageSignals() {
  $("#page").innerHTML = `<div class="book-banner"><div><b>系统化账本 · ${esc(S.status.settings.strategy.rule_id)}</b><br><span>SMA${S.status.settings.strategy.fast_ma} / SMA${S.status.settings.strategy.slow_ma} · ${S.status.settings.strategy.interval} 已收盘 K 线 · 做多→现货，做空→USDT 永续（1 倍）· 非主观判断</span></div>
    <div class="sp"><button class="btn ghost sm" id="sigRefresh">刷新</button><a class="btn ghost sm" href="/api/export/signals.csv">${ic("dl")}导出 CSV</a></div></div>
    <div class="panel" style="padding:12px;margin-bottom:18px"><div class="sec-title" style="margin:4px 8px 8px;gap:12px;flex-wrap:wrap"><h3 id="chartTitle">K 线与均线</h3>
      <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><span class="note" id="chartSrc">▲▼ 为该市场自身均线交叉（收盘确认）· 最后一根为实时推送的未收盘 K 线</span>
      <div class="seg" id="mktSeg"><button data-m="spot">现货</button><button data-m="perp">USDT 永续</button></div></div></div>
      <div class="chart-box" id="candleChart"><div class="empty">加载中…</div></div></div>
    <div class="sig-grid" id="sigGrid"><div class="empty">正在从 ${S.status.settings.venue.toUpperCase()} 公共行情计算信号…</div></div>`;
  $("#sigRefresh").onclick = async () => { S.signals = null; await pageSignals(); };
  try { if (!S.signals) S.signals = await api("/api/signals"); } catch (e) { $("#sigGrid").innerHTML = `<div class="empty neg">信号计算失败：${esc(e.message)}</div>`; return; }
  renderRight();
  const rows = S.signals.rows;
  S.selSym = S.selSym || rows.find((r) => !r.error)?.symbol;
  const selRow = rows.find((r) => r.symbol === S.selSym);
  S.chartMkt = S.chartMkt || (selRow && selRow.signal_market) || "spot";
  const sc = { holding: ["持有中", "info"], entry_pending: ["待入场", "warn"], blocked: ["止损观望", "flat"], flat: ["空仓", "flat"] };
  $("#sigGrid").innerHTML = rows.map((r) => r.error ? `<div class="sig">${coin(r.symbol)}<div class="note neg" style="margin-top:8px">${esc(r.symbol)}：${esc(r.error)}</div></div>` : `
    <div class="sig ${r.symbol === S.selSym ? "sel" : ""}" data-sym="${r.symbol}">
      <div class="hd">${coin(r.symbol, "lg")}<div><div class="nm">${r.symbol.replace("USDT", "")}<span class="muted" style="font-weight:500">/USDT</span></div><div class="px">${r.ref_price_kind === "mark" ? "永续标记价" : r.ref_price_kind === "last" ? "现货最新价" : "收盘价"} <b data-px="${r.symbol}:${r.market === "-" ? "spot" : r.market}">${fp(r.ref_price)}</b></div></div>
        <span class="pill ${r.side}">${r.advice}${r.market !== "-" ? " · " + r.market_cn : ""}</span></div>
      <div class="kv"><div><small>建议名义</small><b class="num">${r.target_notional_usdt ? f2(r.target_notional_usdt) : "—"}</b></div><div><small>权重 / 风险</small><b class="num">${pct(r.target_weight, 1)} / ${f2(r.risk_usdt)}</b></div><div><small>止损价</small><b class="num">${r.stop_price ? fp(r.stop_price) : "—"}</b></div></div>
      <div class="tm"><p><i>入场</i><span>${esc(r.entry_timing)}</span></p><p><i>离场</i><span>${esc(r.exit_timing)}</span></p>
      <p><i>状态</i><span><span class="pill ${sc[r.state][1]}">${sc[r.state][0]}</span> 快线 ${fp(r.sma_fast)} / 慢线 ${fp(r.sma_slow)} · 上限来源 ${({ risk: "5% 风险", weight: "20% 权重", gross: "总敞口", none: "—" })[r.capped_by]}</span></p>
      <p><i>分市场</i><span>现货信号 <b>${r.spot_signal > 0 ? "做多" : r.spot_signal < 0 ? "做空" : "空仓"}</b> · 永续信号 <b>${r.perp_signal > 0 ? "做多" : r.perp_signal < 0 ? "做空" : "空仓"}</b>${r.conflict ? ' · <span class="pill warn">冲突→空仓</span>' : ""}</span></p>
      <p><i>时间</i><span>信号截至 ${tFull(r.as_of)} 收盘 · 下次检查 ${tFull(r.next_check)}</span></p>
      <p><i>数据</i><span class="src">${esc(r.data_source)} · ${esc(r.source_host)} · 拉取 ${tFull(r.fetched_at)}${r.warning ? ` · <span class="neg">${esc(r.warning)}</span>` : ""}</span></p></div>
    </div>`).join("");
  document.querySelectorAll(".sig[data-sym]").forEach((el) => (el.onclick = () => { S.selSym = el.dataset.sym; const rr = rows.find((x) => x.symbol === S.selSym); S.chartMkt = (rr && rr.signal_market) || S.chartMkt; document.querySelectorAll(".sig").forEach((x) => x.classList.toggle("sel", x === el)); loadCandles(); }));
  document.querySelectorAll("#mktSeg [data-m]").forEach((b) => (b.onclick = () => { S.chartMkt = b.dataset.m; loadCandles(); }));
  loadCandles();
}
async function loadCandles() {
  const el = $("#candleChart"); if (!el || !S.selSym) return;
  const m = S.chartMkt || "spot";
  document.querySelectorAll("#mktSeg [data-m]").forEach((b) => b.classList.toggle("on", b.dataset.m === m));
  $("#chartTitle").textContent = `${S.selSym} · ${m === "perp" ? "USDT 永续" : "现货"} · ${S.status.settings.strategy.interval} K 线与均线`;
  try {
    const d = await api(`/api/candles?symbol=${S.selSym}&bars=300&market=${m}`);
    S.chart = BigCharts.candles(el, d); S.chart._sym = S.selSym; S.chart._mkt = m;
    $("#chartSrc").textContent = `来源 ${d.data_source} · ${d.source_host} · ${d.candles.length} 根已收盘 K 线 · 最后一根实时更新`;
    applyForming();
  }
  catch (e) { el.innerHTML = `<div class="empty neg">${esc(e.message)}</div>`; }
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
  ${d.positions.map((p) => `<tr><td><div style="display:flex;gap:10px;align-items:center">${coin(p.symbol)}<b>${p.symbol}</b></div></td><td><span class="pill ${p.side}">${sideCn(p.side)} · ${mktCn(p.market)}</span></td><td class="num">${fp(p.qty)}</td><td class="num">${fp(p.entry_price)}</td><td>${tFull(p.entry_time)}</td><td class="num">${fp(p.mark_price)}</td><td class="num">${fp(p.stop_price)}</td><td class="num">${f2(p.notional)}</td><td class="num">${pct(p.weight, 1)}</td><td class="num ${cls(p.upnl)}">${sgn(p.upnl)}</td></tr>`).join("")}</tbody></table></div>`
  : '<div class="empty">当前空仓。开启自动交易或点击右上角按钮执行一次系统化周期。</div>'}
  <div class="note" style="margin-top:10px">纸面账本持久化保存在 data/paper/（重启不丢失）。永续空头按 1 倍保证金计，占用等额现金。</div></div>`;
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
  <div class="grid" style="grid-template-columns:1.1fr 1fr">
    <div class="panel"><div class="sec-title"><h3>自动交易（纸面执行）</h3><span class="pill ${w.running ? "long" : "flat"}">${w.running ? "运行中" : "已停止"}</span></div>
      <div class="note" style="margin-bottom:14px">后台循环每隔设定秒数：拉取公共行情 → 计算已收盘 K 线信号 → 检查止损 → 在纸面账本按最新价调仓。实盘只有在“API / 设置”页通过全部闸门后才会发单。</div>
      <div style="display:flex;gap:12px;align-items:end;flex-wrap:wrap">
        <label class="field" style="width:160px">检查间隔（秒）<input id="wInt" type="number" min="60" value="${s.worker.interval_sec}"/></label>
        <button class="btn" id="wStart">${ic("play")}开启自动交易</button><button class="btn ghost" id="wStop">${ic("stop")}停止</button><button class="btn ghost" id="cycleNow">立即执行一次</button>
      </div>
      <div class="note" style="margin-top:12px">上次执行：${tFull(w.last_run)}${w.running ? ` · 下次约 ${w.next_run_in_sec ?? "—"} 秒后` : ""}${w.last_error ? `<br><span class="neg">错误：${esc(w.last_error)}</span>` : ""}</div>
    </div>
    <div class="panel" style="background:linear-gradient(135deg,#fff,#fff4f5)"><div class="sec-title"><h3>紧急停止 / 重置</h3></div>
      <div class="note" style="margin-bottom:14px">紧急停止：停止自动交易、关闭实盘开关、按最新公共价平掉全部纸面持仓。重置：清空纸面账本，恢复起始资金（需先停止自动交易）。</div>
      <div style="display:flex;gap:10px"><button class="btn danger" id="killBig">紧急停止（Kill Switch）</button><button class="btn ghost" id="resetPaper">重置纸面账本</button></div></div>
  </div>
  <div class="panel" style="margin-top:18px"><div class="sec-title"><h3>风控规则（已约定）</h3><span class="note">上限不可调高，只能调低</span></div>
    <div class="grid" style="grid-template-columns:repeat(4,1fr)">
      <label class="field">起始纸面资金 (USDT)<input id="rEq" type="number" value="${s.risk.starting_equity_usdt}"/><span class="hint">重置账本后生效</span></label>
      <label class="field">单笔最大风险<input id="rRisk" type="number" step="0.005" max="0.05" value="${s.risk.max_risk_per_trade}"/><span class="hint">≤ 0.05（5%）</span></label>
      <label class="field">单币最大权重<input id="rW" type="number" step="0.01" max="0.2" value="${s.risk.max_weight_per_name}"/><span class="hint">≤ 0.20（20%）</span></label>
      <label class="field">手续费假设 (bps)<input id="rFee" type="number" step="0.5" value="${s.fees.taker_bps}"/><span class="hint">默认 taker 4 bps</span></label>
    </div>
    <div style="display:flex;gap:28px;margin-top:16px;flex-wrap:wrap">
      <label class="toggle"><input type="checkbox" id="rSpot" ${s.risk.allow_spot_long ? "checked" : ""}/><span class="tr"></span>允许现货做多</label>
      <label class="toggle"><input type="checkbox" id="rPerp" ${s.risk.allow_perp_short ? "checked" : ""}/><span class="tr"></span>允许永续做空</label>
      <span class="pill info">永续杠杆：1 倍（保守默认）</span><span class="pill info">总敞口 ≤ 1× 权益</span>
    </div></div>
  <div class="panel" style="margin-top:18px"><div class="sec-title"><h3>策略参数 · ${esc(s.strategy.rule_id)}</h3></div>
    <div class="grid" style="grid-template-columns:repeat(5,1fr)">
      <label class="field">K 线周期<select id="sInt">${["15m", "1h", "4h", "1d"].map((x) => `<option ${x === s.strategy.interval ? "selected" : ""}>${x}</option>`).join("")}</select></label>
      <label class="field">快线 SMA<input id="sFast" type="number" value="${s.strategy.fast_ma}"/></label>
      <label class="field">慢线 SMA<input id="sSlow" type="number" value="${s.strategy.slow_ma}"/></label>
      <label class="field">ATR 周期<input id="sAtrP" type="number" value="${s.strategy.atr_period}"/></label>
      <label class="field">ATR 止损倍数<input id="sAtr" type="number" step="0.5" value="${s.strategy.atr_stop_mult}"/></label>
    </div></div>
  <div class="panel" style="margin-top:18px"><div class="sec-title"><h3>标的池（USDT 交易对）</h3></div>
    <div class="chips" id="chips">${s.symbols.map((x) => `<span class="c">${coin(x)}${x}<button data-rm="${x}" title="移除">×</button></span>`).join("")}</div>
    <div style="display:flex;gap:10px;margin-top:14px"><input id="addSym" class="r-search" style="margin:0;width:200px" placeholder="例如 LINK 或 LINKUSDT"/><button class="btn ghost sm" id="addSymBtn">添加</button></div></div>
  <div style="display:flex;justify-content:flex-end;margin-top:18px"><button class="btn" id="saveRisk">保存风控与策略设置</button></div>`;
  let syms = [...s.symbols];
  const chips = () => { $("#chips").innerHTML = syms.map((x) => `<span class="c">${coin(x)}${x}<button data-rm="${x}">×</button></span>`).join(""); bindRm(); };
  const bindRm = () => document.querySelectorAll("[data-rm]").forEach((b) => (b.onclick = () => { syms = syms.filter((x) => x !== b.dataset.rm); chips(); }));
  bindRm();
  $("#addSymBtn").onclick = () => { let v = $("#addSym").value.trim().toUpperCase().replace(/[-_/]/g, ""); if (!v) return; if (!v.endsWith("USDT")) v += "USDT"; if (!syms.includes(v)) syms.push(v); $("#addSym").value = ""; chips(); };
  $("#saveRisk").onclick = async () => {
    try {
      await api("/api/settings", { method: "PUT", body: { symbols: syms, worker: { interval_sec: +$("#wInt").value },
        risk: { starting_equity_usdt: +$("#rEq").value, max_risk_per_trade: +$("#rRisk").value, max_weight_per_name: +$("#rW").value, allow_spot_long: $("#rSpot").checked, allow_perp_short: $("#rPerp").checked },
        fees: { taker_bps: +$("#rFee").value },
        strategy: { interval: $("#sInt").value, fast_ma: +$("#sFast").value, slow_ma: +$("#sSlow").value, atr_period: +$("#sAtrP").value, atr_stop_mult: +$("#sAtr").value } } });
      toast("已保存"); S.signals = null; await refreshAll();
    } catch (e) { toast("保存失败：" + e.message, true); }
  };
  $("#wStart").onclick = async () => { try { await api("/api/settings", { method: "PUT", body: { worker: { interval_sec: +$("#wInt").value } } }); await api("/api/worker/start", { method: "POST" }); toast("自动交易已开启（纸面执行）"); setTimeout(refreshAll, 1500); } catch (e) { toast(e.message, true); } };
  $("#wStop").onclick = async () => { await api("/api/worker/stop", { method: "POST" }); toast("自动交易已停止"); refreshAll(); };
  $("#cycleNow").onclick = () => $("#runNowBtn").click();
  $("#killBig").onclick = () => $("#killBtn").click();
  $("#resetPaper").onclick = async () => { if (!(await confirmBox("重置纸面账本", "将清空全部纸面持仓、成交与账本历史，并恢复起始资金。", "确认重置", true))) return; try { await api("/api/paper/reset", { method: "POST" }); toast("纸面账本已重置"); refreshAll(); } catch (e) { toast(e.message, true); } };
}

/* ---------- API / 设置 ---------- */
const KEYWAVE = `<svg class="deco" viewBox="0 0 400 170" preserveAspectRatio="none"><path d="M0 0H400V50C340 90 300 20 240 50S140 150 60 110 0 90 0 90Z" fill="#5ee0d6" opacity=".85"/></svg>`;
function pageSettings() {
  const st = S.status, s = st.settings, v = st.vault;
  const kc = (ex, name) => `<div class="keycard">${KEYWAVE}<h4>${name}</h4><div class="st">${v[ex].configured ? "已加密保存（AES / Fernet）" : "未配置 · 不影响行情、回测与纸面交易"}</div>
     <div class="masked">${v[ex].configured ? esc(v[ex].api_key_masked) : "•••• •••• •••• ••••"}</div><div class="st">Secret ${v[ex].secret_set ? "已保存（不可回显）" : "未保存"}${ex === "okx" ? ` · Passphrase ${v.okx.passphrase_set ? "已保存" : "未保存"}` : ""}</div></div>`;
  $("#page").innerHTML = `
  <div class="grid" style="grid-template-columns:1fr 1fr">
    <div class="panel">
      ${kc("okx", "OKX")}
      <div class="grid" style="margin-top:16px">
        <label class="field">API Key<input id="okKey" autocomplete="off" placeholder="${v.okx.configured ? "留空 = 保持不变" : "粘贴 API Key"}"/></label>
        <label class="field">Secret Key<input id="okSec" type="password" autocomplete="new-password" placeholder="${v.okx.secret_set ? "留空 = 保持不变" : "粘贴 Secret"}"/></label>
        <label class="field">Passphrase<input id="okPass" type="password" autocomplete="new-password" placeholder="${v.okx.passphrase_set ? "留空 = 保持不变" : "创建 API 时设置的口令"}"/></label>
        <label class="toggle"><input type="checkbox" id="okDemo" ${s.live.okx_demo ? "checked" : ""}/><span class="tr"></span>OKX 模拟盘（x-simulated-trading）</label>
        <div style="display:flex;gap:8px"><button class="btn" data-save="okx">${ic("key")}加密保存</button><button class="btn ghost" data-test="okx">只读连接测试</button><button class="btn ghost" data-del="okx">删除</button></div>
      </div></div>
    <div class="panel">
      ${kc("gate", "Gate.io")}
      <div class="grid" style="margin-top:16px">
        <label class="field">API Key<input id="gtKey" autocomplete="off" placeholder="${v.gate.configured ? "留空 = 保持不变" : "粘贴 API Key"}"/></label>
        <label class="field">Secret Key<input id="gtSec" type="password" autocomplete="new-password" placeholder="${v.gate.secret_set ? "留空 = 保持不变" : "粘贴 Secret"}"/></label>
        <label class="toggle"><input type="checkbox" id="gtTest" ${s.live.gate_testnet ? "checked" : ""}/><span class="tr"></span>Gate 合约测试网（现货无测试网）</label>
        <div class="note">建议创建 API 时只勾选“交易 + 读取”，<b>不要开启提现权限</b>，并绑定 IP 白名单。</div>
        <div style="display:flex;gap:8px"><button class="btn" data-save="gate">${ic("key")}加密保存</button><button class="btn ghost" data-test="gate">只读连接测试</button><button class="btn ghost" data-del="gate">删除</button></div>
      </div></div>
  </div>
  <div class="panel" style="margin-top:18px"><div class="sec-title"><h3>交易所与密钥存储</h3></div>
    <div class="grid" style="grid-template-columns:240px 1fr;align-items:start">
      <label class="field">当前交易所（行情 + 交易）<select id="venueSel"><option value="okx">OKX</option><option value="gate">Gate.io</option></select></label>
      <div class="note">密钥以 Fernet（AES-128 + HMAC）加密保存在 <b>data/secrets.enc</b>；主密钥来源：<b>${st.vault.key_source === "passphrase" ? "环境变量 QTW_MASTER_PASSPHRASE（scrypt 派生，不落盘）" : "本地密钥文件 data/vault.key（权限 600）"}</b>。data/ 已加入 .gitignore；密钥不写入 CSV / 日志，页面只显示掩码。${st.vault.error ? `<br><span class="neg">${esc(st.vault.error)}</span>` : ""}</div>
    </div></div>
  <div class="live-box" style="margin-top:18px">
    <h4>⚠️ 实盘交易开关（默认关闭）</h4>
    <div class="note" style="color:#7b3141">实盘交易可能亏损全部资金。本工具是系统化研究 / 纸面工具，不构成投资建议。开启需同时满足：模式=实盘、开关打开、输入确认语、启动时设置 <b>QTW_ALLOW_LIVE_ORDERS=1</b>、对应交易所密钥完整。任何一项不满足，订单只会被记录为“blocked”。</div>
    <div style="display:flex;gap:14px;align-items:end;margin-top:14px;flex-wrap:wrap">
      <label class="field" style="flex:1;min-width:280px">确认语（请完整输入：${esc(st.confirm_phrase_required)}）<input id="livePhrase" placeholder="${esc(st.confirm_phrase_required)}"/></label>
      ${st.settings.live.live_enabled ? '<button class="btn" id="liveOff">关闭实盘，回到纸面</button>' : '<button class="btn danger" id="liveOn">开启实盘模式</button>'}
    </div>
    <ul class="reasons">${st.live_block_reasons.length ? st.live_block_reasons.map((r) => `<li>${esc(r)}</li>`).join("") : "<li><b>全部闸门已通过：订单会真实发送！</b></li>"}</ul>
  </div>`;
  $("#venueSel").value = s.venue;
  $("#venueSel").onchange = async (e) => { await api("/api/settings", { method: "PUT", body: { venue: e.target.value } }); toast("已切换交易所"); S.signals = null; refreshAll(); };
  document.querySelectorAll("[data-save]").forEach((b) => (b.onclick = async () => {
    const ex = b.dataset.save;
    const body = ex === "okx" ? { api_key: $("#okKey").value, secret: $("#okSec").value, passphrase: $("#okPass").value } : { api_key: $("#gtKey").value, secret: $("#gtSec").value };
    try {
      await api(`/api/keys/${ex}`, { method: "PUT", body });
      await api("/api/live", { method: "PUT", body: { okx_demo: $("#okDemo").checked, gate_testnet: $("#gtTest").checked, confirm_phrase: S.status.settings.live.confirm_phrase } });
      toast("已加密保存（页面不会回显完整密钥）"); await refreshStatus(); pageSettings();
    } catch (e) { toast(e.message, true); }
  }));
  document.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => { if (!(await confirmBox("删除密钥", `删除本地保存的 ${b.dataset.del.toUpperCase()} 密钥？`, "删除", true))) return; await api(`/api/keys/${b.dataset.del}`, { method: "DELETE" }); toast("已删除"); await refreshStatus(); pageSettings(); }));
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
  <section><h4>策略 · ${esc(s.rule_id)}</h4><ul>
  <li>现货与 USDT 永续<b>各自</b>在自己已收盘的 ${s.interval} K 线上计算 SMA${s.fast_ma} / SMA${s.slow_ma}。</li>
  <li>现货看多且永续不看空 → <b>做多·现货</b>；永续看空且现货不看多 → <b>做空·USDT 永续</b>（1 倍）；两者冲突或无信号 → 空仓。</li>
  <li>做多的入场 / 止损 / 计价全部用现货价格；做空全部用永续 K 线与标记价。</li>
  <li>离场：收盘出现反向或归零信号，或价格触及 <b>${s.atr_stop_mult}×ATR${s.atr_period}</b> 止损；止损后等信号方向改变才再入场。</li></ul></section>
  <section><h4>仓位与风控</h4><ul><li>风险预算 = 权益 × ${pct(st.risk.max_risk_per_trade, 0)}；名义 = 风险预算 ÷ 止损百分比。</li><li>单币名义 ≤ 权益 × ${pct(st.risk.max_weight_per_name, 0)}；总敞口 ≤ 1× 权益，同时入场按比例缩放。</li><li>手续费假设 ${st.fees.taker_bps} bps；永续 1 倍保证金，不放大。</li></ul></section>
  <section><h4>页面</h4><ul><li><b>总览</b>：权益、现金、交易所、最近成交、快速摘要。</li><li><b>信号 / 进出场</b>：每个币的建议、入场与止损时机、建议仓位、K 线图。</li><li><b>回测</b>：真实历史 K 线（现货 + 永续）回测与 CSV 导出。</li><li><b>持仓 / 成交</b>：SQLite 持久化纸面账本与订单日志。</li><li><b>风控 / 自动交易</b>：参数、标的池、后台自动交易、紧急停止。</li><li><b>API / 设置</b>：加密保存密钥、实盘闸门。</li></ul></section>
  <section><h4>数据与存储</h4><ul><li>数据库：<code>data/qtw.sqlite</code>（K 线缓存、纸面账本、订单日志、回测记录、非敏感设置）。</li><li>API 密钥只存在加密文件 <code>data/secrets.enc</code>，不进数据库。</li><li>CSV 导出：<code>output/</code> 与 <code>output/backtest/</code>。</li></ul></section>
  <section><h4>局限</h4><ul><li>回测未计资金费率与滑点；历史表现不代表未来。</li><li>实盘模式没有与交易所持仓对账；实盘前请先在 OKX 模拟盘 / Gate 合约测试网验证。</li></ul></section>
  <section><h4>快捷操作</h4><ul><li>右上角紫色按钮：立即执行一次系统化周期（纸面）。</li><li>右侧提醒卡“紧急停止”：停止自动交易并平掉全部纸面持仓。</li><li>按 <code>Esc</code> 关闭弹窗 / 右侧抽屉。</li></ul></section></div>`;
}

/* ---------- 实时推送（SSE：后端订阅 OKX / Gate 官方公共 WebSocket） ---------- */
function applyForming() {
  const c = S.chart, L = S.live; if (!c || !L || !c._candle || !document.body.contains($("#candleChart"))) return;
  const f = L.forming[`${L.interval}:${c._sym}:${c._mkt}`];
  if (f && f.time >= c._last) { try { c._candle.update({ time: f.time, open: f.open, high: f.high, low: f.low, close: f.close }); c._last = f.time; } catch (_) {} }
}
function renderLivePill() {
  const L = S.live, el = $("#livePill"); if (!el) return;
  if (!L) { el.className = "live-pill"; el.textContent = "行情连接中…"; return; }
  const m = L.stream.mode;
  el.className = "live-pill " + m;
  el.textContent = m === "ws" ? `实时 · ${L.venue.toUpperCase()} WebSocket` : m === "rest" ? "REST 轮询兜底" : "行情断开";
}
function applyLive() {
  const L = S.live; if (!L) return;
  renderLivePill();
  if (S.dash) {
    Object.assign(S.dash, { equity: L.paper.equity, unrealized: L.paper.unrealized, gross: L.paper.gross, net: L.paper.net,
      total_pnl: L.paper.total_pnl, total_return: L.paper.total_pnl / S.dash.starting_equity });
    S.dash.cash_free = Math.abs(L.paper.equity - L.paper.gross) < 0.005 ? 0 : L.paper.equity - L.paper.gross;
    S.dash.positions.forEach((p) => { const q = L.paper.positions[p.symbol]; if (q) Object.assign(p, { mark_price: q.mark, mark_time: q.mark_time, upnl: q.upnl, weight: q.weight, notional: q.notional }); });
  }
  if (S.signals) S.signals.rows.forEach((r) => { const q = L.prices[r.symbol]; const m = r.market === "-" ? "spot" : r.market; if (q && q[m]) r.ref_price = q[m].price; });
  document.querySelectorAll("[data-px]").forEach((el) => {
    const [sym, m] = el.dataset.px.split(":"); const q = L.prices[sym] && L.prices[sym][m];
    if (q) { const t = fp(q.price); if (el.textContent !== t) { el.textContent = t; el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); } }
  });
  renderRight();
  applyForming();
  const now = Date.now();
  if ((S.page === "dashboard" || S.page === "positions") && now - (S._lastLiveRender || 0) > 5000 && !$("#modal:not(.hidden)")) {
    S._lastLiveRender = now; PAGES[S.page]();
  }
}
function connectLive() {
  try {
    const es = new EventSource("/api/stream");
    es.addEventListener("tick", (e) => { try { S.live = JSON.parse(e.data); applyLive(); } catch (_) {} });
    es.onerror = () => { if (S.live) S.live.stream.mode = "down"; renderLivePill(); };
  } catch (_) {}
}
$("#livePill").onclick = () => {
  const L = S.live; if (!L) return;
  modal(`<h3>实时行情（官方公共接口，无需 API Key）</h3><div class="conn-list">${L.connections.map((c) => `<div><b class="${c.status === "connected" ? "ok" : "bad"}">●</b> ${esc(c.name)} · ${esc(c.status)} · <span class="src">${esc(c.url)}</span>${c.reconnects ? ` · 重连 ${c.reconnects} 次` : ""}${c.last_error ? `<br><span class="src neg">${esc(c.last_error)}</span>` : ""}</div>`).join("")}</div>
   <div class="note" style="margin-top:10px">WS 新鲜报价 ${L.stream.quotes_ws_fresh} 个 · REST 兜底 ${L.stream.quotes_rest_fresh} 个。价格超过 20 秒无 WS 更新时自动改用官方 REST；获取失败只报错，不会编造价格。${Object.keys(L.stream.rest_errors || {}).length ? "<br><span class='neg'>REST 错误：" + Object.entries(L.stream.rest_errors).slice(0, 4).map(([k, v]) => esc(k + " " + v)).join("；") + "</span>" : ""}</div>
   <div class="acts"><button class="btn" onclick="closeModal()">关闭</button></div>`);
};

/* ---------- 路由与刷新 ---------- */
const PAGES = { dashboard: pageDashboard, signals: pageSignals, backtest: pageBacktest, positions: pagePositions, trades: pageTrades, risk: pageRisk, settings: pageSettings, help: pageHelp };
const SUBS = { dashboard: "系统化纸面 / 研究工具 · 不构成投资建议", signals: "系统化账本：做多 / 做空 / 空仓与进出场时机", backtest: "真实公共历史 K 线 · 无前视回测", positions: "持久化纸面持仓", trades: "成交明细与订单路由日志", risk: "风控规则、策略参数与自动交易", settings: "OKX / Gate API 密钥（加密保存）与实盘闸门", help: "使用说明与风险提示" };
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
  renderNav(); $("#pageSub").textContent = SUBS[S.page];
  if (!S.status || !S.dash) await refreshAll();
  try { await PAGES[S.page](); } catch (e) { $("#page").innerHTML = `<div class="empty neg">${esc(e.message)}</div>`; }
}
window.addEventListener("hashchange", route);
greet(); setInterval(greet, 60000);
route().then(() => api("/api/signals").then((r) => { S.signals = r; renderRight(); if (S.page === "dashboard") pageDashboard(); }).catch(() => {}));
if (!new URLSearchParams(location.search).has("nolive")) connectLive(); // nolive 仅用于无头截图
setInterval(async () => { await refreshAll(); }, 30000);
setInterval(async () => { try { S.signals = await api("/api/signals"); renderRight(); } catch (_) {} }, 120000);
