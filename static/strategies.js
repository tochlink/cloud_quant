/* 多策略页（v7）：策略卡片 / 详情与现跑回测 / 影子子账本 / 相关性。只读研究结果 + 官方数据现跑；不改默认策略。
   依赖 app.js 的全局工具（$, api, ic, esc, f2, pct, sgn, cls, fp, tCompact, tFull, modal, pgState, pagerHtml, bindPager, toast, sideCn, mktCn, coin）。 */
(function () {
  const ST = { view: "cards", venue: null, data: null, shadow: null, bt: {} };
  const STATUS_CLS = { "采用": "st-adopt", "观察": "st-watch", "淘汰": "st-drop" };
  const C1 = "#8b8fa8", CX = ["#6c5ce7", "#00b894", "#e17055", "#0984e3", "#e84393", "#fdcb6e", "#00cec9"];
  const colorOf = (no) => CX[(no - 1) % CX.length];
  const num = (x, d = 2) => (x == null || !isFinite(x) ? "—" : Number(x).toFixed(d));
  const pp = (x, d = 1) => (x == null || !isFinite(x) ? "—" : (x > 0 ? "+" : "") + Number(x).toFixed(d) + "%");
  const term = () => document.body.classList.contains("theme-term");

  function tag(status) { return `<span class="st-tag ${STATUS_CLS[status] || ""}">${esc(status || "未评估")}</span>`; }

  /* 两条（或多条）归一化权益线 + 悬停：日期、各线数值、与 #1 的差 */
  function lineChart(host, series, opt = {}) {
    if (!host) return;
    const W = Math.max(200, host.clientWidth || 300), H = Math.max(60, host.clientHeight || 120), P = opt.pad ?? 4;
    const all = series.flatMap((s) => s.pts.map((p) => p[1]));
    if (!all.length) { host.innerHTML = '<div class="empty">暂无曲线</div>'; return; }
    let lo = Math.min(...all), hi = Math.max(...all); if (hi - lo < 1e-9) { hi += 0.01; lo -= 0.01; }
    const dates = [...new Set(series.flatMap((s) => s.pts.map((p) => p[0])))].sort();
    const xi = new Map(dates.map((d, i) => [d, i]));
    const X = (d) => P + (xi.get(d) / Math.max(1, dates.length - 1)) * (W - 2 * P), Y = (v) => P + (1 - (v - lo) / (hi - lo)) * (H - 2 * P);
    const base1 = lo <= 1 && hi >= 1 ? `<line x1="0" x2="${W}" y1="${Y(1)}" y2="${Y(1)}" class="st-one"/>` : "";
    const paths = series.map((s) => `<path d="${s.pts.map((p, i) => (i ? "L" : "M") + X(p[0]).toFixed(1) + " " + Y(p[1]).toFixed(1)).join("")}" stroke="${s.color}" stroke-width="${s.w || 2}" fill="none" ${s.dash ? 'stroke-dasharray="4 3"' : ""} vector-effect="non-scaling-stroke"/>`).join("");
    host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" class="st-svg">${base1}${paths}<line class="st-x" y1="0" y2="${H}" hidden/></svg>${opt.hover === false ? "" : '<div class="st-tip" hidden></div>'}`;
    if (opt.hover === false) return;
    const svg = host.querySelector("svg"), tip = host.querySelector(".st-tip"), xl = host.querySelector(".st-x");
    const maps = series.map((s) => new Map(s.pts));
    host.onmousemove = (e) => {
      const r = svg.getBoundingClientRect(), fx = (e.clientX - r.left - P) / Math.max(1, r.width - 2 * P);
      const d = dates[Math.max(0, Math.min(dates.length - 1, Math.round(fx * (dates.length - 1))))];
      const x = X(d); xl.setAttribute("x1", x); xl.setAttribute("x2", x); xl.removeAttribute("hidden");
      const v0 = maps[0].get(d);
      tip.innerHTML = `<b>${esc(d)}</b>` + series.map((s, k) => { const v = maps[k].get(d); return `<div><i style="background:${s.color}"></i>${esc(s.name)}<span class="num">${v == null ? "—" : pp((v - 1) * 100)}</span>${k && v != null && v0 != null ? `<em class="${cls(v - v0)}">较 ${esc(series[0].name.split(" ")[0])} ${pp((v - v0) * 100)}</em>` : ""}</div>`; }).join("");
      tip.hidden = false;
      const tw = tip.offsetWidth, left = Math.min(r.width - tw - 4, Math.max(4, e.clientX - r.left + 12));
      tip.style.transform = `translate(${left}px, 6px)`;
    };
    host.onmouseleave = () => { tip.hidden = true; xl.setAttribute("hidden", ""); };
  }

  function venue() { return ST.venue || (S.status && S.status.settings && S.status.settings.venue) || "gate"; }
  function itemsById() { const m = {}; (ST.data?.items || []).forEach((x) => (m[x.id] = x)); return m; }

  async function load() {
    const [a, b] = await Promise.all([api("/api/strategies"), api("/api/strategies/shadow").catch(() => ({ books: [] }))]);
    ST.data = a; ST.shadow = b;
  }

  window.pageStrategies = async function pageStrategies() {
    if (!window._stLiveWrapped && typeof window.updateLiveCells === "function") {
      const orig = window.updateLiveCells; window._stLiveWrapped = true;
      window.updateLiveCells = function () { orig.apply(this, arguments); try { liveBooks(); } catch (e) { /* noop */ } };
    }
    $("#page").innerHTML = `<div class="fit st-page"><div class="empty">加载策略研究结果…</div></div>`;
    await load();
    render();
  };

  function render() {
    const d = ST.data, v = venue();
    const nWatch = d.items.filter((x) => x.verdict?.status === "观察").length, nDrop = d.items.filter((x) => x.verdict?.status === "淘汰").length;
    $("#page").innerHTML = `<div class="fit st-page">
      <div class="panel st-head">
        <div class="st-head-l">
          <h3>${ic("strategies")}多策略 · ${d.items.length} 套${infoTip(esc(d.rule || "") + "<br>区间：" + esc(d.window || ""), "判定规则")}</h3>
          <span class="note">默认仍是 #1 · 采用 1 · 观察 ${nWatch} · 淘汰 ${nDrop} · 2025-01-18 → 2026-11-13 · ${esc(d.cut)} 之后的数据没参与选参</span>
        </div>
        <div class="st-head-r">
          <div class="seg" role="tablist" aria-label="视图">${[["cards", "策略列表"], ["shadow", "影子子账本"], ["corr", "相关性"]].map(([k, l]) => `<button type="button" role="tab" data-stv="${k}" class="${ST.view === k ? "on" : ""}">${l}</button>`).join("")}</div>
          <div class="seg" role="group" aria-label="交易所">${["gate", "okx"].map((x) => `<button type="button" data-stven="${x}" class="${v === x ? "on" : ""}">${x === "okx" ? "OKX" : "Gate"}</button>`).join("")}</div>
        </div>
      </div>
      <div class="st-body" id="stBody"></div>
      <div id="stPager" class="st-pager"></div>
    </div>`;
    document.querySelectorAll("[data-stv]").forEach((b) => (b.onclick = () => { ST.view = b.dataset.stv; render(); }));
    document.querySelectorAll("[data-stven]").forEach((b) => (b.onclick = () => { ST.venue = b.dataset.stven; render(); }));
    ({ cards: renderCards, shadow: renderShadow, corr: renderCorr })[ST.view]();
  }

  function metric(label, val, c = "") { return `<div class="st-m"><small>${label}</small><b class="num ${c}">${val}</b></div>`; }

  function renderCards() {
    const host = $("#stBody"), v = venue(), items = ST.data.items, byId = itemsById();
    const w = host.clientWidth || 1000, h = host.clientHeight || 500;
    const cols = Math.max(1, Math.min(4, Math.floor((w + 12) / 300))), rows = Math.max(1, Math.floor((h + 12) / 228));
    const st = pgState("stCards", items.length, cols * rows);
    host.style.gridTemplateColumns = `repeat(${cols}, minmax(0, 1fr))`;
    host.style.gridTemplateRows = `repeat(${rows}, minmax(0, 1fr))`;
    host.className = "st-body st-grid";
    host.innerHTML = items.slice(st.start, st.end).map((x) => {
      const m = (x.metrics || {})[`${v}_real`] || {}, ms = (x.metrics || {})[`${v}_stress`] || {};
      const isDef = x.id === "ma_trend";
      return `<article class="panel st-card ${isDef ? "st-default" : ""}" data-sid="${esc(x.id)}" tabindex="0" role="button" aria-label="${esc(x.name)} 详情">
        <header><span class="st-no" style="background:${colorOf(x.no)}">#${x.no}</span><b class="st-name" title="${esc(x.name)}">${esc(x.name)}</b>${tag(x.verdict?.status)}</header>
        <div class="st-sub"><span class="st-kind">${esc(x.kind)}</span><span>${esc(x.interval === "8h" ? "资金费结算" : x.interval)}</span>${x.shadow ? '<span class="st-live">影子盘运行中</span>' : ""}${isDef ? '<span class="st-live def">默认 1000U 账本</span>' : ""}</div>
        <div class="st-ms">${metric("全段收益", pp(m.full_ret), cls(m.full_ret))}${metric("夏普", num(m.sharpe))}${metric("03-05 后", pp(m.post_ret), cls(m.post_ret))}${metric("最大回撤", pp(m.full_dd), "neg")}</div>
        <div class="st-ms sm">${metric("胜率", m.win_rate == null ? "—" : num(m.win_rate, 1) + "%")}${metric("利润因子", num(m.profit_factor))}${metric("与 #1 相关", isDef ? "1.00" : num(m.corr_vs_1))}${metric("压力费率", pp(ms.full_ret), cls(ms.full_ret))}</div>
        <div class="st-spark" data-spark="${esc(x.id)}"></div>
      </article>`;
    }).join("");
    host.querySelectorAll("[data-spark]").forEach((el) => {
      const x = byId[el.dataset.spark], s = [{ name: `#${x.no} ${x.name}`, color: colorOf(x.no), pts: (x.curve || {})[v] || [] }];
      if (x.id !== "ma_trend") s.push({ name: "#1 默认", color: C1, pts: (byId.ma_trend.curve || {})[v] || [], dash: true, w: 1.4 });
      lineChart(el, s, { hover: false, pad: 3 });
    });
    host.querySelectorAll("[data-sid]").forEach((el) => { el.onclick = () => openDetail(el.dataset.sid); el.onkeydown = (e) => { if (e.key === "Enter") openDetail(el.dataset.sid); }; });
    $("#stPager").innerHTML = pagerHtml("stCards", st); bindPager("stCards", renderCards);
    requestAnimationFrame(() => { // 实测溢出则少放一行
      const over = [...host.querySelectorAll(".st-card")].some((c) => c.scrollHeight > c.clientHeight + 2);
      if (over && rows > 1 && !host._shrunk) { host._shrunk = true; S.pg.stCards._fit = cols * (rows - 1); renderCards(); }
    });
  }

  function mtable(x) {
    const cols = [["gate_real", "Gate 真实费率"], ["gate_stress", "Gate 压力费率"], ["okx_real", "OKX 真实费率"], ["okx_stress", "OKX 压力费率"]];
    const rows = [["full_ret", "全段收益", (a) => pp(a)], ["sharpe", "夏普（日）", (a) => num(a)], ["full_dd", "最大回撤", (a) => pp(a)], ["pre_ret", "03-05 前", (a) => pp(a)], ["post_ret", "03-05 后", (a) => pp(a)], ["post_dd", "后段回撤", (a) => pp(a)],
      ["trades", "成交笔数", (a) => (a == null ? "—" : a)], ["win_rate", "胜率", (a) => (a == null ? "—" : num(a, 1) + "%")], ["payoff", "盈亏比", (a) => num(a)], ["profit_factor", "利润因子", (a) => num(a)],
      ["exposure_pct", "平均敞口", (a) => (a == null ? "—" : num(a, 0) + "%")], ["corr_vs_1", "与 #1 日收益相关", (a) => num(a)], ["post_months_pos", "后段盈利月", (a, m) => (a == null ? "—" : `${a} / ${m.post_months}`)], ["funding_usdt", "资金费（事后，U）", (a) => (a == null ? "—" : sgn(a))]];
    return `<table class="tbl st-mt"><thead><tr><th>指标</th>${cols.map((c) => `<th>${c[1]}</th>`).join("")}</tr></thead><tbody>${rows.map(([k, l, f]) => `<tr><td>${l}</td>${cols.map(([c]) => { const m = (x.metrics || {})[c] || {}; const val = m[k]; return `<td class="num ${["full_ret", "post_ret", "pre_ret"].includes(k) ? cls(val) : ""}">${k === "post_months_pos" ? f(val, m) : f(val)}</td>`; }).join("")}</tr>`).join("")}</tbody></table>`;
  }

  function btable(x) {
    const b = x.blends || {}; if (!Object.keys(b).length) return "";
    const names = [["ma_trend_only", "只用 #1"], ["equal_risk", "等风险"], ["50_50", "50 : 50"], ["80_20", "#1 占 80%"]];
    return `<table class="tbl st-mt"><thead><tr><th>与 #1 组合（真实费率）</th>${["gate", "okx"].map((v) => `<th colspan="3">${v === "okx" ? "OKX" : "Gate"}：整段 / 夏普 / 后段</th>`).join("")}</tr></thead><tbody>${names.map(([k, l]) => `<tr><td>${l}${k === "equal_risk" ? `（#1 权重 ${num(b["gate_equal_risk"]?.w_ma_trend * 100, 0)}%）` : ""}</td>${["gate", "okx"].map((v) => { const r = b[`${v}_${k}`] || {}; return `<td class="num ${cls(r.full_ret)}">${pp(r.full_ret)}</td><td class="num">${num(r.sharpe)}</td><td class="num ${cls(r.post_ret)}">${pp(r.post_ret)}</td>`; }).join("")}</tr>`).join("")}</tbody></table>`;
  }

  function openDetail(sid) {
    const byId = itemsById(), x = byId[sid], v = venue();
    const params = Object.entries(x.params || {}).map(([k, val]) => `<span class="st-param"><small>${esc(k)}</small>${esc(Array.isArray(val) ? val.join(" / ") : val)}</span>`).join("");
    modal(`<div class="st-modal-in">
      <div class="st-mh"><span class="st-no" style="background:${colorOf(x.no)}">#${x.no}</span><h3>${esc(x.name)}</h3>${tag(x.verdict?.status)}<button class="ico-btn sm st-close" type="button" aria-label="关闭">${ic("x")}</button></div>
      <div class="seg st-dtabs" role="tablist">${[["sum", "结论与指标"], ["curve", "权益曲线"], ["blend", "组合检验"], ["bt", "现跑回测"]].map(([k, l], i) => `<button type="button" role="tab" data-dt="${k}" class="${i ? "" : "on"}">${l}</button>`).join("")}</div>
      <div class="st-dbody">
        <section data-dp="sum"><p class="st-desc">${esc(x.desc)}</p><div class="st-params">${params}</div><p class="st-verdict ${STATUS_CLS[x.verdict?.status] || ""}">${esc(x.verdict?.reason || "")}</p><div class="tbl-wrap st-tw">${mtable(x)}</div></section>
        <section data-dp="curve" hidden><div class="note">真实费率 · 周度归一化权益（起点 = 1）· 悬停看每周数值与和 #1 的差</div><div class="st-big" id="stBig"></div></section>
        <section data-dp="blend" hidden>${x.id === "ma_trend" ? '<div class="empty">#1 是基准，组合检验见其它策略。</div>' : `<div class="note">日收益组合、每日再平衡；等风险权重只用 2026-03-05 前的波动算。判定：组合须在两所前段与后段夏普都高于只用 #1，且整段回撤不更深。</div><div class="tbl-wrap st-tw">${btable(x)}</div>`}</section>
        <section data-dp="bt" hidden><div class="st-btbar"><span class="note">用交易所官方公共 K 线现跑（${x.interval === "1h" ? "1h 约 9000 根" : "4h 4500 根"}），与 #1 同一批数据对比；策略参数用默认值，风控 / 费率 / 交易方式跟随当前设置。</span>${["gate", "okx"].map((vv) => `<button class="btn sm ${vv === v ? "" : "ghost"}" type="button" data-btv="${vv}">${ic("play")}${vv === "okx" ? "OKX" : "Gate"} 回测</button>`).join("")}</div><div id="stBt" class="st-btout">${ST.bt[sid] ? "" : '<div class="empty">点上方按钮运行。首次拉取官方历史约 10–40 秒。</div>'}</div></section>
      </div></div>`, (card) => {
      card.classList.add("st-modal");
      card.querySelector(".st-close").onclick = closeModal;
      const show = (k) => {
        card.querySelectorAll("[data-dt]").forEach((b) => b.classList.toggle("on", b.dataset.dt === k));
        card.querySelectorAll("[data-dp]").forEach((p) => (p.hidden = p.dataset.dp !== k));
        if (k === "curve") {
          const s = [{ name: `#${x.no} ${x.name}`, color: colorOf(x.no), pts: (x.curve || {})[v] || [] }];
          if (x.id !== "ma_trend") s.unshift({ name: "#1 默认", color: C1, pts: (byId.ma_trend.curve || {})[v] || [], dash: true, w: 1.6 });
          requestAnimationFrame(() => lineChart($("#stBig"), s));
        }
        if (k === "bt" && ST.bt[sid]) renderBt(sid);
      };
      card.querySelectorAll("[data-dt]").forEach((b) => (b.onclick = () => show(b.dataset.dt)));
      card.querySelectorAll("[data-btv]").forEach((b) => (b.onclick = () => runBt(sid, b.dataset.btv, b)));
    });
  }

  async function runBt(sid, vv, btn) {
    const out = $("#stBt"); if (!out) return;
    btn.disabled = true; out.innerHTML = '<div class="empty">正在拉取官方历史 K 线并回测…</div>';
    try { ST.bt[sid] = await api(`/api/strategies/${sid}/backtest`, { method: "POST", body: { venue: vv } }); renderBt(sid); }
    catch (e) { out.innerHTML = `<div class="empty neg">${esc(e.message)}</div>`; }
    finally { btn.disabled = false; }
  }

  function renderBt(sid) {
    const r = ST.bt[sid], out = $("#stBt"); if (!r || !out) return;
    const x = itemsById()[sid], m = r.summary, b = r.base_summary;
    const row = (l, a, c, f) => `<tr><td>${l}</td><td class="num">${f(a)}</td><td class="num">${f(c)}</td></tr>`;
    const P = (z) => pct(z), N = (z) => (z == null ? "—" : Number(z).toFixed(2)), I = (z) => (z == null ? "—" : z);
    out.innerHTML = `<div class="st-btgrid"><div class="st-btchart" id="stBtChart"></div>
      <table class="tbl st-mt"><thead><tr><th>${esc((r.venue || "").toUpperCase())} · ${esc(r.interval)}</th><th>#${x.no}</th><th>#1 默认</th></tr></thead><tbody>
      ${row("总收益", m.total_return, b.total_return, P)}${row("最大回撤", m.max_drawdown, b.max_drawdown, P)}${row("夏普", m.sharpe, b.sharpe, N)}${row("已平笔数", m.closed_trades, b.closed_trades, I)}${row("胜率", m.win_rate, b.win_rate, (z) => pct(z, 1))}${row("利润因子", m.profit_factor, b.profit_factor, N)}${row("手续费 (U)", m.fees_usdt, b.fees_usdt, N)}
      </tbody></table></div><div class="note">${tFull(m.start_time)} → ${tFull(m.end_time)} · 官方公共 K 线 · 做空 = USDT 永续${r.data_errors && Object.keys(r.data_errors).length ? " · 部分数据错误：" + esc(JSON.stringify(r.data_errors)).slice(0, 160) : ""}</div>`;
    lineChart($("#stBtChart"), [{ name: "#1 默认", color: C1, pts: r.base_curve, dash: true, w: 1.6 }, { name: `#${x.no} ${x.name}`, color: colorOf(x.no), pts: r.curve }]);
  }

  /* ---------- 影子子账本 ---------- */
  function renderShadow() {
    const host = $("#stBody"); host.className = "st-body st-shadow"; host.style.gridTemplateColumns = ""; host.style.gridTemplateRows = "";
    const books = (ST.shadow && ST.shadow.books) || [];
    if (!books.length) { host.innerHTML = '<div class="empty">目前没有「采用 / 观察」的候选策略，影子子账本未启动。</div>'; $("#stPager").innerHTML = ""; return; }
    host.innerHTML = `<div class="note st-shnote">每套「观察」策略各一本独立 1000U 纸面账：官方 K 线收盘确认事件触发决策，WS 每个 tick 检查止损，价格取官方实时价；只记录，不影响默认 1000U 账本，也不经过实盘闸门。</div>
      <div class="tbl-wrap st-shwrap"><table class="tbl st-sht"><thead><tr><th>策略</th><th>状态</th><th>权益 (U)</th><th>收益</th><th>持仓</th><th>浮动盈亏</th><th>已平 / 胜</th><th>最近决策</th></tr></thead><tbody>
      ${books.map((bk) => {
        const x = itemsById()[bk.sid] || { no: 0 };
        const up = bk.positions.reduce((a, p) => a + (p.upnl || 0), 0);
        return `<tr data-book="${esc(bk.sid)}" tabindex="0"><td><span class="st-no sm" style="background:${colorOf(x.no)}">#${x.no}</span>${esc(bk.name)}</td><td>${tag(bk.status)}</td>
          <td class="num" data-bk-eq="${esc(bk.sid)}" data-base="${bk.equity - up}">${f2(bk.equity)}</td><td class="num ${cls(bk.ret)}" data-bk-ret="${esc(bk.sid)}">${pct(bk.ret)}</td>
          <td>${bk.positions.length ? bk.positions.map((p) => `<span class="pill ${p.side} st-pp" title="${esc(p.symbol)} ${sideCn(p.side)} · ${mktCn(p.market)}">${esc(base(p.symbol))}</span>`).join(" ") : '<span class="muted">空仓</span>'}</td>
          <td class="num" data-bk-up="${esc(bk.sid)}">${sgn(up)}</td><td class="num" title="手续费 ${f2(bk.fees)} U">${bk.closed_trades} / ${bk.wins}</td>
          <td class="reason" title="${esc((bk.last_decision?.events || []).join("；"))}">${bk.last_decision ? tCompact(bk.last_decision.at) : "等待首个收盘事件"}</td></tr>`;
      }).join("")}</tbody></table></div>`;
    host.querySelectorAll("[data-book]").forEach((tr) => { tr.onclick = () => openBook(tr.dataset.book); tr.onkeydown = (e) => { if (e.key === "Enter") openBook(tr.dataset.book); }; });
    $("#stPager").innerHTML = "";
    liveBooks();
  }

  /* 用页面已有的官方实时报价（与持仓页同一路数据）重算影子账本浮盈与权益 */
  function liveBooks() {
    if (S.page !== "strategies" || !ST.shadow) return;
    (ST.shadow.books || []).forEach((bk) => {
      let up = 0;
      bk.positions.forEach((p) => {
        const q = typeof liveQuote === "function" ? liveQuote(p.symbol, p.market) : null, px = q ? Number(q.price) : p.mark;
        const d = p.side === "long" ? 1 : -1; up += d * p.qty * ((pxOk(px) ? px : p.mark) - p.entry);
      });
      const e = document.querySelector(`[data-bk-eq="${bk.sid}"]`); if (!e) return;
      const eq = Number(e.dataset.base) + up;
      e.textContent = f2(eq);
      const r = document.querySelector(`[data-bk-ret="${bk.sid}"]`); r.textContent = pct(eq / bk.start_equity - 1); r.className = `num ${cls(eq - bk.start_equity)}`;
      const u = document.querySelector(`[data-bk-up="${bk.sid}"]`); u.textContent = sgn(up); u.className = `num ${cls(up)}`;
    });
  }

  function openBook(sid) {
    const bk = (ST.shadow.books || []).find((b) => b.sid === sid); if (!bk) return;
    const x = itemsById()[sid] || { no: 0 };
    modal(`<div class="st-modal-in"><div class="st-mh"><span class="st-no" style="background:${colorOf(x.no)}">#${x.no}</span><h3>${esc(bk.name)} · 影子子账本</h3>${tag(bk.status)}<button class="ico-btn sm st-close" type="button" aria-label="关闭">${ic("x")}</button></div>
      <div class="st-dbody"><div class="note">${esc((bk.venue || "").toUpperCase())} · 起始 ${f2(bk.start_equity)} U · 建立于 ${tFull(bk.created_at)} · 最近决策 ${bk.last_decision ? tFull(bk.last_decision.at) : "—"}</div>
      <h4>持仓（${bk.positions.length}）</h4><div class="tbl-wrap st-tw"><table class="tbl"><thead><tr><th>标的</th><th>方向</th><th>入场</th><th>入场价</th><th>止损</th><th>名义 (U)</th><th>实时浮盈</th></tr></thead><tbody>
      ${bk.positions.map((p) => `<tr><td>${coin(p.symbol, "sm")}${esc(p.symbol)}</td><td><span class="pill ${p.side}">${sideCn(p.side)} · ${mktCn(p.market)}</span></td><td>${tCompact(p.entry_time)}</td><td class="num">${fp(p.entry)}</td><td class="num">${fp(p.stop)}</td><td class="num">${f2(p.notional)}</td><td class="num" data-live="pnl" data-sym="${esc(p.symbol)}" data-mkt="${esc(p.market)}" data-entry="${p.entry}" data-qty="${p.qty}" data-side="${p.side}" data-mark="${p.mark}" data-fee="${p.fee_in}">${sgn(p.upnl)}</td></tr>`).join("") || '<tr><td colspan="7" class="muted">空仓</td></tr>'}
      </tbody></table></div>
      <h4>最近平仓（${bk.recent_trades.length}）</h4><div class="tbl-wrap st-tw"><table class="tbl"><thead><tr><th>标的</th><th>方向</th><th>入场 → 离场</th><th>盈亏 (U)</th><th>原因</th></tr></thead><tbody>
      ${bk.recent_trades.slice(0, 8).map((t) => `<tr><td>${esc(t.symbol)}</td><td><span class="pill ${t.side}">${sideCn(t.side)}</span></td><td>${tCompact(t.entry_time)} → ${tCompact(t.exit_time)}</td><td class="num ${cls(t.pnl_usdt)}">${sgn(t.pnl_usdt)}</td><td class="reason">${esc(t.exit_reason)}</td></tr>`).join("") || '<tr><td colspan="5" class="muted">还没有平仓记录</td></tr>'}
      </tbody></table></div></div></div>`, (card) => { card.classList.add("st-modal"); card.querySelector(".st-close").onclick = closeModal; updateLiveCells(); });
  }

  /* ---------- 相关性 ---------- */
  function renderCorr() {
    const host = $("#stBody"); host.className = "st-body st-corr"; host.style.gridTemplateColumns = ""; host.style.gridTemplateRows = "";
    const items = ST.data.items, C = ST.data.corr || {};
    const cell = (a) => { if (a == null) return "<td>—</td>"; const k = Math.min(1, Math.abs(a)); const bg = a >= 0 ? `rgba(108,92,231,${0.08 + k * 0.55})` : `rgba(0,184,148,${0.08 + k * 0.55})`; return `<td class="num" style="background:${bg};${k > 0.55 ? "color:#fff" : ""}">${a.toFixed(2)}</td>`; };
    host.innerHTML = `<div class="note">Gate · 真实费率 · 日收益相关系数（2025-01-18 起共同区间）。越接近 0 越能分散 #1 的风险；负值 = 反向。</div>
      <div class="tbl-wrap st-cw"><table class="tbl st-ct"><thead><tr><th></th>${items.map((x) => `<th title="${esc(x.name)}">#${x.no}</th>`).join("")}</tr></thead><tbody>
      ${items.map((a) => `<tr><td><span class="st-no sm" style="background:${colorOf(a.no)}">#${a.no}</span>${esc(a.name)}</td>${items.map((b) => cell((C[a.id] || {})[b.id])).join("")}</tr>`).join("")}</tbody></table></div>
      <div class="note">只用 2026-03-05 前数据选参的前推检验：${(ST.data.walkforward || []).filter((w) => w.venue === "gate").map((w) => `${esc((itemsById()[w.strategy] || {}).name || w.strategy)} 前段夏普 ${num(w.pre_sharpe)} → 后段 ${pp(w.post_ret)}`).join("；")}。</div>`;
    $("#stPager").innerHTML = "";
  }

  new MutationObserver(() => { const m = document.getElementById("modal"); if (m && m.classList.contains("hidden")) document.getElementById("modalCard")?.classList.remove("st-modal"); })
    .observe(document.getElementById("modal") || document.body, { attributes: true, attributeFilter: ["class"] });
})();
