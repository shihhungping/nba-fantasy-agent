# Kickoff prompt

第一次在這個 repo 開 Claude Code 時貼上下面這段。之後每個 phase 開始時,把 "Phase 0" 換成下一個 phase 即可。

---

這個 repo 是 Yahoo Fantasy NBA 的賽季分析工具,目前只有規格、設定檔和 seed data,還沒有程式碼。

請依序執行:

1. 讀 `CLAUDE.md`,再讀 `docs/roadmap.md`、`docs/methodology.md`、`docs/architecture.md`、`config/` 下兩個 yaml,以及 `data/` 下的 CSV 欄位。
2. 如果還不是 git repo,執行 `git init` 並把目前所有檔案做第一個 commit。
3. 進入 plan mode,針對 **Phase 0** 提出實作計畫:
   - 檔案與 module 結構
   - 每個函式的責任與介面
   - 測試清單 (對應 roadmap 的驗收條件)
   - 你在規格中發現的矛盾、缺漏或不確定之處。用 AskUserQuestion 問我,不要自行假設。
4. 我確認計畫後再實作。完成後跑 `ruff check src tests` 與 `pytest`,全部通過才 commit。
5. 更新 `CLAUDE.md` 的「目前狀態」和「常用指令」,然後停下來回報: 做了什麼、測試結果、下一個 phase 開始前需要我準備什麼 (例如 Yahoo app 的 consumer key)。

限制:
- 只做 Phase 0,不要提前實作 Yahoo API 呼叫或 z-score 計算。
- 不要讀取 `.env` 或 `.secrets/`。
- 不要新增 `pyproject.toml` 以外的依賴管理工具;要加套件先問我。
