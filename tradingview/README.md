# TradingView × FCN：工具選項與 K 線標記指標

## 1. 有哪些可以直接拿來用（2026-10 調查）

| 類型 | 項目 | 能做什麼 | 注意 |
|---|---|---|---|
| **Pine Script（最推薦）** | 本資料夾 `fcn_marker.pine` | 貼進你自己的 TradingView，直接在真實 K 線上畫出 KO／轉換價／KI、月度觀察日、觸發與到期結果 | 免費帳號即可；資料用你 TradingView 上的報價 |
| 官方開源圖表庫 | [Lightweight Charts](https://github.com/tradingview/lightweight-charts)（Apache-2.0，npm `lightweight-charts`，v5） | 自己的網頁/APP 畫 K 線；`createSeriesMarkers` 打標記、`createPriceLine` 畫水平線、plugin/primitive 畫區塊（[文件](https://tradingview.github.io/lightweight-charts/docs/next/plugins/intro)） | **不含資料**，要自己餵 OHLC |
| 官方完整圖表 | Charting Library / Advanced Charts | TradingView 原生介面＋畫圖工具 | 需申請授權，個案審核（[FAQ](https://www.tradingview.com/charting-library-docs/v29/getting_started/Frequently-Asked-Questions)） |
| 官方資料 API | — | **沒有**公開行情 API；REST API 只給券商夥伴 | |
| 社群 MCP（非官方） | [atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp)（最多星，指標/篩選/回測）、[bidouilles/mcp-tradingview-server](https://github.com/bidouilles/mcp-tradingview-server)（指標＋OHLCV）、[mikeh-22/tradingview-mcp](https://github.com/mikeh-22/tradingview-mcp)（報價、K 線、自選、Pine）、[ali-rajabpour/tradingview-mcp](https://github.com/ali-rajabpour/tradingview-mcp)、[ertugrul59/tradingview-chart-mcp](https://github.com/ertugrul59/tradingview-chart-mcp)（截 K 線圖）、[daviddme/…indicator-search…](https://github.com/daviddme/tradingview-indicator-search-mcp-server)（搜 Pine 原始碼） | 讓 Claude 在**你本機**抓 TradingView 資料或截圖 | 非官方、靠爬蟲/瀏覽器自動化，可能違反 TradingView 服務條款、隨時失效；裝之前請先讀原始碼 |
| 社群 Python | `tradingview-screener`、TvDatafeed | 抓篩選器/歷史 K 線 | 同上，非官方 |

> Claude 的官方連接器目錄目前**沒有** TradingView。這個雲端環境也連不到 tradingview.com，所以社群 MCP 只能裝在你自己的電腦（Claude Desktop / Claude Code 本機）。

## 2. 安裝 `fcn_marker.pine`

1. TradingView 打開第 1 檔標的（例如 `NASDAQ:NVDA`），**切到日線**。
2. 下方「Pine 編輯器」→ 新建 → 全部貼上 `fcn_marker.pine` → 「加到圖表」。
3. 指標設定裡填你的條款：進場日、天期、KO／轉換價／KI、AKI 或 EKI、年化配息；worst-of 的第 2、3 檔填 `NYSE:TSM` 等。

> 我在雲端環境沒辦法連 TradingView 實際編譯；如果貼上後報錯，把錯誤訊息貼回來給我，我來修。

## 3. 怎麼看圖

```
   KO 100%  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┤ 綠虛線：月度觀察日全部標的 ≥ 這裡 → 提前贖回
   轉換價    · · · · · · · · · · · · · ·┤ 深藍點線：轉股時用這個價接股票
   KI 65%   ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─┤ 紅虛線：跌破＝保護消失（AKI 任一天；EKI 只看到期）
   ▲進場        ①  ②  ③  ④  ⑤  ⑥    │← 到期日
```

| 圖上元素 | 意思 | 你該注意什麼 |
|---|---|---|
| ▲ 進場標籤 | 期初價 = 100% 基準 | 三條線都是「期初價 × %」 |
| ①②③… 圓點 | 月度觀察日（假日順延）；滑鼠移上去看當時 worst-of % | 綠＝當天 KO、紅＝當天已在 KI 下方、灰＝一般 |
| ⚠ KI 觸發 | AKI 下，最差標的第一次跌破 KI | 觸發後**不是立刻賠**，要看到期是否仍 < 轉換價 |
| ✓ KO 提前贖回 | 拿回本金＋已領配息 | 上漲被切掉，只拿到幾期配息 |
| ✗ 轉股 | 到期時觸發過 KI 且最差 < 轉換價 → 以轉換價接股 | 標籤寫本金損失與含配息總報酬 |
| 右上表格 | 最差標的、距 KI、距 KO、已領配息、σ20/σ250、到期日 | **距 KI < 10% 變紅**，是要開始評估的警戒 |
| 綠色底色 | σ20/σ250 < 0.9（短期波動低於長期） | 回測中唯一前後兩段結論一致、略佳的進場環境（效果很小） |
| 紅色底色 | σ20/σ250 > 1.2（波動飆升） | 回測中**最差**的進場時機（「大跌後配息比較肥」的直覺被推翻） |
| 橘線 | 200 日均線 | 參考用；回測顯示「站上 200MA 才進場」沒有幫助 |

### 看圖三步驟
1. **進場前**：看底色。紅底先不要進；再看最近一年 K 線有沒有單日 −20% 以上的跳空，有的話，KI 離期初價的距離其實沒有看起來那麼遠。
2. **存續中**：只盯右上表格的「距 KI」跟「最差標的」。KO 線附近的波動不用管。
3. **觸發 KI 後**（AKI）：問自己願不願意在轉換價持有那檔股票。這張單接下來就是一張「到期前要回到轉換價」的賭注，跟配息已經沒有關係。

## 4. 想讓 Claude 直接看你的 K 線
- **最簡單**：在 TradingView 截圖貼給 Claude，Claude 可以讀圖幫你標註、解讀。
- **自動化**：在本機 Claude Desktop / Claude Code 裝上表中任一個社群 MCP（例如 chart 截圖類或 OHLCV 類），Claude 就能自己抓 K 線，再搭配 `research/quote_check.py` 算報價是否划算。
