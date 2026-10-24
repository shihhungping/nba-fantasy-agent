# nba-fantasy-agent

Yahoo Fantasy NBA「樹龜投不進肚子大聯盟」(2026-27) 的賽季分析工具。開發規格見 `CLAUDE.md` 與 `docs/`。

## 初次設定 (本機)

1. 建立 Yahoo app: https://developer.yahoo.com/apps/create/
   - API Permissions 勾選 Fantasy Sports (Read)
   - Redirect URI 依 yfpy 文件設定
   - 記下 Client ID (Consumer Key) 與 Client Secret
2. 安裝:
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -e ".[dev]"
   cp .env.example .env   # 填入 YAHOO_CONSUMER_KEY / YAHOO_CONSUMER_SECRET
   ```
3. 第一次授權 (Phase 1 完成後): `fantasy auth`,會開瀏覽器。
4. 建 GitHub repo (建議 private) 並 push。

## 雲端 Claude Code 環境設定

在 claude.ai/code 編輯 cloud environment:
- **Network access**: 改成 Custom,Allowed domains 加入 Yahoo 網域 (Phase 1 會確認完整清單),勾選保留預設的 package manager 清單。
- **Environment variables**: `YAHOO_CONSUMER_KEY`、`YAHOO_CONSUMER_SECRET`、`YAHOO_ACCESS_TOKEN_JSON` (本機授權後的 token JSON)。
- **Setup script**: `pip install -e ".[dev]" || true`

雲端 session 之間不保留檔案,每次同步後要 commit 並 push `data/warehouse/` 與 `reports/`。

## 開發

用 Claude Code 開發時,第一次請貼上 `docs/kickoff_prompt.md` 的內容。
