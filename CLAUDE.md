# NBA Fantasy Agent (2026-27)

Yahoo Fantasy NBA 聯盟「樹龜投不進肚子大聯盟」的賽季分析工具。從 Yahoo Fantasy API 抓資料,計算 blended z-score、回測預測準確度,產出每週建議報告。

使用者是資料工程師,熟悉 Python、SQL、PySpark。不需要解釋基礎概念。

## 回覆規範
- 使用繁體中文 (台灣用語),技術與 fantasy 術語保持英文 (z-score, punt, waiver, FAB, upsert, idempotency)。
- 括號與斜線一律半形。
- 直接給結論與數字,不要客套與修飾性語句。
- 需求或假設不確定時先問,不要自行猜測後直接實作。大改動先列 high-level approach。
- 架構決策要說明 trade-offs (maintainability / cost / 複雜度)。

## 聯盟設定
完整設定在 `config/league.yaml`,程式只能從這裡讀,不要 hardcode。摘要:
- League ID 23840,12 隊,H2H Categories,10 類別: FG%, FT%, 3PTM, PTS, REB, AST, ST, BLK, TO (越少越好), DD。
- 先發 PG, SG, G, SF, PF, F, C, C, Util, Util;BN ×1;IL ×2。Lineup 每日鎖定。
- 異動每週最多 5 次、整季最多 90 次;FAB waiver,2 天 waiver 期。
- 季後賽 6 隊, Week 20-22,2027-04-04 結束。
- 我的隊伍: `(弘平)The decision 8.7`。`data/draft/` 裡的 manager 欄位寫成 `Your Team`。

## Repo 結構
```
config/          league.yaml (聯盟規則) / model.yaml (模型參數)
data/
  prior/         prior_z_2026-27.csv: 季前 10 類 z-score (唯讀 seed)
  draft/         draft_results_2026-27.csv: 選秀結果 (唯讀 seed)
  manual/        手動輸入或截圖轉錄的資料,也當 test fixture
  warehouse/     ingest 後的正規化 CSV (commit 進 git,見「資料儲存」)
reports/         weekly/YYYY-Www.md 週報,predictions/ 預測紀錄
src/fantasy/     Python package (Phase 0 開始建立)
tests/           pytest,fixtures 放 tests/fixtures/
docs/            methodology.md, architecture.md, roadmap.md, kickoff_prompt.md
scripts/         一次性腳本 (convert_seed_data.py 已執行過)
```

## 必讀文件
- `docs/methodology.md`: z-score 計算、prior 混合、出賽加權、預測與回測方法。**改動任何計算邏輯前先讀。**
- `docs/architecture.md`: 資料流、儲存決策、Yahoo API 使用方式、雲端環境限制。
- `docs/roadmap.md`: 分 phase 的開發範圍與驗收條件。一次只做一個 phase。

## 開發規範
- Python 3.10+。套件管理用 `pyproject.toml`,安裝: `pip install -e ".[dev]"`。
- CLI 用 Typer,入口 `fantasy` (`python -m fantasy` 也要能跑)。
- 資料處理用 pandas。設定檔用 pydantic model 驗證,讀取失敗要直接報錯。
- Yahoo API 用 `yfpy`。stat_id 不要 hardcode,從 league settings 的 stat categories 依名稱對應。
- Ingest 要 idempotent: 同一天重跑結果相同,以 natural key upsert (例如 `player_key + game_date`)。
- 時區: Yahoo 與 NBA 的比賽日期用美東日期 (`game_date`) 儲存;報告顯示時另外標台灣時間。實作前先用實際 API 回應確認 Yahoo 用的是哪個時區。
- 球員對應: prior 與選秀資料用的是 ASCII 名字 (Nikola Jokic、K. Towns),Yahoo 有變音符號 (Jokić)。建立 `data/warehouse/player_map.csv` 把 prior 名字對到 Yahoo `player_key`,對不到的列出來給我確認,不要模糊比對後直接採用。
- 測試不能打網路。Yahoo 回應存成 JSON fixture 後再測。計算邏輯 (z-score、blend、預算) 一定要有單元測試。
- `ruff check` 和 `pytest` 通過才能 commit。

## 資料儲存
- 正規化資料存成 CSV 放 `data/warehouse/`,commit 進 git。雲端 session 之間不保留檔案,git 是唯一的持久層。
- Yahoo 原始 JSON 回應放 `.cache/` (gitignore),只用來 debug 與建立 fixture。
- 衍生結果 (z-score、預測) 可以從 warehouse 重算,不要當成唯一來源。

## 安全規則
- 這個工具只讀取 Yahoo 資料。不要實作任何會改動 Yahoo 的操作 (add/drop、lineup 變更、交易),即使 API 支援。
- 不要讀取、印出或 commit `.env`、`.secrets/`、token 檔案的內容。需要確認設定時只檢查變數是否存在。
- 新增外部資料來源前先問我。

## 常用指令 (隨 phase 實作逐步補上)
```bash
python -m venv .venv            # 本機第一次 (全域 Python 的 pandas 壞掉,一律用 venv)
.venv\Scripts\activate          # Windows;bash 下用 source .venv/Scripts/activate
pip install -e ".[dev]"         # 安裝
pytest                          # 測試
ruff check src tests            # lint
fantasy --help                  # Phase 0: CLI 骨架
fantasy version                 # Phase 0: 顯示版本 (python -m fantasy version 亦可)
fantasy auth                    # Phase 1: 本機 OAuth 授權
fantasy sync --since 2026-10-20 # Phase 1: 抓資料寫入 warehouse
fantasy compute                 # Phase 2: 計算 actual / blended z
fantasy report --week current   # Phase 2: 產出週報
fantasy backtest                # Phase 3: 預測準確度
```

## 目前狀態
- 2026-10-24: 開季第 1 週。**Phase 0 完成** (78 tests 通過)。下一步 Phase 1 (Yahoo ingest),等使用者確認並準備 Yahoo app。
  - `src/fantasy/`: `cli.py` (Typer)、`config.py` (pydantic,`load_configs()`)、`seeds.py` (`load_prior/load_draft/load_manual_roster`)、`names.py` (`name_key/short_key/match_name`)、`budget.py` (`compute_budget`)、`paths.py`。
  - 球隊縮寫標準 = NBA 官方 3 碼,別名在 `league.yaml` 的 `team_aliases` (key 要加引號,YAML 會把 `NO` 讀成 false)。
  - 名字比對: key 去變音/去 Jr./III;縮寫名用 (首字母, 姓氏);多候選用 nba_team 消歧,仍多個 → ambiguous,不模糊比對。
  - draft 對 prior: 128/132 對得到,對不到 4 人 (K. Filipowski、K. Maluach、R. Hachimura、W. Carter Jr.,prior 裡本來就沒有)。
  - 預算: floor 取整、週初基準 (methodology §7)。
- 我的陣容截至 2026-10-24 見 `data/manual/my_roster_2026-10-24.csv` (由 Yahoo 截圖轉錄,Kessler 那場比賽當時正在進行,數字可能不完整)。
- NBA 賽程資料來源還沒決定 (使用者會另外申請 NBA 資料 API),先用 interface + CSV fallback。
