import logging
from multiprocessing import freeze_support

from app.config import LOG_DIR, ensure_runtime_dirs
from app.utils.logger import configure_logging
from app.window import run

ensure_runtime_dirs()

configure_logging(
    log_dir=LOG_DIR,
    level=logging.INFO,
    json_format=False,
    enable_category_files=True,
    enable_slow_op_tracking=True,
    enable_memory_tracking=False,
)

if __name__ == "__main__":
    freeze_support()
    raise SystemExit(run())
