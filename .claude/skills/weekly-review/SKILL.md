---
name: weekly-review
description: 每週結算後執行 Fantasy 週檢視 - 同步 Yahoo 資料、計算 blended z、更新預測與回測、產出週報並 commit。使用者說「週檢視」、「REVIEW」、「跑這週的報告」或 /weekly-review 時使用。
---

# Weekly review

前提: roadmap Phase 3 已完成。如果 `fantasy backtest` 指令還不存在,告訴使用者目前完成到哪個 phase,只執行已存在的步驟。

## 步驟
1. `git pull`,確認 working tree 乾淨。
2. 確認 `YAHOO_ACCESS_TOKEN_JSON` 或 `.secrets/` token 存在 (只檢查是否存在,不要印出內容)。不存在就停下來告訴使用者。
3. `fantasy sync --since <上次同步日期>`。失敗時看錯誤: 網路被擋 → 提醒雲端環境要把 Yahoo 網域加進 Allowed domains;401 → token 過期,請使用者在本機重新 `fantasy auth`。
4. `fantasy compute`
5. 在 `predictions.csv` 補上剛結束那週的 `actual_win`,然後 `fantasy backtest`。
6. `fantasy report --week current`,讀產出的週報。
7. 對週報中標記「觀察」或「drop 候選」的球員,以及 waiver 前 5 名,用 web search 查傷病、minutes restriction、先發角色。查到會改變建議的消息,在週報的「新聞」段落寫出球員、消息日期、影響方向。
8. 產生下週預測 (`fantasy report` 會寫入 predictions.csv;確認預測時間早於下週第一場比賽)。
9. `ruff check` 和 `pytest` 通過後,commit `data/warehouse/`、`reports/`,push。
10. 回覆使用者: 上週比分、預測錯的類別、最多 2 組 add/drop 建議 (附本週 / 本季剩餘異動數)、下週預測贏類數。最後附週報檔案路徑,提醒可以上傳到 claude.ai Project。

## 規則
- 不要對 Yahoo 做任何寫入操作。add/drop 只給建議,由使用者自己執行。
- 樣本不足時 (methodology §3 的門檻) 直接說「樣本不足」,不要用少量場次下結論。
- 建議的異動數不能超過 methodology §7 的預算。
