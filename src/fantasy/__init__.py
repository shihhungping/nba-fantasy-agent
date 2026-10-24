"""Yahoo Fantasy NBA in-season analysis toolkit."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nba-fantasy-agent")
except PackageNotFoundError:  # running from source without install
    __version__ = "0.0.0+unknown"
