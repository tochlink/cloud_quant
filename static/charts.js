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
      return c;
    },
    equity(el, pts) {
      const c = this.make(el);
      c.addAreaSeries({ lineColor: "#4b3aa6", topColor: "rgba(108,92,231,.35)", bottomColor: "rgba(108,92,231,0)", lineWidth: 2, title: "权益" })
        .setData(pts.map((p) => ({ time: p.time, value: p.equity })));
      const dd = c.addHistogramSeries({ color: "rgba(94,224,214,.55)", priceScaleId: "dd", title: "回撤%" });
      c.priceScale("dd").applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
      dd.setData(pts.map((p) => ({ time: p.time, value: (p.drawdown || 0) * 100 })));
      c.timeScale().fitContent();
      return c;
    },
  };
})();
