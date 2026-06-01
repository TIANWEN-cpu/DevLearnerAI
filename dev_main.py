import logging
from multiprocessing import freeze_support

from app.window import run

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

if __name__ == "__main__":
    freeze_support()
    raise SystemExit(run())
