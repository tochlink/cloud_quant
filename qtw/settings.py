"""非敏感配置，存于 SQLite（data/qtw.sqlite 的 settings 表）。API 密钥不在这里，见 qtw/vault.py。"""
from __future__ import annotations

import copy
import os
import threading
from typing import Any

import json

import yaml

from . import db
from .paths import DATA_DIR, ensure_dirs
from .timeutil import iso, utcnow

LIVE_CONFIRM_PHRASE = "我已了解实盘交易可能亏损全部资金"
REGIME_SYMBOLS = ("BTCUSDT", "ETHUSDT")  # 体制过滤（btc_regime_ma）可选的来源现货币种

DEFAULTS: dict[str, Any] = {
    "venue": "okx",  # okx | gate —— 行情与（未来的）实盘交易所
    "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "AVAXUSDT"],
    "strategy": {
        "rule_id": "dual_ma_trend_4h_v1",
        "interval": "4h",
        # 2026-11-10 12:30：由 20/60 改为 50/150。官方 Gate / OKX 4h 长历史（4500 根，2024-10 起）上，
        # 20/60 在调参窗口之前（2024-12-31 ~ 2026-03-05）亏 −41%（回撤 −47.6%）；40~60 / 120~200 慢均线是一片平台，
        # 50/150 两段都为正：Gate +27.0% / +21.9%、OKX +30.3% / +25.0%，整段回撤约 −28%，压力费率同向
        # （output/research_gate_long_history_param_revalidation.csv、research_gate_long_history_slow_ma_plateau.csv）
        "fast_ma": 50,
        "slow_ma": 150,
        "atr_period": 14,
        "atr_stop_mult": 2.0,
        "confirm_bars": 2,  # 2026-11-10：OKX+Gate 各 3 段滚动样本外均优于 1
        # 2026-11-10：仅入场的趋势过滤（多需收盘>SMA100，空需收盘<SMA100；不强制平仓）。
        # 6 段不重叠窗口：前 3 段选出 100，后 3 段（未参与选择）在 OKX/Gate、4/14bps 下均优于不过滤。0=关闭
        "trend_ma": 100,
        # 2026-11-10：空头熔断。影子「只做空」账本最近 N 根已平仓合计亏损时暂停新开空单（因果，不平已有仓）。
        # 6/12 段不重叠窗口：前半段从 {60,120,240} 选出 60，后半段（未参与选择）在 OKX/Gate、4/14bps 下均明显优于不熔断。0=关闭
        # 2026-11-10 12:30：随 50/150 改为 0（关闭）。长历史上 50/150 + 熔断 60 调参前段只有 +7.8%（不熔断 +27.0%），
        # 2025Q1 熔断拦掉了盈利空单。仍可手动设为 10–500 开启
        "short_breaker_bars": 0,
        # 2026-11-10 12:45：BTC 熊市体制过滤（仅入场）。BTC 现货 4h 收盘 < SMA_N（上一根已收盘）时不新开多单，不平已有仓、空单不受影响。
        # 1200 根 4h ≈ 日线 SMA200。Gate / OKX 官方 4500 根长历史、50/150 基线：调参前段（未见）Gate +27.0%→+42.2%、OKX +30.3%→+45.6%，
        # 2026-03 后 +21.9%→+56.7% / +25.0%→+57.9%；N = 300–1500 全部两段都优于不过滤，压力费率（现货 20 / 永续 15.1 bps）同向；
        # 滚动选 N（回看 90/180/365 天、测下 30 天）12 组全部优于不过滤。最大回撤不变（约 −28%）。0=关闭
        # （output/research_long_history_regime_filter_and_knobs_50_150.csv、research_long_history_btc_regime_fee_stress.csv、
        #   research_long_history_btc_regime_walkforward.csv）
        "btc_regime_ma": 1200,
        # 2026-11-14：可选 BTC 体制线多周期投票（默认 0 = 单线 SMA_N）。k > 0 时改为：BTC 收盘低于 N×(0.5, 0.75, 1, 1.25, 1.5)
        # 五条 SMA（N = 1200 → 600 / 900 / 1200 / 1500 / 1800）中 ≥ k 条才拦新开多。深历史未见段 k = 3：日 Sharpe OKX8 / Gate8 / OKX7
        # 0.81 / 0.31 / 0.80（单线 0.71 / 0.09 / 0.77），压力费同向、回撤更浅，2026-03 后与单线逐位相同；但差异只来自少数几次体制切换，
        # 强观察、未改默认（scratch/drgv/run.py、output/research_deep_history_btc_regime_vote.csv）。k = 1 或 ≥ 4 均已否决。
        "btc_regime_vote_k": 0,
        # 2026-11-14：可选体制线来源币种（默认 BTCUSDT）。ETHUSDT = 用同所官方 ETH 现货收盘 < SMA_N 拦新开多（其余逻辑与 BTC 完全相同）。
        # 双重留出 5 组深历史未见段日 Sharpe 1.09 / 1.00 / 0.38 / 0.40 / −0.01（BTC 0.71 / 0.77 / 0.09 / 0.24 / −0.32），2026-03 后收益 5/5 更高，
        # N 1050–1350 平台平滑；但调参窗口 2026-03 前少 23–37 点，强观察、未改默认（scratch/drsrc/run.py、output/research_regime_source_swap_deep.csv）。
        "btc_regime_symbol": "BTCUSDT",
        # 2026-11-11：可选震荡指数入场闸门（默认关闭）。上一根 CHOP_n > chop_max 时不新开 / 反手开仓，离场、止损、调仓不变。
        # 严格月度 walk-forward（候选 off + n{42,56,70}×T{48,50,52}，回看 3/6/12 个月按 Calmar/Sharpe 选）：Gate/OKX、真实与压力费率
        # 24 组全部 ≥ 固定关闭、回撤低 0.5–5 个百分点，但收益主要来自 2026-03 之前，n42 固定参数整段明显差于关闭（参数敏感），
        # 未达到改默认的标准（output/research_choppiness_entry_gate_monthly_walkforward.csv）。0=关闭；建议试用 chop_n 56 / chop_max 50
        "chop_n": 0,
        "chop_max": 50.0,
        # 2026-11-12：可选 Elder-Ray 空头入场闸门（默认关闭，只拦新开 / 反手空单）。现货 4h：E = EMA_N(close)，bull = (high − E) / WilderATR14；
        # 上一根 bull < −X（整根 K 线低于 EMA 超过 X 个 ATR，空头过度延伸）时不新开空，已有持仓 / 止损 / 离场 / 调仓不变。
        # 研究（scratch/eray_*.py，docs/STRATEGY_FORMULAS.md）：N26 X0 Gate +196.6% / OKX +193.3%（基线约 +156% / +159%），
        # 2026-03 后 +59.6…+60.5% vs +57.3%，10 个时移安慰剂 2026-03 后都更差；3/6 个月 walk-forward 胜基线、12 个月略低，未改默认。
        # 0=关闭；建议试用 elder_short_gate_n 26–50 / elder_short_gate_x 0–0.5
        "elder_short_gate_n": 0,
        "elder_short_gate_x": 0.0,
        # 2026-11-12：可选止损反手（stop-and-reverse，默认关闭，仅回测生效）。第 i 根 ATR 止损后第 i+1 根开盘开反向仓：
        # 风险 / 权重上限 × sar_risk_mult，止损 sar_atr_mult × ATR，持有 sar_hold_bars 根（或自身止损）；信号转向反手方向则转为正常持仓。
        # 研究（scratch/sar_*.py）：H12 k1 m2 Gate +234% / OKX +232%（基线约 +162% / +165%），Sharpe 2.02 vs 1.69，回撤 −15.7% vs −18.8%，
        # 胜过全部随机方向安慰剂；但 2026-03 后逐月只 Gate 6/8、OKX 3/8 更好，12 个月 walk-forward 低约 3.5 个百分点，未改默认。0=关闭
        "sar_hold_bars": 0,
        "sar_risk_mult": 1.0,
        "sar_atr_mult": 2.0,
        # 2026-11-13：可选动态多空风险平价 up（默认关闭；回测与模拟盘 / 实盘定仓同口径，engine.apply_ls_parity）。上一根合成信号下，较小一侧信号书（Σ 单币波动乘数）的
        # 单笔风险 / 单币权重上限放大到与较大一侧相同，最多 ls_parity_cap 倍；总敞口上限不变。研究（scratch/drp2/*.py）：多空永续 10× 下
        # C3 Gate +228.7% / OKX +235.8%（基线 +163.3% / +165.4%），Sharpe 2.01 / 2.04，回撤 −16.0%，2026-03 后两所 6/9 月更好；
        # C 越大越好、无内部最优，超额集中在 2025-10，未改默认。0=关闭，建议试用 2–3
        "ls_parity_cap": 0.0,
        # 2026-11-13：可选多空对冲对乘数（默认关闭；回测与模拟盘 / 实盘定仓同口径，engine.apply_hedge_pair）。上一根收盘若另一币持反向信号、
        # 且两币最近 hedge_pair_w 根永续对数收益相关 ≥ hedge_pair_c，则该币单笔风险 / 单币权重乘数 × hedge_pair_h（总敞口上限不变）。
        # 研究（scratch/hpn、scratch/hpph）：单独使用 12 个月 walk-forward 两所都输、相位检验 Sharpe 0–1/4，不建议单独用；
        # 叠加 ls_parity_cap 3 + 单笔风险 3% + 组合波动 50%（策略页 #9）时 4 个 4h 相位收益与 2026-03 后都更高。0=关闭，建议 W180 c0.5 h1.5
        "hedge_pair_w": 0,
        "hedge_pair_c": 0.5,
        "hedge_pair_h": 1.5,
        # 2026-11-14：可选同侧拥挤上限 CROWD（默认关闭；回测与模拟盘 / 实盘定仓同口径，engine.apply_side_crowd）。上一根合成信号中某侧有 n 个币时，
        # 该侧单币风险 / 权重乘数 × side_crowd_mult·min(1, side_crowd_cap/n)（总敞口上限不变）。研究（scratch/deep/run_crowd.py、oou_crowd.py）：
        # 深历史留出 3 组、未调参 8 币、20 组随机 8 币、压力费、时移安慰剂都更好（C5 m1.25），但默认 8 币全期收益略低、2026-03 后逐月 4/8 → 强观察，非默认。
        # 0=关闭，建议 C5 m1.25
        "side_crowd_cap": 0.0,
        "side_crowd_mult": 1.25,
        # 2026-11-13：可选 ES NORM 尾部厚度单币乘子（默认关闭；回测与模拟盘 / 实盘定仓同口径，engine.apply_es_tail）。每币按其交易市场最近
        # name_es_w 根 4h 对数收益的 ES/σ 相对正态的厚度 F（多看左尾、空看右尾），乘子 clip(F^−k, 0.5, 1.5) 后在有信号的币间归一。
        # 研究（scratch/dsz）：深历史留出 3 组 + 未调参 8 币 + 20 组随机 16 选 8 都更好、安慰剂更差，但 2026-03 后约持平 → 强观察，非默认。0=关闭，建议 W120 k2
        "name_es_w": 0,
        "name_es_k": 2.0,
        "name_es_alpha": 0.05,
        # 2026-11-13：可选跨根分批入场（默认关闭，仅回测生效）。新确认入场在第 i 根开盘只开计划名义的 f1，第 i+1 根开盘补满到计划名义，
        # 止损保持首笔；反手仓不分批。研究（scratch/xse_*.py、scratch/phc4–6）：多空永续 10× 下 f1 0.10–0.35 在 4 个 4h 相位 × 两所 × 真实 / 压力费率
        # 全部不输（f1 0.10 平均 +4.8 点，Sharpe +0.06），固定 f1 0.10 月度样本外 32/32 胜；但 2026-03 后逐月只约 5/8 更好，未改默认。
        # 「仅推迟入场一根」对照被否定（2026-03 后 8/8 落后）。0=关闭，建议试用 0.10–0.25
        "staged_entry_f1": 0.0,
        # 2026-11-21：可选 OKX 官方 USDT 借贷利率体制闸门（默认关闭；回测与模拟盘 / 实盘同一函数 qtw/lending.block_mask）。
        # r = 时间戳 ≤ 信号 K 线开盘时间的最近一条 OKX 小时 lendingRate（finance/savings/lending-rate-history?ccy=USDT），
        # z = (r − W 天均值) / W 天标准差；z > q 时不新开多（已持多不动，空单不受影响）。数据过旧（> stale_hours）/ 取不到 → 不拦（失败开放）。
        # 研究（scratch/lend/run.py、output/research_usdt_lending_rate_regime_4h.csv）：W30 q1.0 深历史 / 调参前段三组都更好，
        # 但 2026-03 后三组都更差（逐月 0–2/9）→ 弱观察，只做纸面前向检验（8793 paper-lendgate）。环境变量 QTW_LENDING_GATE=1 强制开启。
        "lending_gate_enabled": False,
        "lending_gate_window_days": 30,
        "lending_gate_z": 1.0,
        "lending_gate_side": "long",
        "lending_gate_stale_hours": 6.0,
        # 2026-11-21：可选美联储 H.4.1 外国官方托管美债闸门（默认关闭；回测与模拟盘 / 实盘同一函数 qtw/custody.block_mask）。
        # FRED WMTSECL1（周三水平，可用 = 周三 + 3 天 00:00 UTC）；z = h 周对数变化相对最近 N 周的 z；z < −k（外国官方抛售）时不新开多。
        # 研究（scratch/fedcustody4h/run.py、output/research_fed_custody_gate_4h.csv、docs/fed_custody_gate_4h.md）：预注册先验 N52 h4 k1
        # 深历史未见 / 调参前段三组都更好、未调参 new8 两所更好，但 2026-03 后从未拦到新多（post 无信息）→ 强观察，只做纸面前向检验
        # （8794 paper-custody）。环境变量 QTW_CUSTODY_GATE=1 强制开启。
        "custody_gate_enabled": False,
        "custody_gate_series": "tsy",
        "custody_gate_n": 52,
        "custody_gate_h": 4,
        "custody_gate_k": 1.0,
        "custody_gate_stale_days": 21.0,
        # 2026-11-22：可选加密股相对强弱闸门（默认关闭；回测与模拟盘 / 实盘同一函数 qtw/cryptoeq.block_mask）。
        # rs = ln(Nasdaq 官方 MSTR 日收盘 / BTCUSDT 现货当日 20:00 UTC 收盘)，chg = rs − n 个交易日前；chg ≤ 0（美股资金减配加密）时不新开多。
        # 可用 = 交易日 + 1 天 00:00 UTC。研究（scratch/cryptoeq4h/run.py、output/research_crypto_equity_relstrength_gate_4h.csv、
        # docs/crypto_equity_relstrength_gate_4h.md）：预注册先验 MSTR n20 long_off 9/9（深未见 / 调参三组都更好、n10/15 邻域同为 9/9、
        # 安慰剂 ≤ 2/9），但 2026-03 后几乎不拦（逐月 2/1）→ 强观察，只做纸面前向检验（8795 paper-cryptoeq）。环境变量 QTW_CRYPTOEQ_GATE=1 强制开启。
        "cryptoeq_gate_enabled": False,
        "cryptoeq_gate_symbol": "MSTR",
        "cryptoeq_gate_n": 20,
        "cryptoeq_gate_stale_days": 7.0,
        # 2026-11-22：可选美元广义指数做空闸门（默认关闭；回测与模拟盘 / 实盘同一函数 qtw/usd_gate.block_mask）。
        # FRED DTWEXBGS（美联储 H.10 广义美元指数，观测日 + 10 天 00:00 UTC 才算已知）；最新已知值 ≤ 最近 n 个观测均值（美元走弱）时不新开空。
        # 研究（scratch/macro/run.py、output/research_us_macro_risk_regime_gate_4h.csv、docs/STRATEGY_FORMULAS.md 2026-11-14 宏观节）：
        # N20 short_on 8/9，2026-03 后 OKX d8 +72.6% vs +59.9%、Gate +73.3% vs +60.3%（逐月 5/3），但 d7 深历史输、对发布滞后敏感
        # → 观察，只做纸面前向检验（8796 paper-usdgate）。环境变量 QTW_USD_GATE=1 强制开启。
        "usd_gate_enabled": False,
        "usd_gate_n": 20,
        "usd_gate_lag_days": 10,
        "usd_gate_stale_days": 14.0,
        # 2026-11-22：可选日本财务省周度居民外债净买闸门（默认关闭；回测与模拟盘 / 实盘同一函数 qtw/mof_gate.block_mask）。
        # MoF「对外及对内证券买卖（周度）」居民中长期外债净买，13 周和 > 其 26 周均值（外流加速 = risk-on）时不新开空，否则不新开多；
        # 周末 + 6 天 00:00 UTC 才算已知。研究（scratch/mofsec4h/run.py、output/research_mof_resident_foreign_bond_flow_gate_4h.csv、
        # docs/mof_resident_foreign_bond_flow_gate_4h.md）：预注册先验 b13_trend26_contra_both 9/9，2026-03 后 OKX d8 +70.7% vs +59.9%、
        # Gate +71.2% vs +60.3%，但逐月只 4/3、5/2（< 6/9）、邻域深未见不稳 → 强观察，只做纸面前向检验（8798 paper-mofgate）。
        # 环境变量 QTW_MOF_GATE=1 强制开启。
        "mof_gate_enabled": False,
        "mof_gate_sum_n": 13,
        "mof_gate_trend_n": 26,
        "mof_gate_stale_days": 21.0,
        # 2026-11-27：可选美联储 H.15 商业票据融资利差闸门（默认关闭；回测与模拟盘 / 实盘同一函数 qtw/cp_gate.block_mask）。
        # FRED DCPF3M − DTB3（3M AA 金融类 CP − 3M 国库券）5 个观测均值 > 其 60 个观测均线（短端美元融资压力上升）时不新开多；
        # 下一个工作日 + 1 天 00:00 UTC 才算已知。研究（scratch/cpspread4h/run.py、output/research_fed_h15_cp_spread_gate_4h.csv、
        # docs/fed_h15_cp_spread_gate_4h.md）：预注册回退格 FIN3_trend_n60_long_off 深未见 Sharpe OKX 1.46 / Gate 0.56（基线 0.71 / 0.09）、
        # 安慰剂 0/17 超过；2026-03 后与基线逐位相同（post 窗内无多单被拦，逐月 0 胜 0 负）→ 强观察（非默认），只做纸面前向检验（8800 paper-cpgate）。
        # 环境变量 QTW_CP_GATE=1 强制开启。
        "cp_gate_enabled": False,
        "cp_gate_n": 60,
        "cp_gate_smooth": 5,
        "cp_gate_stale_days": 10.0,
        # 2026-11-27：可选美联储贴现窗口一级信贷（H.4.1 WLCFLPCL 周三水平）闸门（默认关闭；回测与模拟盘 / 实盘同一函数 qtw/backstop_gate.block_mask）。
        # 一级信贷 > 其 13 周均线（银行融资压力上升）时不新开多，否则不新开空（both）；周三 + 3 天 00:00 UTC 才算已知。研究（scratch/fedswap4h/run.py、
        # output/research_fed_backstop_lending_gate_4h.csv、docs/fed_backstop_lending_gate_4h.md）：pcr_trend_n13_both 6/9，2026-03 后 OKX d8 +66.7% vs +59.9%、
        # Gate +67.4% vs +60.3%，逐月 5/2、6/1，安慰剂全部更差，但 2024-10→2026-03 段大幅落后 → 弱观察，只做纸面前向检验（8799 paper-backstop）。
        # 环境变量 QTW_BACKSTOP_GATE=1 强制开启。
        "backstop_gate_enabled": False,
        "backstop_gate_trend_n": 13,
        "backstop_gate_stale_days": 21.0,
        # 2026-11-27：可选 Gate 官方 BTC 3 倍杠杆代币多空成交额比闸门（默认关闭；回测与模拟盘 / 实盘同一函数 qtw/levtok_gate.block_mask）。
        # x = ln(7 日 BTC3L 成交额 / 7 日 BTC3S 成交额)（Gate v4 官方 1d K 线，日 D 自 D+1 04:00 UTC 起已知）；x > 其 90 日均线
        # （散户杠杆偏多上升）时不新开空，否则不新开多（contra_both，确认式）。研究（scratch/levtok4h/run.py、
        # output/research_gate_leveraged_token_flow_gate_4h.csv、docs/gate_leveraged_token_flow_gate_4h.md）：反向先验 ls7_trend_n30_long_off 0/9 否决；
        # 非先验 lsbtc7_trend_n90_contra_both 9/9，2026-03 后 OKX d8 +64.8% vs +59.9%、Gate +65.2% vs +60.3%，深未见三组大幅更好、压力费保持、
        # new8 pre 两所更好、n45–180 邻域 post Sharpe 全高于基线、8 个平移安慰剂 post 全更差，但逐月只 4/5、4/4（< 6/9）→ 观察，
        # 只做纸面前向检验（8802 paper-levtok）。环境变量 QTW_LEVTOK_GATE=1 强制开启。
        "levtok_gate_enabled": False,
        "levtok_gate_sum_n": 7,
        "levtok_gate_trend_n": 90,
        "levtok_gate_stale_days": 3.0,
        # 2026-11-10：可选浮盈加仓（默认关闭）。前一根收盘浮盈 ≥ pyramid_r × R 时加仓一次，规模 pyramid_frac × 原名义，止损不动。
        # 12 组邻域整段全优于基线，但前推后 6 段只高约 0.5 个百分点，未达到改默认的标准。0=关闭（仅回测生效）
        "pyramid_r": 0.0,
        "pyramid_frac": 0.5,
        # 2026-11-10：可选固定止盈（默认关闭）。目标价 = 入场价 ± tp_r × R（R = 初始止损距离 = atr_stop_mult × ATR），触及全部平仓。
        # tp_reentry = False：止盈后像止损一样锁定，信号改变前不再开同向仓；True：下一根若信号仍在则按新 ATR 重新开仓。0=关闭
        "tp_r": 0.0,
        "tp_reentry": False,
        # 2026-11-13：可选分批止盈 + 保本止损（默认关闭）。浮盈触及 入场价 ± tp_partial_r × R0（R0 = 入场价到初始止损的距离，
        # 即 atr_stop_mult × ATR）时按吃单平掉 tp_frac 比例（原因「止盈」）；tp_breakeven = True 时剩余仓位止损移到保本价
        # （入场价，tp_be_fees = True 时再加两条腿 taker 手续费），之后触及记「保本止损」。已部分止盈的持仓不再参与调仓带。
        # 回测 / 模拟盘周期 / 实时止损轮询同一公式（engine.partial_tp_price / breakeven_price）。
        "tp_partial": False,
        "tp_partial_r": 2.0,
        "tp_frac": 0.5,
        "tp_breakeven": False,
        "tp_be_fees": True,
        # 2026-11-13：可选快速层离场（默认关闭）：用官方 1m/5m（10m 由 1m/5m 聚合）或 1D K 线判断 4h 持仓的趋势是否已破。
        # fast_exit_tf = off | 5m | 10m | 1d；该周期收盘价相对 EMA(fast_exit_n) 逆持仓方向（多：收盘 < EMA；空：收盘 > EMA）
        # 连续 fast_exit_confirm 根已收盘 K 线即平仓（原因「快速离场」），并像止损一样锁定到 4h 信号改变。
        "fast_exit_tf": "off",
        "fast_exit_n": 50,
        "fast_exit_confirm": 2,
        # 2026-11-11：持仓调仓（每根新收盘 K 线一次）。目标名义 = min(权益×单笔风险/现有止损距离%, 权益×单币权重)，
        # 再按总敞口等比缩放；|当前−目标|/目标 > rebalance_band 才调，先减后加，止损不变（见 qtw/rebalance.py）。
        # 真实费率（现货 10 / 永续 5.1 bps）：前 6 段选出 0.1，后 6 段（未参与选择）OKX +33.6% vs 基线 +29.4%，
        # Gate +33.2% vs +29.3%；费率 ×2 仍更好；0.1/0.25/0.5 三档全优（平台而非尖峰）。0 = 关闭
        "rebalance_band": 0.1,
        # 2026-11-12 19:55：可选「减仓专用阈值」（非对称调仓带）。0 = 与 rebalance_band 相同（默认，行为不变）；
        # >0 时：当前名义高于目标（减仓）需偏离 > rebalance_band_down，加仓仍用 rebalance_band。研究建议 0.3–0.35
        #（4500 根 4h：0.3 时 Gate +163% / OKX +169% 对基线 +156% / +159%，2026-03 后 +4 点；OKX walk-forward 全胜，Gate 3 个月训练略输，暂不设为默认，详见 docs/STRATEGY_FORMULAS.md）
        "rebalance_band_down": 0.0,
        # 2026-11-10 13:05 改为默认 30%/180，并已接入模拟/实盘引擎（qtw/engine.vol_scaled_cfg：账本按 4h 分桶的收盘权益，
        # 不足 181 根即约 30 天时 k=1 不缩放）。严格月度 walk-forward（候选 0/25/30/35%，训练 3/6/12 月 × Calmar/夏普，两所 × 真实/压力费率
        # 共 24 组）：月度切换不优于固定选择；固定 30% 相对 0% 在全部 24 组样本外窗口回撤都更小（约 −2~−5 点）、夏普都更高，收益真实费率 −9~+4 点、压力费率 −16~−2 点（用收益换回撤）
        # （output/research_port_vol_target_monthly_walkforward.csv）。原 13:00 结论：组合波动率目标。最近 port_vol_lookback 根 4h 权益收益的年化波动 σ，
        # 单笔风险与单币权重上限 × min(1, 目标/σ)。Gate / OKX 4500 根长历史、新基线：目标 25–40% × 回看 90/180/360 共 12 组最大回撤全部
        # 从 −28.3% 降到 −20%~−26%、日夏普 1.25→1.3–1.5；30%/180：Gate 调参前 +42.2%→+54.7%、之后 +56.7%→+55.4%，回撤 −23.5%。
        # （output/research_long_history_drawdown_equity_vol_throttle.csv、research_long_history_port_vol_target_robustness.csv）0=关闭
        "port_vol_target": 0.30,
        "port_vol_lookback": 180,
        # 2026-11-10 14:10 新默认：单币波动率封顶。σ_s = 最近 name_vol_lookback 根 4h 对数收益年化标准差（多头用现货、空头用永续），
        # 单笔风险与单币权重上限再 × min(1, name_vol_target/σ_s)（叠加在组合波动率系数之上，只缩不放）。默认风险 5% 在 2×ATR 下几乎总被
        # 单币 20% 截住，原本接近等名义；封顶只压极高波动的币。Gate / OKX 4500 根：abs 0.6–0.7 × L 60–360 是平台，回撤 −23.5%→−19~−21%，
        # 夏普 1.47→1.55–1.68；严格月度 walk-forward（候选 关闭 / 0.6 / 0.7 × L120 / 180，训练 3/6/12 月 × Calmar/夏普，两所 × 真实/压力费率
        # 共 24 组）：固定 0.6/120 相对关闭在全部 12 个样本外窗口回撤都更小、夏普都更高，收益 11/12 更高，2026-03 后段也略高
        # （output/research_inverse_vol_sizing.csv、_abs_nbhd.csv、_monthly_walkforward.csv）。0 = 关闭
        "name_vol_target": 0.60,
        "name_vol_lookback": 120,
        "rebalance_mode": "stop",  # stop：按现有止损距离定目标；atr：再取与最新 ATR 止损距离的较大者（更保守）
        "lookback_bars": 200,
        # 2026-11-20 kean t88u：运行时自适应（qtw/adaptive.py）。默认开关依据 docs/STRATEGY_FORMULAS.md「运行时自适应」：
        # 只有在未见历史（deep / tune）跑赢同脚本基线、且 2026-03 后 OKX 与 Gate 都至少 6/9 个月更好时才默认开。
        # 趋势强度仓位乘子：off | spread（|SMA快−SMA慢|/ATR 相对 1000 根中位）| adx（ADX14/25），夹在 [lo, hi]，乘积不破 5% / 20% 上限
        "adaptive_size_mode": "off",
        "adaptive_size_lo": 0.5,
        "adaptive_size_hi": 1.0,
        # 体制方向偏置：BTC 收盘 > SMA_btc_regime_ma × (1 + band) 时只做多（拦新开空）；低于 SMA 时只做空（原 BTC 体制过滤）
        "direction_bias": False,
        "direction_bias_band": 0.1,
        # 滚动自动调参：每 N 天用过去 L 天数据在小网格（快 30/50/70 × 慢 100/150/200 × ATR 1.5/2/2.5 × 体制 900/1200/1500）
        # 里按 Sharpe 重选，挑战者需高出 margin 才切换；结果写 SQLite（adaptive_params），热加载生效，不改已保存的设置
        "auto_retune": False,
        "retune_every_days": 30,
        "retune_lookback_days": 365,
        "retune_margin": 0.3,
        # 热加载（基础设施，默认开）：运行中改策略参数 / 改 qtw/strategy.py、qtw/adaptive.py 后 ≤ 5 秒生效，不用重启；持仓不受影响
        "hot_reload": True,
    },
    "risk": {
        "starting_equity_usdt": 1000.0,
        "max_risk_per_trade": 0.05,
        "max_weight_per_name": 0.20,
        "max_gross_exposure": 1.0,  # 总敞口 ≤ 1 倍权益
        # 2026-11-13 t69u：多空都用 USDT 永续（perp_both，默认）；保留「现货做多 + 永续做空」（spot_perp）。
        # 杠杆默认 10 倍、可设 1–100 倍（还受交易所该币上限约束），逐仓：保证金 = 名义 / 杠杆。
        # 默认「杠杆不放大风险」：名义仍按单笔风险 / 单币权重 / 总敞口定，10 倍只是少占保证金；
        # 每仓实际杠杆 = min(设置, 交易所上限, 止损先于强平的安全上限)，见 qtw/leverage.py、qtw/margin.py。
        "trade_mode": "perp_both",
        "perp_leverage": 10,
        # 可选（默认关）：杠杆放大敞口 —— 单笔风险、单币权重、总敞口都 × 杠杆。历史回测在 ≥3 倍时回撤 / 爆仓风险急剧上升，仅供观察
        "leverage_scales_exposure": False,
        "allow_spot_long": True,
        "allow_perp_short": True,
    },
    # 手续费（bps，1 bp = 0.01%）。2026-11-10 按 kean 实际账户费率：现货 maker 0.08% / taker 0.10%，
    # 永续 maker 0.02% / taker 0.051%。策略在下一根开盘以市价成交，按 taker 计费、每条市价腿各收一次。
    # taker_bps 为旧版单一费率字段（仅在缺少分市场费率时回退使用）。
    "fees": {"spot_taker_bps": 10.0, "spot_maker_bps": 8.0, "perp_taker_bps": 5.1, "perp_maker_bps": 2.0, "taker_bps": 4.0},
    # 7×24 纸面自动交易（服务运行即运行；紧急停止会关闭）。决策由实时 WS 事件驱动（qtw/realtime.py）：
    # interval_sec 只是旧字段，不再用于定时轮询。deselect_policy：开始交易时取消勾选、但仍有持仓的币
    # keep = 继续按止损 / 信号管理到离场（不再新开），flatten = 确认时按官方价立即平掉（纸面）。
    "worker": {"enabled": True, "interval_sec": 60, "deselect_policy": "keep"},
    # 短线层（1m / 5m / 10m / 1h，顺 4h / 1D 方向的独立进出场系统，独立风险预算）。
    # 2026-11-13 研究：两家交易所未见数据上扣费后期望均为负 → 未通过验证，不能开启（见 docs/STRATEGY_FORMULAS.md「短线层」）。
    "short_layer": {"enabled": False, "base_tf": "5m", "budget_frac": 0.3},
    "live": {
        "mode": "paper",  # paper | live
        "live_enabled": False,
        "confirm_phrase": "",
        "okx_demo": True,  # OKX 模拟盘 (x-simulated-trading: 1)
        "gate_testnet": True,
    },
}

_LOCK = threading.RLock()
PATH = DATA_DIR / "settings.yaml"


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def _read_db() -> dict | None:
    r = db.query("SELECT value FROM settings WHERE key='config'")
    return json.loads(r[0]["value"]) if r else None


def _write_db(s: dict) -> None:
    db.execute("INSERT INTO settings(key,value,updated_at) VALUES('config',?,?) "
               "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
               (db.dumps(s), iso(utcnow())))


def load() -> dict:
    with _LOCK:
        ensure_dirs()
        data = _read_db()
        if data is None:
            data = {}
            if PATH.exists():  # 旧版 YAML → SQLite 一次性迁移
                data = yaml.safe_load(PATH.read_text(encoding="utf-8")) or {}
                _write_db(_merge(DEFAULTS, data))
                PATH.rename(PATH.with_suffix(".yaml.migrated"))
        rk = data.get("risk") if isinstance(data.get("risk"), dict) else None
        if rk is not None and "trade_mode" not in rk:
            # v1 存档：perp_leverage 被强制为 1（不是用户选择）。升级到 t69u 后改用新默认（多空永续、10 倍，仓位仍按风险）
            data = {**data, "risk": {k: v for k, v in rk.items() if k != "perp_leverage"}}
        out = _merge(DEFAULTS, data)
        if str(os.environ.get("QTW_LENDING_GATE", "")).strip().lower() in ("1", "true", "yes", "on"):
            out["strategy"]["lending_gate_enabled"] = True  # 纸面前向检验实例（paper-lendgate）用环境变量强制开启借贷利率闸门
        if str(os.environ.get("QTW_CUSTODY_GATE", "")).strip().lower() in ("1", "true", "yes", "on"):
            out["strategy"]["custody_gate_enabled"] = True  # 纸面前向检验实例（paper-custody）用环境变量强制开启 H.4.1 托管闸门
        if str(os.environ.get("QTW_CRYPTOEQ_GATE", "")).strip().lower() in ("1", "true", "yes", "on"):
            out["strategy"]["cryptoeq_gate_enabled"] = True  # 纸面前向检验实例（paper-cryptoeq）用环境变量强制开启加密股相对强弱闸门
        if str(os.environ.get("QTW_USD_GATE", "")).strip().lower() in ("1", "true", "yes", "on"):
            out["strategy"]["usd_gate_enabled"] = True  # 纸面前向检验实例（paper-usdgate）用环境变量强制开启美元广义指数做空闸门
        if str(os.environ.get("QTW_MOF_GATE", "")).strip().lower() in ("1", "true", "yes", "on"):
            out["strategy"]["mof_gate_enabled"] = True  # 纸面前向检验实例（paper-mofgate）用环境变量强制开启 MoF 居民外债净买闸门
        if str(os.environ.get("QTW_CP_GATE", "")).strip().lower() in ("1", "true", "yes", "on"):
            out["strategy"]["cp_gate_enabled"] = True  # 纸面前向检验实例（paper-cpgate）用环境变量强制开启 H.15 商业票据融资利差闸门
        if str(os.environ.get("QTW_BACKSTOP_GATE", "")).strip().lower() in ("1", "true", "yes", "on"):
            out["strategy"]["backstop_gate_enabled"] = True  # 纸面前向检验实例（paper-backstop）用环境变量强制开启一级信贷闸门
        if str(os.environ.get("QTW_LEVTOK_GATE", "")).strip().lower() in ("1", "true", "yes", "on"):
            out["strategy"]["levtok_gate_enabled"] = True  # 纸面前向检验实例（paper-levtok）用环境变量强制开启杠杆代币多空比闸门
        out["strategy"]["fast_exit_tf"] = "off"  # 已存的旧值（5m / 10m / 1d）也不生效，见 validate() 注释
        for k in ("live_enabled", "okx_demo", "gate_testnet"):  # 旧存档里的字符串 "false" 不能被当成 True（实盘闸门 / 模拟盘开关）
            out["live"][k] = _as_bool(out["live"].get(k, DEFAULTS["live"][k]))
        return out


def taker_rate(cfg: dict, market: str) -> float:
    """某市场（spot / perp）的 taker 费率（小数）。缺少分市场字段时回退到旧版 taker_bps。"""
    fees = cfg.get("fees") or {}
    v = fees.get(f"{market}_taker_bps")
    if v is None:
        v = fees.get("taker_bps", 0.0)
    return float(v) / 10_000


def _as_bool(v) -> bool:
    """严格布尔：只有 True / 非零数 / "true" "1" "yes" "on"（不分大小写）为真；"false" "0" "" 等为假。"""
    if isinstance(v, str):
        return v.strip().lower() in ("true", "1", "yes", "on")
    return bool(v)


def validate(s: dict) -> dict:
    st, rk = s["strategy"], s["risk"]
    for k in ("spot_taker_bps", "spot_maker_bps", "perp_taker_bps", "perp_maker_bps", "taker_bps"):
        if k in s["fees"]:
            s["fees"][k] = float(s["fees"][k])
            if not 0 <= s["fees"][k] <= 100:
                raise ValueError("手续费需在 0–100 bps 之间")
    if st["interval"] not in ("15m", "1h", "4h", "1d"):
        raise ValueError("K 线周期只支持 15m / 1h / 4h / 1d")
    st["fast_ma"], st["slow_ma"], st["atr_period"] = int(st["fast_ma"]), int(st["slow_ma"]), int(st["atr_period"])
    if not (2 <= st["fast_ma"] < st["slow_ma"] <= 400):
        raise ValueError("需要 2 ≤ 快线 < 慢线 ≤ 400")
    if not 2 <= st["atr_period"] <= 200:  # 0 / 1 会让 ATR 为空或退化成单根 TR，止损与按风险定仓失真
        raise ValueError("ATR 周期需在 2–200 之间")
    st["atr_stop_mult"] = float(st["atr_stop_mult"])
    if not 0.5 <= st["atr_stop_mult"] <= 10:
        raise ValueError("ATR 止损倍数需在 0.5–10 之间")
    st["confirm_bars"] = int(st.get("confirm_bars", 1))
    if not 1 <= st["confirm_bars"] <= 5:
        raise ValueError("信号确认根数需在 1–5 之间")
    st["trend_ma"] = int(st.get("trend_ma", 0) or 0)
    if st["trend_ma"] and not 20 <= st["trend_ma"] <= 400:
        raise ValueError("趋势过滤 SMA 需为 0（关闭）或 20–400")
    st["short_breaker_bars"] = int(st.get("short_breaker_bars", 0) or 0)
    if st["short_breaker_bars"] and not 10 <= st["short_breaker_bars"] <= 500:
        raise ValueError("空头熔断回看根数需为 0（关闭）或 10–500")
    st["btc_regime_ma"] = int(st.get("btc_regime_ma", 0) or 0)
    if st["btc_regime_ma"] and not 50 <= st["btc_regime_ma"] <= 2000:
        raise ValueError("BTC 熊市过滤 SMA 需为 0（关闭）或 50–2000")
    st["btc_regime_vote_k"] = int(st.get("btc_regime_vote_k", 0) or 0)
    if not 0 <= st["btc_regime_vote_k"] <= 5:
        raise ValueError("BTC 体制线投票门槛需为 0（单线）或 1–5")
    if st["btc_regime_vote_k"] and st["btc_regime_ma"] and round(st["btc_regime_ma"] * 1.5) > 2000:
        raise ValueError("BTC 体制线投票最长一条为 1.5×N，需 ≤ 2000 根（N ≤ 1333）")
    st["btc_regime_symbol"] = str(st.get("btc_regime_symbol") or "BTCUSDT").upper()
    if st["btc_regime_symbol"] not in REGIME_SYMBOLS:
        raise ValueError("体制线来源币种需为 " + " / ".join(REGIME_SYMBOLS))
    st["chop_n"] = int(st.get("chop_n", 0) or 0)
    if st["chop_n"] and not 5 <= st["chop_n"] <= 300:
        raise ValueError("震荡指数周期需为 0（关闭）或 5–300")
    st["chop_max"] = float(st.get("chop_max", 50) or 50)
    if not 20 <= st["chop_max"] <= 100:
        raise ValueError("震荡指数阈值需在 20–100 之间")
    st["elder_short_gate_n"] = int(st.get("elder_short_gate_n", 0) or 0)
    if st["elder_short_gate_n"] and not 5 <= st["elder_short_gate_n"] <= 300:
        raise ValueError("Elder-Ray 空头闸门 EMA 周期需为 0（关闭）或 5–300")
    st["elder_short_gate_x"] = float(st.get("elder_short_gate_x", 0) or 0)
    if not 0 <= st["elder_short_gate_x"] <= 5:
        raise ValueError("Elder-Ray 空头闸门 ATR 倍数需在 0–5 之间")
    st["sar_hold_bars"] = int(st.get("sar_hold_bars", 0) or 0)
    if not 0 <= st["sar_hold_bars"] <= 100:
        raise ValueError("止损反手持有根数需为 0（关闭）或 1–100")
    st["sar_risk_mult"] = float(st.get("sar_risk_mult", 1.0) or 0)
    if not 0.1 <= st["sar_risk_mult"] <= 3:
        raise ValueError("止损反手风险倍数需在 0.1–3 之间")
    st["sar_atr_mult"] = float(st.get("sar_atr_mult", 2.0) or 0)
    if not 0.5 <= st["sar_atr_mult"] <= 10:
        raise ValueError("止损反手 ATR 止损倍数需在 0.5–10 之间")
    st["ls_parity_cap"] = float(st.get("ls_parity_cap", 0) or 0)
    if st["ls_parity_cap"] and not 1 <= st["ls_parity_cap"] <= 10:
        raise ValueError("多空风险平价放大上限需为 0（关闭）或 1–10")
    st["hedge_pair_w"] = int(st.get("hedge_pair_w", 0) or 0)
    if st["hedge_pair_w"] and not 20 <= st["hedge_pair_w"] <= 1000:
        raise ValueError("对冲对相关窗口需为 0（关闭）或 20–1000 根")
    st["hedge_pair_c"] = float(st.get("hedge_pair_c", 0.5) if st.get("hedge_pair_c") is not None else 0.5)
    if not -1 <= st["hedge_pair_c"] <= 1:
        raise ValueError("对冲对相关阈值需在 −1 到 1 之间")
    st["hedge_pair_h"] = float(st.get("hedge_pair_h", 1.5) if st.get("hedge_pair_h") is not None else 1.5)
    if not 0.25 <= st["hedge_pair_h"] <= 3:
        raise ValueError("对冲对乘数需在 0.25–3 之间")
    st["side_crowd_cap"] = float(st.get("side_crowd_cap", 0) or 0)
    if st["side_crowd_cap"] and not 1 <= st["side_crowd_cap"] <= 50:
        raise ValueError("同侧拥挤上限 C 需为 0（关闭）或 1–50 个币")
    st["side_crowd_mult"] = float(st.get("side_crowd_mult", 1.25) if st.get("side_crowd_mult") is not None else 1.25)
    if not 0.25 <= st["side_crowd_mult"] <= 3:
        raise ValueError("同侧拥挤乘数 m 需在 0.25–3 之间")
    st["name_es_w"] = int(st.get("name_es_w", 0) or 0)
    if st["name_es_w"] and not 20 <= st["name_es_w"] <= 1000:
        raise ValueError("ES 尾部厚度窗口需为 0（关闭）或 20–1000 根")
    st["name_es_k"] = float(st.get("name_es_k", 2.0) if st.get("name_es_k") is not None else 2.0)
    if not 0.25 <= st["name_es_k"] <= 5:
        raise ValueError("ES 尾部厚度指数 k 需在 0.25–5 之间")
    st["name_es_alpha"] = float(st.get("name_es_alpha", 0.05) if st.get("name_es_alpha") is not None else 0.05)
    if not 0.01 <= st["name_es_alpha"] <= 0.25:
        raise ValueError("ES 尾部分位 α 需在 0.01–0.25 之间")
    st["lending_gate_enabled"] = _as_bool(st.get("lending_gate_enabled", False))
    st["lending_gate_window_days"] = int(st.get("lending_gate_window_days", 30) or 30)
    if not 7 <= st["lending_gate_window_days"] <= 180:
        raise ValueError("借贷利率闸门窗口需在 7–180 天之间")
    st["lending_gate_z"] = float(st.get("lending_gate_z", 1.0) if st.get("lending_gate_z") is not None else 1.0)
    if not 0.25 <= st["lending_gate_z"] <= 5:
        raise ValueError("借贷利率闸门阈值 q 需在 0.25–5 之间")
    st["lending_gate_side"] = str(st.get("lending_gate_side") or "long").lower()
    if st["lending_gate_side"] != "long":
        raise ValueError("借贷利率闸门目前只支持 long（拦新开多）")
    st["lending_gate_stale_hours"] = float(st.get("lending_gate_stale_hours", 6.0) or 6.0)
    if not 1 <= st["lending_gate_stale_hours"] <= 72:
        raise ValueError("借贷利率过期阈值需在 1–72 小时之间")
    st["custody_gate_enabled"] = _as_bool(st.get("custody_gate_enabled", False))
    st["custody_gate_series"] = str(st.get("custody_gate_series") or "tsy").lower()
    if st["custody_gate_series"] not in ("tsy", "tot"):
        raise ValueError("托管闸门序列只支持 tsy（可交易美债）或 tot（托管合计）")
    st["custody_gate_n"] = int(st.get("custody_gate_n", 52) or 52)
    if not 13 <= st["custody_gate_n"] <= 260:
        raise ValueError("托管闸门 z 窗口 N 需在 13–260 周之间")
    st["custody_gate_h"] = int(st.get("custody_gate_h", 4) or 4)
    if not 1 <= st["custody_gate_h"] <= 13:
        raise ValueError("托管闸门变化周数 h 需在 1–13 之间")
    st["custody_gate_k"] = float(st.get("custody_gate_k", 1.0) if st.get("custody_gate_k") is not None else 1.0)
    if not 0.25 <= st["custody_gate_k"] <= 5:
        raise ValueError("托管闸门阈值 k 需在 0.25–5 之间")
    st["custody_gate_stale_days"] = float(st.get("custody_gate_stale_days", 21.0) or 21.0)
    if not 7 <= st["custody_gate_stale_days"] <= 60:
        raise ValueError("托管数据过期阈值需在 7–60 天之间")
    st["cryptoeq_gate_enabled"] = _as_bool(st.get("cryptoeq_gate_enabled", False))
    st["cryptoeq_gate_symbol"] = str(st.get("cryptoeq_gate_symbol") or "MSTR").upper()
    if st["cryptoeq_gate_symbol"] not in ("MSTR", "COIN"):
        raise ValueError("加密股闸门标的只支持 MSTR 或 COIN")
    st["cryptoeq_gate_n"] = int(st.get("cryptoeq_gate_n", 20) or 20)
    if not 5 <= st["cryptoeq_gate_n"] <= 120:
        raise ValueError("加密股闸门回看交易日 n 需在 5–120 之间")
    st["cryptoeq_gate_stale_days"] = float(st.get("cryptoeq_gate_stale_days", 7.0) or 7.0)
    if not 4 <= st["cryptoeq_gate_stale_days"] <= 30:
        raise ValueError("加密股数据过期阈值需在 4–30 天之间")
    st["usd_gate_enabled"] = _as_bool(st.get("usd_gate_enabled", False))
    st["usd_gate_n"] = int(st.get("usd_gate_n", 20) or 20)
    if not 5 <= st["usd_gate_n"] <= 200:
        raise ValueError("美元闸门均线观测数 n 需在 5–200 之间")
    st["usd_gate_lag_days"] = int(st.get("usd_gate_lag_days", 10) or 10)
    if not 3 <= st["usd_gate_lag_days"] <= 30:
        raise ValueError("美元闸门发布滞后需在 3–30 天之间")
    st["usd_gate_stale_days"] = float(st.get("usd_gate_stale_days", 14.0) or 14.0)
    if not 5 <= st["usd_gate_stale_days"] <= 60:
        raise ValueError("美元数据过期阈值需在 5–60 天之间")
    st["mof_gate_enabled"] = _as_bool(st.get("mof_gate_enabled", False))
    st["mof_gate_sum_n"] = int(st.get("mof_gate_sum_n", 13) or 13)
    if not 1 <= st["mof_gate_sum_n"] <= 52:
        raise ValueError("MoF 闸门求和周数需在 1–52 之间")
    st["mof_gate_trend_n"] = int(st.get("mof_gate_trend_n", 26) or 26)
    if not 2 <= st["mof_gate_trend_n"] <= 104:
        raise ValueError("MoF 闸门均线周数需在 2–104 之间")
    st["mof_gate_stale_days"] = float(st.get("mof_gate_stale_days", 21.0) or 21.0)
    if not 8 <= st["mof_gate_stale_days"] <= 60:
        raise ValueError("MoF 数据过期阈值需在 8–60 天之间")
    st["cp_gate_enabled"] = _as_bool(st.get("cp_gate_enabled", False))
    st["cp_gate_n"] = int(st.get("cp_gate_n", 60) or 60)
    if not 10 <= st["cp_gate_n"] <= 300:
        raise ValueError("CP 利差闸门均线观测数 n 需在 10–300 之间")
    st["cp_gate_smooth"] = int(st.get("cp_gate_smooth", 5) or 5)
    if not 1 <= st["cp_gate_smooth"] <= 20:
        raise ValueError("CP 利差闸门平滑观测数需在 1–20 之间")
    st["cp_gate_stale_days"] = float(st.get("cp_gate_stale_days", 10.0) or 10.0)
    if not 4 <= st["cp_gate_stale_days"] <= 60:
        raise ValueError("CP 利差数据过期阈值需在 4–60 天之间")
    st["backstop_gate_enabled"] = _as_bool(st.get("backstop_gate_enabled", False))
    st["backstop_gate_trend_n"] = int(st.get("backstop_gate_trend_n", 13) or 13)
    if not 2 <= st["backstop_gate_trend_n"] <= 104:
        raise ValueError("一级信贷闸门均线周数需在 2–104 之间")
    st["backstop_gate_stale_days"] = float(st.get("backstop_gate_stale_days", 21.0) or 21.0)
    if not 8 <= st["backstop_gate_stale_days"] <= 60:
        raise ValueError("一级信贷数据过期阈值需在 8–60 天之间")
    st["levtok_gate_enabled"] = _as_bool(st.get("levtok_gate_enabled", False))
    st["levtok_gate_sum_n"] = int(st.get("levtok_gate_sum_n", 7) or 7)
    if not 1 <= st["levtok_gate_sum_n"] <= 30:
        raise ValueError("杠杆代币闸门成交额求和天数需在 1–30 之间")
    st["levtok_gate_trend_n"] = int(st.get("levtok_gate_trend_n", 90) or 90)
    if not 5 <= st["levtok_gate_trend_n"] <= 365:
        raise ValueError("杠杆代币闸门均线天数需在 5–365 之间")
    st["levtok_gate_stale_days"] = float(st.get("levtok_gate_stale_days", 3.0) or 3.0)
    if not 2 <= st["levtok_gate_stale_days"] <= 14:
        raise ValueError("杠杆代币数据过期阈值需在 2–14 天之间")
    st["staged_entry_f1"] = float(st.get("staged_entry_f1", 0) or 0)
    if st["staged_entry_f1"] and not 0.05 <= st["staged_entry_f1"] <= 0.95:
        raise ValueError("分批入场首笔比例需为 0（关闭）或 0.05–0.95")
    st["pyramid_r"] = float(st.get("pyramid_r", 0) or 0)
    st["pyramid_frac"] = float(st.get("pyramid_frac", 0.5) or 0)
    if st["pyramid_r"] and not 0.5 <= st["pyramid_r"] <= 5:
        raise ValueError("浮盈加仓触发倍数需为 0（关闭）或 0.5–5 R")
    if not 0 <= st["pyramid_frac"] <= 1:
        raise ValueError("加仓比例需在 0–1 之间")
    st["tp_r"] = float(st.get("tp_r", 0) or 0)
    if st["tp_r"] and not 0.5 <= st["tp_r"] <= 20:
        raise ValueError("止盈倍数需为 0（关闭）或 0.5–20 R")
    st["tp_reentry"] = bool(st.get("tp_reentry", False))
    st["tp_partial"] = bool(st.get("tp_partial", False))
    st["tp_partial_r"] = float(st.get("tp_partial_r", 2.0) or 2.0)
    if not 0.5 <= st["tp_partial_r"] <= 20:
        raise ValueError("分批止盈倍数需在 0.5–20 R 之间")
    st["tp_frac"] = float(st.get("tp_frac", 0.5) or 0.5)
    if not 0.05 <= st["tp_frac"] <= 0.95:
        raise ValueError("分批止盈比例需在 5%–95% 之间")
    st["tp_breakeven"] = bool(st.get("tp_breakeven", False))
    st["tp_be_fees"] = bool(st.get("tp_be_fees", True))
    st["fast_exit_tf"] = str(st.get("fast_exit_tf", "off") or "off")
    if st["fast_exit_tf"] not in ("off", "5m", "10m", "1d"):
        raise ValueError("快速离场周期只能是 off / 5m / 10m / 1d")
    # 2026-11-14：模拟盘 / 实盘禁用快速离场。研究（docs/STRATEGY_FORMULAS.md）里 5m / 10m / 1D 每一组都显著劣于不离场
    # （5m EMA50：+160% → 约 −8%），而且回测基线从未启用它；旧版页面能把它存成 5m，导致长线单在 4h 收盘之间被 5m 破位逐个平掉、
    # 再锁到信号改变（kean 本地 11-14 01:35–02:15 北京时间 8 笔亏损平仓）。保存的旧值一律按 off 处理；研究只能在脚本里显式传 fast=。
    st["fast_exit_tf"] = "off"
    st["fast_exit_n"] = int(st.get("fast_exit_n", 50) or 50)
    if not 5 <= st["fast_exit_n"] <= 500:
        raise ValueError("快速离场 EMA 周期需在 5–500 之间")
    st["fast_exit_confirm"] = int(st.get("fast_exit_confirm", 2) or 1)
    if not 1 <= st["fast_exit_confirm"] <= 12:
        raise ValueError("快速离场确认根数需在 1–12 之间")
    st["rebalance_band"] = float(st.get("rebalance_band", 0) or 0)
    if st["rebalance_band"] and not 0.05 <= st["rebalance_band"] <= 2:
        raise ValueError("调仓阈值需为 0（关闭）或 0.05–2（即 5%–200%）")
    st["rebalance_band_down"] = float(st.get("rebalance_band_down", 0) or 0)
    if st["rebalance_band_down"] and not 0.05 <= st["rebalance_band_down"] <= 2:
        raise ValueError("减仓调仓阈值需为 0（同调仓阈值）或 0.05–2（即 5%–200%）")
    st["port_vol_target"] = float(st.get("port_vol_target", 0) or 0)
    if st["port_vol_target"] and not 0.05 <= st["port_vol_target"] <= 2:
        raise ValueError("组合波动率目标需为 0（关闭）或 0.05–2（年化 5%–200%）")
    st["port_vol_lookback"] = int(st.get("port_vol_lookback", 180) or 180)
    if not 30 <= st["port_vol_lookback"] <= 1000:
        raise ValueError("组合波动率回看根数需在 30–1000 之间")
    st["name_vol_target"] = float(st.get("name_vol_target", 0) or 0)
    if st["name_vol_target"] and not 0.1 <= st["name_vol_target"] <= 5:
        raise ValueError("单币波动率封顶需为 0（关闭）或 0.1–5（年化 10%–500%）")
    st["name_vol_lookback"] = int(st.get("name_vol_lookback", 120) or 120)
    if not 20 <= st["name_vol_lookback"] <= 1000:
        raise ValueError("单币波动率回看根数需在 20–1000 之间")
    st["rebalance_mode"] = str(st.get("rebalance_mode", "stop") or "stop")
    if st["rebalance_mode"] not in ("stop", "atr"):
        raise ValueError("调仓模式只能是 stop 或 atr")
    st["adaptive_size_mode"] = str(st.get("adaptive_size_mode", "off") or "off")
    if st["adaptive_size_mode"] not in ("off", "spread", "adx"):
        raise ValueError("自适应仓位模式只能是 off / spread / adx")
    st["adaptive_size_lo"], st["adaptive_size_hi"] = float(st.get("adaptive_size_lo", 0.5)), float(st.get("adaptive_size_hi", 1.0))
    if not 0.1 <= st["adaptive_size_lo"] <= st["adaptive_size_hi"] <= 2.0:
        raise ValueError("自适应仓位乘子需满足 0.1 ≤ 下限 ≤ 上限 ≤ 2（单笔 5% / 单币 20% 上限仍然有效）")
    st["direction_bias"] = _as_bool(st.get("direction_bias", False))
    st["direction_bias_band"] = float(st.get("direction_bias_band", 0.1) or 0.0)
    if not 0 <= st["direction_bias_band"] <= 1:
        raise ValueError("方向偏置带宽需在 0–1 之间（0.1 = BTC 高于体制线 10% 才只做多）")
    st["auto_retune"] = _as_bool(st.get("auto_retune", False))
    st["retune_every_days"] = int(st.get("retune_every_days", 30) or 30)
    if not 7 <= st["retune_every_days"] <= 180:
        raise ValueError("自动调参间隔需在 7–180 天之间")
    st["retune_lookback_days"] = int(st.get("retune_lookback_days", 365) or 365)
    if not 90 <= st["retune_lookback_days"] <= 600:
        raise ValueError("自动调参回看需在 90–600 天之间")
    st["retune_margin"] = float(st.get("retune_margin", 0.3) or 0.0)
    if not 0 <= st["retune_margin"] <= 2:
        raise ValueError("自动调参迟滞需在 0–2（Sharpe）之间")
    st["hot_reload"] = _as_bool(st.get("hot_reload", True))
    rk["starting_equity_usdt"] = float(rk.get("starting_equity_usdt", 1000.0))
    if not 10 <= rk["starting_equity_usdt"] <= 1e9:  # 0 / 负数 / 空输入（前端 +"" = 0）会让纸面账本与回测权益为 0，收益率除零、仓位全为 0
        raise ValueError("起始纸面资金需在 10–1,000,000,000 USDT 之间")
    rk["allow_spot_long"], rk["allow_perp_short"] = bool(rk.get("allow_spot_long", True)), bool(rk.get("allow_perp_short", True))
    rk["max_risk_per_trade"] = float(rk["max_risk_per_trade"])
    rk["max_weight_per_name"] = float(rk["max_weight_per_name"])
    if not 0 < rk["max_risk_per_trade"] <= 0.05:
        raise ValueError("单笔风险上限不能超过 5%（已约定规则）")
    if not 0 < rk["max_weight_per_name"] <= 0.20:
        raise ValueError("单币权重上限不能超过 20%（已约定规则）")
    if float(rk["max_gross_exposure"]) > 1.0:
        raise ValueError("总敞口上限不能超过 1 倍权益（放大敞口请用「杠杆放大敞口」开关）")
    rk["trade_mode"] = str(rk.get("trade_mode", "perp_both") or "perp_both")
    if rk["trade_mode"] not in ("perp_both", "spot_perp"):
        raise ValueError("交易方式只能是 perp_both（多空都用永续）或 spot_perp（现货做多 + 永续做空）")
    try:
        lev = float(rk.get("perp_leverage", 10))
    except (TypeError, ValueError):
        raise ValueError("杠杆倍数需为 1–100 的整数") from None
    if lev != int(lev) or not 1 <= lev <= 100:
        raise ValueError("杠杆倍数需为 1–100 的整数")
    rk["perp_leverage"] = int(lev)
    rk["leverage_scales_exposure"] = bool(rk.get("leverage_scales_exposure", False))
    if s["venue"] not in ("okx", "gate"):
        raise ValueError("交易所只能是 okx 或 gate")
    syms = [x.strip().upper().replace("/", "").replace("-", "") for x in s["symbols"] if x.strip()]
    syms = [x if x.endswith("USDT") else x + "USDT" for x in syms]
    if not 1 <= len(syms) <= 30:
        raise ValueError("标的数量需在 1–30 之间")
    s["symbols"] = list(dict.fromkeys(syms))
    if s["live"]["mode"] not in ("paper", "live"):
        raise ValueError("模式只能是 paper 或 live")
    for k in ("live_enabled", "okx_demo", "gate_testnet"):  # 字符串 "false" / "0" 不能被 bool() 当成 True（否则 live_enabled:"false" 也会开实盘）
        s["live"][k] = _as_bool(s["live"].get(k, DEFAULTS["live"][k]))
    s["worker"]["interval_sec"] = max(60, int(s["worker"]["interval_sec"]))
    if s["worker"].get("deselect_policy") not in ("keep", "flatten"):
        raise ValueError("取消勾选币种的处理方式只能是 keep 或 flatten")
    sl = s["short_layer"]
    if sl.get("enabled") and not SHORT_LAYER_VALIDATED:
        raise ValueError("短线层未通过验证（未见数据上扣费后期望为负），不能开启")
    if sl.get("base_tf") not in ("1m", "5m", "10m", "1h"):
        raise ValueError("短线层周期只能是 1m / 5m / 10m / 1h")
    if not 0 < float(sl.get("budget_frac", 0.3)) <= 0.5:
        raise ValueError("短线风险预算需在 0–50% 之间")
    return s


SHORT_LAYER_VALIDATED = False  # 研究门槛未通过；只有新研究在两家交易所未见数据上扣费后期望 > 0 才能改为 True
SUPPORTED_SYMBOLS = list(DEFAULTS["symbols"])  # 开始交易时可勾选的币种（官方 OKX / Gate 都有现货与 USDT 永续）


def save(s: dict) -> dict:
    with _LOCK:
        s = validate(_merge(DEFAULTS, s))
        _write_db(s)
        return s


def update(patch: dict) -> dict:
    with _LOCK:
        return save(_merge(load(), patch))


def live_armed(s: dict) -> bool:
    lv = s["live"]
    return lv["mode"] == "live" and _as_bool(lv["live_enabled"]) and lv.get("confirm_phrase") == LIVE_CONFIRM_PHRASE
