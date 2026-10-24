"""`fantasy` CLI 入口。Phase 0 只有 --help 與 version。"""

import typer

from fantasy import __version__

app = typer.Typer(
    name="fantasy",
    help="Yahoo Fantasy NBA 賽季分析工具 (樹龜投不進肚子大聯盟 2026-27)。",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def main() -> None:
    """Yahoo Fantasy NBA 賽季分析工具。"""


@app.command()
def version() -> None:
    """顯示版本。"""
    typer.echo(f"fantasy {__version__}")


@app.command()
def auth() -> None:
    """本機 Yahoo OAuth 授權 (互動式): 開瀏覽器同意後,把 Yahoo 顯示的 code 貼回終端。"""
    from fantasy.config import load_league_config
    from fantasy.yahoo.auth import AuthError, run_auth_flow

    typer.echo("即將開啟瀏覽器。登入 Yahoo 並按同意後,把頁面上的 code 貼到下面的 'Enter verifier :'。")
    try:
        path = run_auth_flow(load_league_config())
    except AuthError as e:
        typer.echo(f"授權失敗: {e}", err=True)
        raise typer.Exit(1) from e
    typer.echo(f"授權完成,token 已存到 {path} (已 gitignore,不要 commit 或貼出內容)。")
