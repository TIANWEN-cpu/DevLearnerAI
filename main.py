import logging
from logging.handlers import RotatingFileHandler
from multiprocessing import freeze_support

from app.config import LOG_DIR, ensure_runtime_dirs
from app.window import run

ensure_runtime_dirs()

log_file = LOG_DIR / "app.log"
file_handler = RotatingFileHandler(
    log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(), file_handler],
)

if __name__ == "__main__":
    freeze_support()
    raise SystemExit(run())
