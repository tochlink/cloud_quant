# 1h 收盘同向连续根数（run-length）事件：反向 / 顺势（2026-11-27 ~10:30 PST，短线研究，REJECTED）

- 查重：4h streak 入场闸门（close_streak_runs_gate）与蜡烛形态已否决；本族是 1h 独立事件、单币裸单 / 篮子对冲，持有 6–48h，未测过。
- 公式：某币 1h 收盘对收盘收益符号连续同向根数首次等于 k 时触发，次根开盘入场，方向 = 反向（fade）或顺势（follow），持有 H 根，单币同时一仓；hedge=1 时对其余 7 币等权反向对冲。费用每腿 5.1 bps（压力 15.1），含官方资金费。
- 预注册（sha256 4a848366ddc99fbcefc89039fd728192dd517207112ad12b3b54b53366f508da）：k∈{4,6,8} × H∈{6,24,48} × {fade,follow} × hedge{0,1} = 36 格 × OKX/Gate 默认 8 币 + OKX 未调 new8；分段 train<2024-10-21、test<2026-03-05、post；placebo 信号后移 168h。
- 结果：fade 全部 post 均值为负（−0.7…−78 bps，仅 k8H6 裸单 +8/+15 bps，test −9…−12）；follow 仅 k8H24/H48 裸单 post 为正（H48 OKX +57.5 bps t0.89，Gate +51.7 t0.77，n≈71），但 test 反号（OKX −32.9、Gate −99.4）、new8 train −42，placebo +168h 在 test 同样 −124/−165 bps（t −3.2），邻格 k6H48 post OKX −8.4。hedge=1 全部亏（−15…−50 bps，成本主导）。无任何格在两所 train/test/post 同号。
- 结论：否决，不进观察名单，不加 shadow，默认与纸面不变。
- 永不重测：改 k / H / 方向、换裸单/对冲、换收盘对收盘为开收阳阴、加量能 / 幅度过滤、4h 或 15m 版 run-length。
- 研究表：output/research_1h_close_streak_run_event.csv；脚本 scratch/streak1h/run.py。
