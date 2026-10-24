# Roadmap

一次只做一個 phase。每個 phase 結束時: 測試通過、更新 CLAUDE.md「目前狀態」與「常用指令」、commit,然後停下來回報,等使用者確認再進下一個 phase。

## Phase 0: Scaffold
範圍:
- `pyproject.toml` 已有初版,補齊後建立 `src/fantasy/` package 與 `fantasy` CLI 入口 (只有 `--help` 和 `version`)。
- 用 pydantic 載入 `config/league.yaml`、`config/model.yaml`,驗證失敗要報錯。
- Seed data loader: 讀 `data/prior/prior_z_2026-27.csv`、`data/draft/draft_results_2026-27.csv`、`data/manual/my_roster_2026-10-24.csv`。
- 名字正規化函式 (去變音符號、處理 Jr./III、縮寫名 "K. Towns")。
- 預算計算函式 (methodology §7)。

驗收:
- `pip install -e ".[dev]"` 後 `fantasy --help` 可執行。
- 測試涵蓋: config 驗證、seed 筆數 (prior 156、draft 132)、名字正規化 (Jokić → jokic、"A. Şengün" 能對到 "Alperen Sengun")、預算計算。
- `ruff check` 通過。

## Phase 1: Yahoo ingest
範圍:
- `fantasy auth`: 本機 OAuth,token 存 `.secrets/`。也支援從環境變數讀 token (雲端用)。
- `fantasy sync --since YYYY-MM-DD [--until]`: 抓 architecture §4 列的資料,寫入 `data/warehouse/` 各 CSV,idempotent upsert。
- 先把每種 API 回應存一份 JSON fixture 到 `tests/fixtures/yahoo/`,parser 用 fixture 測。
- 產生 `player_map.csv`,列出對不到或有多個候選的 prior 球員。
- 回答 architecture §4 的「Phase 1 要確認的事」,把結果寫回 architecture.md 和 league.yaml 的 verify 欄位。

驗收:
- 從 2026-10-20 (或實際開季日) 同步到今天,重跑一次後所有 CSV 沒有變化 (idempotency 測試)。
- `rosters.csv` 中我的隊伍當天陣容和 `data/manual/my_roster_2026-10-24.csv` 一致。
- 列出 player_map 對不到的人,等使用者確認。

## Phase 2: Compute + 週報
範圍:
- `fantasy compute`: methodology §2-§4 的 actual z、blended z、週價值。
- ScheduleProvider (CSV 版) 與每日 lineup 最佳化。
- `fantasy report --week N|current`: 產出 `reports/weekly/YYYY-Www.md`,格式見下方。
- Prior scale 診斷 (methodology §6.2),只輸出診斷結果,不自動 rescale。

週報格式:
1. 上週結果: 比分、贏 / 輸的類別 (Phase 3 後加上與預測的比較)
2. 球員檢查表: `球員 | GP | MPG | 角色訊號 | prior_z 合計 | blended_z 合計 | Δ | 動作建議`
3. 本隊 10 類 blended z 合計,標出最弱 2 類與 punt 判斷
4. Waiver 候選: blended 週價值前 10 名,以及和我陣容最弱的人比較的差值
5. 下週: 對手、每位球員出賽場數 (標出 ≤ 2 場)
6. 異動預算: 本週與本季剩餘

驗收:
- z-score 計算有單元測試 (用小型手算資料驗證 counting 與 percentage 兩種算法)。
- 用 Phase 1 的實際資料產出第一份週報。

## Phase 3: 預測與回測
範圍:
- Monte Carlo 類別勝率 (methodology §5.1),每週開始前寫入 `predictions.csv`。
- `fantasy backtest`: 校準指標、prior 準確度、建議追蹤 (methodology §6)。
- 週報加入「上週預測 vs 實際」與「建議追蹤」段落。
- `.claude/skills/weekly-review/` 的流程可以完整跑通。

驗收:
- 固定 seed 下模擬結果可重現。
- 回測報告在只有 1-2 週資料時要明講樣本不足,不輸出結論。

## Phase 4: 擴充 (範圍待定)
候選:
- NBA 賽程 API provider
- 角色改變自動偵測
- 交易評估 (雙方 10 類變化)
- 對手分析
- 雲端 routine 每週自動執行
- Dashboard (HTML 或其他)
