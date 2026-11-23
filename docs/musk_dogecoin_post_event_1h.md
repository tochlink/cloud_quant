# 短线：Elon Musk 官方 X 帖子提到 Dogecoin → DOGE USDT 永续 1h 事件（2026-11-22 ~19:25 PST，研究，不改默认；否决）

- 查重：docs/STRATEGY_FORMULAS.md、docs/*.md 侧文件、output/research_*.csv、记忆中检索 musk / elonmusk / 马斯克 / tweet / twitter / doge 帖子，0 条。不同于已否决的 GDELT 新闻冲击、Wikipedia 关注度闸门、恐贪指数、Polymarket、币安 / Upbit 公告（交易所公告，不是名人社交帖子）。
- 数据（只用官方）：信号 = X API v2 全量归档搜索（connector `search_posts_all`），`from:elonmusk -is:retweet`，时间 = `created_at`（UTC）。S1 = 文本含 "dogecoin"（2022-01-01 起）；S2 = 2024-11-12 前文本含 "doge" 或 "dogecoin"（之后 "DOGE" 指政府效率部，只保留 S1）。共 **27 帖**（2022 年 16、2023 年 10、2024 年 4、**2025-01 之后 0 帖**；2026-03-05 之后 post 段 **0 个事件**）。表 `output/musk_dogecoin_posts_official.csv`。价格：OKX DOGE-USDT-SWAP 官方 1h（2022-01-29 起）、Gate DOGE_USDT 官方 1h（2025-09-24 起）、官方资金费；BTC 同所对冲腿。
- 公式：入场 = created_at + 60 s 之后第一根 1h 开盘；持有 H 根后开盘平；持仓未平时不重复入场。净收益 = dir·价格收益 − dir·资金费 − 2×taker（5.1 bps/边，压力 15.1）；hedge=btc 时加反向等名义 BTC 腿（两腿收费）。
- 预注册（`scratch/muskdoge1h/PRE_REGISTER.json`，sha256 前缀 36d9e7da，看任何 PnL 前锁定 64 格）：set {S1, S2} × kind {all, orig（非回复）} × dir {long, short} × H {1, 4, 12, 24} × hedge {none, btc}。先验 `S2_all_long_H4_none`（关注度拉盘），回退 `S2_all_short_H24_none`（拉盘回落）。切分 train 2022-01-29→2024-10-21（深未见）/ test →2026-03-05 / post →今；安慰剂 ±168h / ±720h。
- 结果（OKX，真实费，每笔净 bps；`output/research_musk_dogecoin_post_event_1h.csv`，5,120 行）：
  - 先验 `S2_all_long_H4_none`：train **−7.4**（n=22，t −0.18，胜率 50%）/ test **−474.9**（n=2）/ post **n=0**；全样本 −46.4（n=24，t −1.01）；压力费 train −27.4。Gate 只有 test 1 笔（+137），post 0 笔。
  - 回退 `S2_all_short_H24_none`：train −104.5（n=21）/ test +386（n=2）/ post n=0。
  - 安慰剂（先验，全样本）：+168h **+88.7**（t 2.65）、+720h +17.2，都好于真实事件 −46.4。
  - 邻域：H1 train −12.3、H12 train +37.9 但 test −467；S1 版本 train +46.8（n=7）/ test −580（n=1）。全格中 train、test 同为正的 11 格，样本都只有 2–5 笔，事后挑选，不采用。
- 结论：**否决**，不实现、不加模拟盘、不改默认，代码没改。2022 年后马斯克几乎不再发狗狗币帖子（2025 年起 0 帖），先验在深未见段已为负，post 段没有事件可前向验证，平移安慰剂更好。**勿以改 H、方向、对冲、帖子类型（原帖 / 回复 / 引用），或换关键词（doge / Ðoge / 🐕 / Shiba）、换其他名人账号（Saylor、Trump、CZ 等），或换币种（SHIB 等 meme 币）的方式重测本族。**
- 文件：`output/research_musk_dogecoin_post_event_1h.csv`、`output/musk_dogecoin_posts_official.csv`；脚本 `scratch/muskdoge1h/run.py`（研究脚本未推送）。

