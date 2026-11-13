/* 小型 SVG 图表（摘要卡片用）+ lightweight-charts 封装 */
(function () {
  /* 统一时间格式：按 kean 所在时区 Asia/Shanghai 显示，标注“北京时间” */
  const TZ = "Asia/Shanghai", LABEL = "北京时间", _f = {};
  function parts(d, o) {
    const k = JSON.stringify(o);
    const f = _f[k] || (_f[k] = new Intl.DateTimeFormat("en-CA", { timeZone: TZ, hourCycle: "h23", ...o }));
    return Object.fromEntries(f.formatToParts(d).map((p) => [p.type, p.value]));
  }
  const toD = (x) => (x instanceof Date ? x : typeof x === "number" ? new Date(x * 1000) : new Date(x));
  window.PT = { /* 显示时区助手（历史名字 PT，现为北京时间） */
    tz: TZ, label: LABEL,
    hour(d = new Date()) { return +parts(d, { hour: "2-digit" }).hour; },
    short(x) { const d = toD(x); if (isNaN(d)) return String(x); const p = parts(d, { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); return `${p.month}-${p.day} ${p.hour}:${p.minute} ${LABEL}`; },
    full(x, sec) { const d = toD(x); if (isNaN(d)) return String(x); const p = parts(d, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", ...(sec ? { second: "2-digit" } : {}) }); return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute}${sec ? ":" + p.second : ""} ${LABEL}`; },
    clock(x) { const d = toD(x); const p = parts(d, { hour: "2-digit", minute: "2-digit" }); return `${p.hour}:${p.minute}`; },
    tick(ts, type) { const d = toD(ts); const p = parts(d, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
      return type === 0 ? p.year : type === 1 ? `${p.year}-${p.month}` : type === 2 ? `${p.month}-${p.day}` : `${p.hour}:${p.minute}`; },
  };
  const W = 260, H = 90;
  let gid = 0;
  function norm(vals, pad = 8) {
    const v = vals.filter((x) => x != null && isFinite(x));
    if (!v.length) return { pts: [], min: 0, max: 1 };
    let min = Math.min(...v), max = Math.max(...v);
    if (max - min < 1e-9) { max += 1; min -= 1; }
    const pts = v.map((y, i) => [v.length === 1 ? W / 2 : (i / (v.length - 1)) * W, pad + (1 - (y - min) / (max - min)) * (H - pad * 2)]);
    return { pts, min, max };
  }
  function smooth(pts) {
    if (pts.length < 2) return pts.length ? `M0 ${pts[0][1]} L${W} ${pts[0][1]}` : "";
    let d = `M${pts[0][0]} ${pts[0][1]}`;
    for (let i = 1; i < pts.length; i++) {
      const [x0, y0] = pts[i - 1], [x1, y1] = pts[i], cx = (x0 + x1) / 2;
      d += ` C${cx} ${y0},${cx} ${y1},${x1} ${y1}`;
    }
    return d;
  }
  function empty(msg) {
    return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none"><text x="${W / 2}" y="${H / 2}" text-anchor="middle" font-size="11" fill="#b5b2cf">${msg || "暂无数据"}</text></svg>`;
  }

  const KIND_COLOR = {
    "开仓": "#73f0e0", "平仓": "#c9c2f5", "调仓": "#8ec0ff",
    "止损": "#ff7a8a", "止盈": "#ffd56a", "手动平仓": "#ffb3c0", "一键清仓": "#ff9f6b",
  };
  const KIND_RANK = { "止损": 0, "止盈": 1, "手动平仓": 2, "一键清仓": 3, "平仓": 4, "调仓": 5, "开仓": 6 };
  function primaryKind(evs) {
    let best = evs[0] && evs[0].kind, r = 99;
    for (const e of evs || []) {
      const k = KIND_RANK[e.kind];
      if (k != null && k < r) { r = k; best = e.kind; }
    }
    return best || "开仓";
  }
  function hexA(hex, a) { const h = hex.replace("#", ""); const v = parseInt(h.length === 3 ? h.split("").map((x) => x + x).join("") : h, 16); return `rgba(${(v >> 16) & 255},${(v >> 8) & 255},${v & 255},${a})`; }
  function escH(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({ "&": "&#38;", "<": "&#60;", ">": "&#62;", '"': "&#34;", "'": "&#39;" }[c]));
  }
  function fmtN(x, d = 2) {
    if (x == null || !isFinite(x)) return "—";
    return Number(x).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function sgnN(x, d = 2) { return (x > 0 ? "+" : x < 0 ? "" : "") + fmtN(x, d); }
  function pctN(x) { return (x > 0 ? "+" : x < 0 ? "" : "") + (isFinite(x) ? (x * 100).toFixed(2) : "—") + "%"; }
  function clsN(x) { return x > 0 ? "pos" : x < 0 ? "neg" : ""; }
  function classifyReason(reason) {
    const r = reason || "";
    if (r.includes("止盈")) return "止盈";
    if (r.includes("ATR止损") || r.includes("止损")) return "止损";
    if (r.includes("手动平仓")) return "手动平仓";
    if (r.includes("一键清仓")) return "一键清仓";
    if (r.includes("调仓")) return "调仓";
    return "平仓";
  }
  function evRow(e) {
    const col = KIND_COLOR[e.kind] || "#73f0e0";
    const bits = [e.symbol, e.side_cn || (e.side === "long" ? "多" : e.side === "short" ? "空" : "")]
      .filter(Boolean).join(" ");
    const px = e.price != null && isFinite(e.price) ? " · " + fmtN(e.price, e.price >= 100 ? 1 : 4) : "";
    const sub = [];
    if (e.realized_pnl != null && isFinite(e.realized_pnl)) sub.push("已实现 " + sgnN(e.realized_pnl) + " USDT");
    if (e.reason) sub.push(e.reason);
    return `<div class="eq-ev"><span class="eq-dot" style="background:${col}"></span><div><div><b>${escH(e.kind)}</b>${bits ? " " + escH(bits) : ""}${escH(px)}</div>${sub.length ? `<div class="eq-ev-sub">${escH(sub.join(" · "))}</div>` : ""}</div></div>`;
  }
  function tipEvents(evs) {
    evs = evs || [];
    if (!evs.length) return "";
    const same = evs.length > 1 && evs.every((e) => e.kind === evs[0].kind);
    if (same) {
      const rest = evs.slice(1).map((e) => e.symbol).filter(Boolean);
      const extra = rest.length
        ? `<div class="eq-ev-sub">另有 ${rest.length} 笔（${escH(rest.slice(0, 4).join("、"))}${rest.length > 4 ? " 等" : ""}）</div>`
        : "";
      return `<div class="eq-tip-evs">${evRow(evs[0])}${extra}</div>`;
    }
    const rows = evs.slice(0, 2).map(evRow).join("");
    const more = evs.length > 2 ? `<div class="eq-ev-sub">另有 ${evs.length - 2} 笔</div>` : "";
    return `<div class="eq-tip-evs">${rows}${more}</div>`;
  }
  function tipHtml(points, i, starting) {
    const p = points[i];
    const prev = i > 0 ? points[i - 1] : null;
    const eq = p.equity;
    const dPrev = prev ? eq - prev.equity : null;
    const pPrev = prev && prev.equity ? dPrev / prev.equity : null;
    const dStart = starting != null ? eq - starting : null;
    const pStart = starting ? dStart / starting : null;
    return `<div class="eq-tip-t">${escH(window.PT.full(p.time, true))}</div>
      <div class="eq-tip-eq">权益 <b>${fmtN(eq)}</b> USDT</div>
      <div class="eq-tip-row ${dPrev == null ? "" : clsN(dPrev)}">较上一点 ${dPrev == null ? "—" : `${sgnN(dPrev)}（${pctN(pPrev)}）`}</div>
      <div class="eq-tip-row ${dStart == null ? "" : clsN(dStart)}">较起始 ${dStart == null ? "—" : `${sgnN(dStart)}（${pctN(pStart)}）`}</div>
      ${tipEvents(p.events)}`;
  }
  function placeTip(host, tip, ev, boxEl) {
    const box = (boxEl || host).getBoundingClientRect();
    const origin = host.getBoundingClientRect();
    const tw = tip.offsetWidth, th = tip.offsetHeight, pad = 6;
    let vx = ev.clientX + 14, vy = ev.clientY - th - 10;
    if (vx + tw > box.right - pad) vx = ev.clientX - tw - 14;
    if (vx < box.left + pad) vx = box.left + pad;
    if (vx + tw > box.right - pad) vx = box.right - pad - tw;
    if (vy < box.top + pad) vy = ev.clientY + 16;
    if (vy + th > box.bottom - pad) vy = box.bottom - pad - th;
    if (vy < box.top + pad) vy = box.top + pad;
    tip.style.left = `${Math.round(vx - origin.left)}px`;
    tip.style.top = `${Math.round(vy - origin.top)}px`;
  }
  function toUnix(t) {
    if (t == null || t === "") return null;
    if (typeof t === "number") return t > 1e12 ? Math.floor(t / 1000) : t;
    const d = new Date(t);
    return isNaN(d) ? null : Math.floor(d.getTime() / 1000);
  }
  function attachTradeEvents(pts, trades) {
    const points = pts.map((p) => ({ ...p, events: p.events ? p.events.slice() : [] }));
    if (!points.length || !trades || !trades.length) return points;
    function snap(ts) {
      if (ts == null) return null;
      let best = 0, bd = Infinity;
      for (let i = 0; i < points.length; i++) {
        const d = Math.abs(points[i].time - ts);
        if (d < bd) { bd = d; best = i; }
      }
      return best;
    }
    for (const t of trades) {
      const side = t.side || "";
      const sideCn = side === "long" ? "多" : side === "short" ? "空" : "";
      const et = toUnix(t.entry_time);
      const ei = snap(et);
      if (ei != null && et != null) {
        points[ei].events.push({
          time: t.entry_time, kind: "开仓", symbol: t.symbol, market: t.market,
          side, side_cn: sideCn, price: t.entry_price, realized_pnl: null, reason: "", source: "backtest",
        });
      }
      const xt = toUnix(t.exit_time);
      const xi = snap(xt);
      if (xi != null && xt != null) {
        points[xi].events.push({
          time: t.exit_time, kind: classifyReason(t.exit_reason), symbol: t.symbol, market: t.market,
          side, side_cn: sideCn, price: t.exit_price, realized_pnl: t.pnl_usdt, reason: t.exit_reason || "", source: "backtest",
        });
      }
    }
    return points;
  }

    window.MiniCharts = {
    area(vals, color = "#4b3aa6") {
      const { pts } = norm(vals, 10);
      if (pts.length < 2) return empty("运行后生成权益曲线");
      const d = smooth(pts);
      return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none"><path d="${d} L${W} ${H} L0 ${H}Z" fill="${color}"/></svg>`;
    },
    spark(vals, color = "#73f0e0") {
      const { pts } = norm(vals, 10);
      if (pts.length < 2) return empty("跑几轮后生成权益曲线");
      const d = smooth(pts), id = "sp" + ++gid, last = pts[pts.length - 1];
      return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none"><defs><linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".35"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs><path d="${d} L${W} ${H} L0 ${H}Z" fill="url(#${id})"/><path d="${d}" stroke="${color}" stroke-width="2.2" fill="none" vector-effect="non-scaling-stroke"/><circle cx="${last[0] - 3}" cy="${last[1]}" r="3.5" fill="${color}"/></svg>`;
    },
    equityHover(host, opts) {
      if (!host) return;
      const points = (opts && opts.points) || [];
      const starting = (opts && opts.starting) != null ? opts.starting : (points[0] && points[0].equity);
      const color = (opts && opts.color) || "#73f0e0";
      const boxEl = (opts && opts.box) || host.closest(".hero") || host.closest(".chart-box") || host;
      host.classList.add("eq-hover");
      host.innerHTML = "";
      if (points.length < 2) { host.innerHTML = empty("跑几轮后生成权益曲线"); return; }
      const vals = points.map((p) => p.equity);
      const { pts } = norm(vals, 10);
      const d = smooth(pts), id = "sp" + ++gid, last = pts[pts.length - 1];
      const dots = points.map((p, i) => {
        if (!p.events || !p.events.length) return "";
        const col = KIND_COLOR[primaryKind(p.events)] || color;
        return `<circle class="eq-ev-dot" cx="${pts[i][0]}" cy="${pts[i][1]}" r="3.3" fill="${col}" stroke="#fff" stroke-width="1" vector-effect="non-scaling-stroke"/>`;
      }).join("");
      host.innerHTML = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" class="eq-svg"><defs><linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".35"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs><path d="${d} L${W} ${H} L0 ${H}Z" fill="url(#${id})"/><path d="${d}" stroke="${color}" stroke-width="2.2" fill="none" vector-effect="non-scaling-stroke"/>${dots}<circle cx="${last[0] - 3}" cy="${last[1]}" r="3.5" fill="${color}"/><g class="eq-cross" hidden="hidden"><line class="eq-xhair" y1="0" y2="${H}" stroke="rgba(255,255,255,.8)" stroke-width="1" vector-effect="non-scaling-stroke"/><circle class="eq-focus" r="5" fill="${color}" stroke="#fff" stroke-width="1.7" vector-effect="non-scaling-stroke"/></g></svg><div class="eq-tip" hidden></div>`;
      const svg = host.querySelector("svg");
      const cross = host.querySelector(".eq-cross");
      const xhair = host.querySelector(".eq-xhair");
      const foc = host.querySelector(".eq-focus");
      const tip = host.querySelector(".eq-tip");
      const showAt = (i, ev) => {
        const [x, y] = pts[i];
        cross.removeAttribute("hidden");
        xhair.setAttribute("x1", x); xhair.setAttribute("x2", x);
        foc.setAttribute("cx", x); foc.setAttribute("cy", y);
        tip.innerHTML = tipHtml(points, i, starting);
        tip.hidden = false;
        placeTip(host, tip, ev, boxEl);
      };
      const hide = () => { cross.setAttribute("hidden", "hidden"); tip.hidden = true; };
      const idxFrom = (ev) => {
        const r = svg.getBoundingClientRect();
        if (r.width <= 0) return 0;
        const vx = ((ev.clientX - r.left) / r.width) * W;
        let best = 0, bd = Infinity;
        for (let i = 0; i < pts.length; i++) {
          const dist = Math.abs(pts[i][0] - vx);
          if (dist < bd) { bd = dist; best = i; }
        }
        return best;
      };
      const onMove = (ev) => { if (ev.pointerType === "touch") ev.preventDefault(); showAt(idxFrom(ev), ev); };
      host.addEventListener("pointermove", onMove);
      host.addEventListener("pointerdown", onMove);
      host.addEventListener("pointerleave", hide);
      host.addEventListener("pointercancel", hide);
    },
    line(vals, color = "#2cc4c9") {
      const { pts } = norm(vals, 14);
      if (pts.length < 2) return empty("暂无已平仓盈亏");
      const d = smooth(pts);
      const dots = [pts[Math.floor(pts.length / 3)], pts[Math.floor((2 * pts.length) / 3)]]
        .map((p) => `<circle cx="${p[0]}" cy="${p[1]}" r="4.5" fill="${color}" stroke="#fff" stroke-width="2"/>`).join("");
      const id = "lg" + ++gid;
      return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none"><defs><linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".25"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs><path d="${d} L${W} ${H} L0 ${H}Z" fill="url(#${id})"/><path d="${d}" stroke="${color}" stroke-width="2.2" fill="none"/>${dots}</svg>`;
    },
    bars(vals) {
      const v = vals.slice(-18);
      if (!v.length) return empty("暂无回撤数据");
      const mx = Math.max(...v.map((x) => Math.abs(x)), 1e-6), bw = W / (v.length * 1.6);
      return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">` + v.map((x, i) => {
        const h = Math.max(4, (Math.abs(x) / mx) * (H - 14)), xx = 8 + i * (W - 16) / v.length;
        return `<rect x="${xx}" y="${H - h}" width="${bw}" height="${h}" rx="${bw / 2}" fill="${i % 2 ? "#5ee0d6" : "#4b3aa6"}"/>`;
      }).join("") + `</svg>`;
    },
    donut(parts) {
      const tot = parts.reduce((a, p) => a + Math.max(0, p.v), 0);
      if (tot <= 0) return `<svg viewBox="0 0 100 100"><circle cx="50" cy="50" r="34" stroke="#ece8fd" stroke-width="22" fill="none"/></svg>`;
      let a0 = -Math.PI / 2, out = "";
      parts.forEach((p) => {
        const f = Math.max(0, p.v) / tot; if (f <= 0) return;
        const a1 = a0 + f * Math.PI * 2 - (f < 1 ? 0.0001 : 0.001), r = 34, large = f > 0.5 ? 1 : 0;
        const x0 = 50 + r * Math.cos(a0), y0 = 50 + r * Math.sin(a0), x1 = 50 + r * Math.cos(a1), y1 = 50 + r * Math.sin(a1);
        out += `<path d="M${x0} ${y0} A${r} ${r} 0 ${large} 1 ${x1} ${y1}" stroke="${p.c}" stroke-width="${p.w || 22}" fill="none" stroke-linecap="butt"/>`;
        a0 = a1;
      });
      return `<svg viewBox="0 0 100 100">${out}<circle cx="50" cy="50" r="15" fill="#fff"/></svg>`;
    },
  };

  const base = {
    layout: { attributionLogo: false, background: { type: "solid", color: "#ffffff" }, textColor: "#6f6c92", fontFamily: "Poppins, PingFang SC, sans-serif" },
    grid: { vertLines: { color: "#f3f1fb" }, horzLines: { color: "#f3f1fb" } },
    rightPriceScale: { borderColor: "#ece8fd" },
    timeScale: { borderColor: "#ece8fd", timeVisible: true, tickMarkFormatter: (ts, type) => window.PT.tick(ts, type) },
    crosshair: { mode: 1 },
    localization: { locale: "zh-CN", timeFormatter: (ts) => window.PT.full(ts) },
  };
  window.BigCharts = {
    make(el, h) {
      el.innerHTML = "";
      const c = LightweightCharts.createChart(el, { ...base, width: el.clientWidth, height: h || el.clientHeight });
      const ro = new ResizeObserver(() => { if (!el.isConnected) { ro.disconnect(); return; } c.applyOptions({ width: el.clientWidth, height: h || el.clientHeight }); });
      ro.observe(el);
      return c;
    },
    candles(el, d) {
      const c = this.make(el);
      const s = c.addCandlestickSeries({ upColor: "#25b07a", downColor: "#e5536b", borderVisible: false, wickUpColor: "#25b07a", wickDownColor: "#e5536b" });
      s.setData(d.candles);
      c.addLineSeries({ color: "#2cc4c9", lineWidth: 2, title: "快线" }).setData(d.fast);
      c.addLineSeries({ color: "#6c5ce7", lineWidth: 2, title: "慢线" }).setData(d.slow);
      s.setMarkers(d.markers.map((m) => ({ time: m.time, position: m.signal > 0 ? "belowBar" : m.signal < 0 ? "aboveBar" : "inBar",
        color: m.signal > 0 ? "#25b07a" : m.signal < 0 ? "#e5536b" : "#9a98b8", shape: m.signal > 0 ? "arrowUp" : m.signal < 0 ? "arrowDown" : "circle",
        text: m.signal > 0 ? "做多" : m.signal < 0 ? "做空" : "空仓" })));
      c.timeScale().fitContent();
      c._candle = s;
      c._last = d.candles.length ? d.candles[d.candles.length - 1].time : 0;
      c._lastClosed = c._last; // 已收盘最后一根；未收盘跳动只更新 c._last
      c._lastBar = d.candles.length ? { ...d.candles[d.candles.length - 1] } : null;
      return c;
    },
    /* 同比叠加：横轴 = 参考年 2000 的同月同日（UTC），刻度只显示 月-日。
       style = "k"（默认，每年一组 K 线：空心 = 收涨、实心 = 收跌，颜色区分年份，同一天按年份并排）| "line"（只画收盘线）。
       悬浮：十字线 + 固定宽度提示框（各年日期 / 开高低收 / 涨跌 / 年内涨跌，以及最新年份与其他年份的差异）。 */
    yoy(el, d, colorOf, style) {
      el.innerHTML = "";
      const K = style !== "line";
      const md = (ts) => { const x = new Date(ts * 1000); return `${String(x.getUTCMonth() + 1).padStart(2, "0")}-${String(x.getUTCDate()).padStart(2, "0")}`; };
      const pfmt = (v) => d.mode === "pct" ? (v >= 0 ? "+" : "") + v.toFixed(1) + "%" : (Math.abs(v) >= 100 ? v.toFixed(2) : v.toPrecision(5));
      const c = LightweightCharts.createChart(el, { ...base, width: el.clientWidth, height: el.clientHeight,
        crosshair: { mode: 0 },
        timeScale: { borderColor: "#ece8fd", timeVisible: false, tickMarkFormatter: (ts) => md(ts) },
        localization: { locale: "zh-CN", timeFormatter: (ts) => md(ts), priceFormatter: pfmt } });
      const ro = new ResizeObserver(() => { if (!el.isConnected) { ro.disconnect(); return; } c.applyOptions({ width: el.clientWidth, height: el.clientHeight }); });
      ro.observe(el);
      const n = d.series.length;
      const idx = []; // 每年：基准时间（整点）→ 点序号
      d.series.forEach((sr, i) => {
        const map = new Map(); idx.push(map);
        if (!sr.points.length) return;
        const col = colorOf(i, n), off = K ? i * 60 : 0; // K 线模式每年错开 i 分钟 → 同一天的各年 K 线并排、不重叠
        const seen = new Set(), pts = [];
        sr.points.forEach((p, k) => { if (!seen.has(p.time)) { seen.add(p.time); map.set(p.time, k); pts.push(p); } });
        if (K) {
          const s = c.addCandlestickSeries({ upColor: hexA(col, 0.14), downColor: col, borderVisible: true, borderUpColor: col, borderDownColor: col,
            wickUpColor: col, wickDownColor: col, title: String(sr.year), priceLineVisible: false, lastValueVisible: true });
          s.setData(pts.map((p) => ({ time: p.time + off, open: p.open ?? p.value, high: p.high ?? p.value, low: p.low ?? p.value, close: p.close ?? p.value })));
        } else {
          c.addLineSeries({ color: col, lineWidth: i === n - 1 ? 3 : 2, title: String(sr.year), priceLineVisible: false })
            .setData(pts.map((p) => ({ time: p.time, value: p.value })));
        }
      });
      c.timeScale().fitContent();
      c._n = 0;
      // ---- 悬浮提示 ----
      const tip = document.createElement("div"); tip.className = "yoy-tip"; tip.style.display = "none"; el.appendChild(tip);
      const fp = (v) => (v == null || !isFinite(v) ? "—" : Math.abs(v) >= 1000 ? v.toLocaleString("en-US", { maximumFractionDigits: 2 }) : Math.abs(v) >= 1 ? v.toFixed(4).replace(/0+$/, "").replace(/\.$/, "") : v.toPrecision(4));
      const sg = (v, dgt = 2, unit = "%") => (v == null || !isFinite(v) ? "—" : (v >= 0 ? "+" : "\u2212") + Math.abs(v).toFixed(dgt) + unit);
      const cl = (v) => (v == null || !isFinite(v) ? "" : v >= 0 ? "pos" : "neg");
      c.subscribeCrosshairMove((pr) => {
        if (!pr || pr.time == null || !pr.point || pr.point.x < 0 || pr.point.y < 0) { tip.style.display = "none"; return; }
        const bt = Number(pr.time) - (Number(pr.time) % 3600);
        const rows = d.series.map((sr, i) => {
          const k = idx[i] && idx[i].get(bt);
          if (k == null) return { sr, i, p: null };
          const p = sr.points[k], prev = k > 0 ? sr.points[k - 1] : null, r = p.raw || [p.value, p.value, p.value, p.value];
          const prc = prev ? (prev.raw ? prev.raw[3] : prev.value) : r[0];
          return { sr, i, p, r, chg: prc ? (r[3] / prc - 1) * 100 : null, ytd: sr.first_close ? (r[3] / sr.first_close - 1) * 100 : null };
        });
        if (!rows.some((x) => x.p)) { tip.style.display = "none"; return; }
        const head = `<tr><th>年份</th><th>日期</th><th>开</th><th>高</th><th>低</th><th>收</th><th>涨跌</th><th>年内</th></tr>`;
        const body = rows.map((x) => `<tr><td><i style="background:${colorOf(x.i, n)}"></i>${x.sr.year}</td>${x.p ? `<td>${escH(String(x.p.date).slice(5, d.interval === "4h" ? 16 : 10))}</td><td>${fp(x.r[0])}</td><td>${fp(x.r[1])}</td><td>${fp(x.r[2])}</td><td><b>${fp(x.r[3])}</b></td><td class="${cl(x.chg)}">${sg(x.chg)}</td><td class="${cl(x.ytd)}">${sg(x.ytd, 1)}</td>` : `<td colspan="7" class="muted">当天无 K 线</td>`}</tr>`).join("");
        const L = rows[rows.length - 1];
        const diffs = L && L.p ? rows.slice(0, -1).filter((x) => x.p).map((x) => {
          const dp = L.r[3] - x.r[3], dpc = (L.r[3] / x.r[3] - 1) * 100, gap = L.ytd - x.ytd;
          return `<div class="yoy-diff">${L.sr.year} vs ${x.sr.year}：收盘差 <b class="${cl(dp)}">${dp >= 0 ? "+" : "\u2212"}${fp(Math.abs(dp))}</b>（<span class="${cl(dpc)}">${sg(dpc)}</span>）· 年内涨跌差 <b class="${cl(gap)}">${sg(gap, 1, " pts")}</b></div>`;
        }).join("") : "";
        tip.innerHTML = `<table>${head}${body}</table>${diffs}`;
        tip.style.display = "block";
        const W = el.clientWidth, H = el.clientHeight, tw = tip.offsetWidth, th = tip.offsetHeight;
        let x = pr.point.x + 16; if (x + tw > W - 70) x = pr.point.x - tw - 16; // 右侧留出价格轴
        x = Math.max(4, Math.min(x, W - tw - 4));
        const y = Math.max(4, Math.min(H - th - 28, 6));
        tip.style.left = x + "px"; tip.style.top = y + "px";
      });
      c._yoyTip = tip;
      return c;
    },
    equity(el, pts, extra) {
      const c = this.make(el);
      const area = c.addAreaSeries({ lineColor: "#4b3aa6", topColor: "rgba(108,92,231,.35)", bottomColor: "rgba(108,92,231,0)", lineWidth: 2, title: "权益" });
      area.setData((pts || []).map((p) => ({ time: p.time, value: p.equity })));
      const dd = c.addHistogramSeries({ color: "rgba(94,224,214,.55)", priceScaleId: "dd", title: "回撤%" });
      c.priceScale("dd").applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
      dd.setData((pts || []).map((p) => ({ time: p.time, value: (p.drawdown || 0) * 100 })));
      const start = extra && extra.starting != null ? extra.starting : (pts && pts[0] && pts[0].equity);
      const attached = attachTradeEvents(pts || [], (extra && extra.trades) || []);
      const markers = [];
      for (const p of attached) {
        if (!p.events || !p.events.length) continue;
        const kind = primaryKind(p.events);
        markers.push({ time: p.time, position: "aboveBar", color: KIND_COLOR[kind] || "#4b3aa6", shape: "circle", text: kind });
      }
      if (markers.length) area.setMarkers(markers);
      let tip = el.querySelector(".eq-tip");
      if (!tip) { tip = document.createElement("div"); tip.className = "eq-tip eq-tip-light"; tip.hidden = true; el.appendChild(tip); }
      const hide = () => { tip.hidden = true; };
      c.subscribeCrosshairMove((param) => {
        if (!param || param.time == null || !param.point || param.point.x < 0 || param.point.y < 0) { hide(); return; }
        const t = param.time;
        let best = 0, bd = Infinity;
        for (let i = 0; i < attached.length; i++) {
          const dist = Math.abs(attached[i].time - t);
          if (dist < bd) { bd = dist; best = i; }
        }
        tip.innerHTML = tipHtml(attached, best, start);
        tip.hidden = false;
        const box = el.getBoundingClientRect();
        placeTip(el, tip, { clientX: box.left + param.point.x, clientY: box.top + param.point.y }, el);
      });
      el.addEventListener("pointerleave", hide);
      c.timeScale().fitContent();
      return c;
    },
  };
})();
