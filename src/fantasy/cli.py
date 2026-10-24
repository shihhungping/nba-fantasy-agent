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
