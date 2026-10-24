# Architecture

## 1. 資料流

```
Yahoo Fantasy API ──(yfpy, OAuth 2.0)──▶ ingest ──▶ .cache/ (原始 JSON, gitignore)
                                            │
NBA 賽程 (ScheduleProvider) ───────────────┤
                                            ▼
                                   data/warehouse/*.csv (正規化, commit)
                                            │
data/prior/ + data/draft/ (seed) ──────────┤
                                            ▼
                                   compute: actual z → blended z → 週價值
                                            │
                              ┌─────────────┼──────────────┐
                              ▼             ▼              ▼
                          predict       backtest       recommend
                              └─────────────┼──────────────┘
                                            ▼
                         reports/weekly/YYYY-Www.md + reports/predictions/*.csv
                                            │
                                            ▼
                         (手動) 上傳週報到 claude.ai Project,手機上對話用
```

## 2. Warehouse 表 (CSV)

| 檔案 | Grain | Natural key | 說明 |
|---|---|---|---|
| `teams.csv` | 每隊 | `team_key` | 隊名、manager、異動次數 |
| `rosters.csv` | 每隊 × 每日 | `team_key, date, player_key` | 當日陣容與 slot (SCD 快照) |
| `players.csv` | 每位球員 | `player_key` | 名字、NBA 隊、位置資格、傷病狀態 (最新值) |
| `player_game_stats.csv` | 每球員 × 比賽日 | `player_key, game_date` | 單場 10 類原始數據 + MIN + FGM/FGA/FTM/FTA |
| `matchups.csv` | 每週 × 每組對戰 × 每類 | `week, team_key, category` | 雙方類別總和與勝負 |
| `transactions.csv` | 每筆異動 | `transaction_key` | add/drop/trade |
| `player_map.csv` | 每位 prior 球員 | `prior_name` | prior 名字 → Yahoo `player_key`,人工確認欄位 `confirmed` |
| `schedule.csv` | 每隊 × 比賽日 | `nba_team, game_date` | NBA 賽程 |

- 寫入一律 upsert by natural key,同一天重跑結果相同。
- `rosters.csv` 保留每日快照,不要覆蓋歷史。資料量: 12 隊 × 13 人 × 約 170 天 ≈ 2.7 萬列,CSV 足夠。
- `player_game_stats.csv` 只抓 pool 需要的球員 (各隊陣容 + waiver 前段),約 200 人 × 80 場 ≈ 1.6 萬列。

## 3. 儲存決策 (ADR)

**決策**: warehouse 用 CSV commit 進 git,衍生資料不 commit (可重算),原始 JSON 不 commit。

**原因**:
- 雲端 Claude Code session 之間不保留檔案。每個 session 從 GitHub clone repo,git 是唯一的持久層。
- 資料量小 (全季幾 MB),CSV 的 diff 可讀,方便在 PR 裡檢查每週變化。

**Trade-offs**:
- SQLite / DuckDB 查詢較方便,但 binary 檔 commit 進 git 無法 diff,多 session 同時寫入會衝突。之後如果需要查詢,可以在執行時從 CSV 載入 DuckDB in-memory,不改儲存格式。
- Parquet 型別較安全,但同樣無法 diff。資料量不到需要考慮效能的程度。

## 4. Yahoo API

- 用 `yfpy` 呼叫,OAuth 2.0。授權需要瀏覽器,第一次只能在本機做。
- 預期需要的資料 (實作時以 yfpy 方法與實際回應為準,先存 fixture 再寫 parser):
  - League settings: stat categories (取得 stat_id 對應)、roster positions、週次起訖日期
  - 各隊資訊與陣容 (含指定日期的陣容)
  - 球員指定日期的單場數據
  - 每週 scoreboard / matchup 類別結果
  - 異動紀錄與各隊已用異動數
  - Free agents (依 Yahoo rank 排序)
- 呼叫要加 retry with backoff 與請求間隔。Yahoo 沒有公開 rate limit,先保守設定 (例如每秒 1 次)。
- Phase 1 要確認的事:
  - Yahoo 的比賽日期用哪個時區
  - Refresh token 是否會在 refresh 時輪替 (影響雲端環境變數能不能固定)
  - `matchups` 的平手類別如何表示

## 5. 執行環境

### 5.1 本機
- `.env` 放 Yahoo consumer key / secret。第一次 `fantasy auth` 開瀏覽器授權,token 存在 `.secrets/` (gitignore)。

### 5.2 Claude Code 雲端環境
- **Network access**: 預設的 Trusted 等級只允許 package registries、GitHub 等網域,Yahoo 不在其中。要在環境設定把 Network access 改成 **Custom**,在 Allowed domains 加入 Yahoo 的網域 (至少 `api.login.yahoo.com`、`fantasysports.yahooapis.com`,實際以 Phase 1 抓到的請求為準),並勾選保留預設 package manager 清單。
- **Token**: 雲端無法開瀏覽器授權。在本機授權後,把 token JSON 放進雲端環境的 environment variables。環境變數對使用該環境的人可見,這裡只有使用者自己使用,可以接受。
  - Network secrets 功能是把固定的 header 加到請求上,但 Yahoo access token 約 1 小時過期、需要用 refresh token 換新,所以不適合用 network secrets。
- **持久化**: session 結束後檔案不保留。每次 `fantasy sync` 之後要 commit 並 push `data/warehouse/` 與 `reports/`。
- **排程**: 雲端的 routines 可以定期跑週報,等 Phase 3 穩定後再設定。

## 6. NBA 賽程 (未定)

- 使用者會另外申請 NBA 資料 API。先定義 `ScheduleProvider` interface,第一個實作讀 `data/manual/nba_schedule_2026-27.csv`。
- CSV 欄位: `game_date, home_team, away_team` (球隊縮寫與 prior 一致)。
- 換成 API 時只新增 provider 實作,不改下游。

## 7. Open questions
| # | 問題 | 影響 | 預計決定時間 |
|---|---|---|---|
| 1 | NBA 賽程資料來源 | §4 週價值、§5 預測 | Phase 2 前 |
| 2 | Prior 季中是否更新 (重新匯出 projections) | blend 的 prior 端 | Phase 2 |
| 3 | 是否分析對手 (交易評估、對手類別強弱) | Phase 4 範圍 | Phase 3 後 |
| 4 | 週報輸出除了 markdown,是否需要 dashboard | Phase 4 範圍 | Phase 3 後 |
