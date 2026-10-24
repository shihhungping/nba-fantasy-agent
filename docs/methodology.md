# Methodology

計算邏輯的唯一規格。程式實作與這份文件不一致時,先問使用者以哪個為準,再一起更新。參數值在 `config/model.yaml`。

## 1. Prior

- 來源: `data/prior/prior_z_2026-27.csv`,156 人,季前 (2026-10-02) 產出。
- 10 類別的 per-game z-score,TO 已轉成正值越好。
- `src`: P = 2026-27 projection、S = 上季數據依新球隊調整、E = 估計值 (信心低)。
- `draft_bid_value`、`market_value` 是選秀用的價格,賽季中不參與計算,只在報告中當參考。
- 已知限制: 原始 z-score 的 pool 定義與標準差不明。Phase 2 要做 scale 診斷 (見 §6)。

## 2. Actual z-score

### 2.1 Pool
1. 取 GP ≥ `pool.min_gp_for_pool` 的所有球員,計算 per-game 數據。
2. 用全體分布算一次 z,依 10 類 z 合計排序,取前 `pool.size` 名。
3. 用這 `pool.size` 人重新計算 mean 與 sd,再算一次所有球員的 z。

Pool 要涵蓋全聯盟,不能只用自己隊伍或只用被選走的球員。資料來源是各隊陣容 + waiver 上依 Yahoo rank 排序的前段球員。

### 2.2 Counting stats (3PTM, PTS, REB, AST, ST, BLK, TO, DD)
- `z = (x − mean_pool) / sd_pool`,x 是 per-game 平均。
- TO 的 z 取負號,讓所有類別都是正值越好。
- DD 是每場是否達成 double-double 的比率 (0/1 平均)。

### 2.3 Percentage (FG%, FT%)
用出手量加權的 impact,不能直接對百分比算 z:
- `impact = (player_pct − pool_pct) × attempts_per_game`
- `pool_pct = Σmakes / Σattempts` (pool 內加總)
- `z = (impact − mean(impact_pool)) / sd(impact_pool)`

## 3. Blending

- 樣本門檻 (`sample_thresholds`):
  - GP ≤ 5: 只回報角色訊號,blended_z = prior_z。
  - Counting stats 在 GP ≥ 6 開始混合;FG%, FT% 在 GP ≥ 16 開始混合。
- 公式: `blended_z = w × actual_z + (1 − w) × prior_z`,`w = GP / (GP + k)`。
  - k 依類別: counting 15、FG% 30、FT% 40。
  - `k_effective = k × src_k_multiplier[src]`,src = E 時 k 減半。
- 不在 prior 的球員: 直接用 actual_z,報告標記「無 prior」。
- 角色改變 (先發 / 替補、隊友長期缺陣、交易) 後,只用改變後的場次計算 actual。角色改變點先由使用者在 `data/manual/role_changes.csv` 標記,Phase 4 再考慮自動偵測。

## 4. 價值要乘出賽數

- 週價值 = Σ_類別 blended_z × 本週可上場場數。
- 可上場場數要考慮 lineup 限制: 同一天能上場的球員數不能超過 active slots,而且要符合位置資格。用每日 lineup 最佳化 (見 §5.2) 算出每位球員實際能計入的場數。
- 長期價值 = per-game blended_z × 預期剩餘出賽比例。出賽比例先用季前 src 與傷病標記粗估,報告要明講折扣。

## 5. 每週預測

### 5.1 類別勝率
- 對每一週的對戰,用 Monte Carlo 模擬雙方 10 類總和:
  - 每位球員每個排定出賽日,從他的 game log 抽一場 (bootstrap)。
  - game log 少於 `min_games_for_resample` 時,用 prior_z 反推的 per-game 平均與聯盟典型變異補樣本。反推方式在 Phase 3 定案,實作前先提出方案。
  - FG%, FT% 用模擬出的 makes/attempts 加總後再算百分比。
- 輸出: 每類勝率、預期贏類數、整體勝率。
- 每次預測都寫入 `reports/predictions/predictions.csv`,欄位包含 `week, opponent, category, p_win, predicted_at, model_version`。預測在該週開始前產生,之後不能修改。

### 5.2 Lineup 最佳化
- 每天依位置資格把有比賽的球員分配到 active slots,最大化當日 blended 價值 (或只最大化出賽人數)。
- 規模小,可以用 `scipy.optimize.linear_sum_assignment` 或簡單 ILP。

## 6. 回測

### 6.1 預測校準
- 每週結算後,把實際類別勝負寫進 `predictions.csv` 的 `actual_win` 欄位。
- 指標: 每類 Brier score、依 `calibration_bins` 分組的 reliability (預測 60-80% 勝率的類別實際贏了幾成)、預期贏類數 vs 實際贏類數的 MAE。
- 累積 6-8 週 (約 60-80 個類別結果) 後,才對系統性偏差下結論。

### 6.2 Prior 準確度
- GP ≥ 15 後,比較 prior_z 與 actual_z: 每類的相關係數、平均偏差,以及依 src (P/S/E) 分組的誤差。
- Scale 診斷: 比較 prior 與 actual 在 pool 內每類的 sd。差距大時,提出 rescale 方案讓使用者決定,不要自動套用。

### 6.3 建議追蹤
- 每個 add/drop 建議寫入 `reports/predictions/recommendations.csv`: `date, add_player, drop_player, expected_delta_value, horizon_weeks`。
- 在 2 週與 4 週後計算實際 delta (add 球員的實際價值 − drop 球員的實際價值),記錄命中與否。

## 7. 異動預算
- 季後賽保留 15 次 (Week 20-22 每週 5 次)。
- 例行賽每週建議上限 = min(5, (90 − 15 − 已用次數) / 剩餘例行賽週數)。
- 報告中每個 add/drop 建議都附本週與本季剩餘次數。

## 8. Punt 判斷
- 可 punt: FG%, FT%, 3PTM, PTS, AST, TO。不 punt: REB, ST, BLK, DD。最多 punt 1 類。
- 條件: 該類陣容 blended z 合計 ≤ −1.5,且符合結構條件 (FT% 差的長人是核心 → punt FT%;2 位以上高 TO 持球後衛 → punt TO)。
- 決定後至少 4 週不改。已 punt 的類別在 add/drop 評估中權重設 0。

## 變更紀錄
| 日期 | 變更 | 原因 |
|---|---|---|
| 2026-10-24 | 初版 | 從 claude.ai Project 的賽季顧問 instructions 整理 |
