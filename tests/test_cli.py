import os
import subprocess
import sys

from typer.testing import CliRunner

from fantasy import __version__
from fantasy.cli import app

runner = CliRunner()


def test_help_lists_version_command():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "version" in result.output


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"fantasy {__version__}"
    assert __version__ == "0.1.0"


def test_python_m_fantasy_help():
    # 中文 Windows console 預設 cp950,強制子程序用 UTF-8 輸出才能穩定解碼
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, "-m", "fantasy", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "version" in proc.stdout
