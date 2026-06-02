import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

APP_NAME = "DevLearnerAI"


def _read_package_version() -> str:
    """Read version from installed package metadata (pyproject.toml).

    Falls back to a hard-coded default when running from source without
    ``pip install -e .`` so that the application always starts.
    """
    try:
        from importlib.metadata import PackageNotFoundError, version

        return version("devlearner-ai")
    except (PackageNotFoundError, Exception):
        logger.debug("importlib.metadata 查不到 devlearner-ai 版本，使用回退值")
        return "7.0"


APP_VERSION = _read_package_version()
BASE_DIR = Path(__file__).resolve().parent.parent
RUNTIME_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))


def _resource_dir(name: str) -> Path:
    runtime_candidate = RUNTIME_DIR / name
    if runtime_candidate.exists():
        return runtime_candidate
    source_candidate = BASE_DIR / name
    if source_candidate.exists():
        return source_candidate
    return runtime_candidate


CONTENT_DIR = _resource_dir("content")
METADATA_DIR = CONTENT_DIR / "metadata"


def _user_data_root() -> Path:
    appdata = os.getenv("APPDATA") or os.getenv("LOCALAPPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"


USER_DATA_DIR = _user_data_root()
DB_DIR = USER_DATA_DIR / "data"
DB_PATH = DB_DIR / "app.db"
LOG_DIR = USER_DATA_DIR / "logs"
CACHE_DIR = USER_DATA_DIR / "cache"
EXPORT_DIR = USER_DATA_DIR / "exports"
DRAFT_DIR = USER_DATA_DIR / "drafts"
LEGACY_DB_PATH = BASE_DIR / "db" / "learner.db"

APP_TITLE = f"DevLearner AI {APP_VERSION}"
APP_SUBTITLE = "Python / 数据库 / 融合项目一体化学习平台"
API_CREDENTIAL_ALIAS = f"{APP_NAME}:mentor_api_key"


def ensure_runtime_dirs() -> None:
    for directory in (USER_DATA_DIR, DB_DIR, LOG_DIR, CACHE_DIR, EXPORT_DIR, DRAFT_DIR):
        directory.mkdir(parents=True, exist_ok=True)
