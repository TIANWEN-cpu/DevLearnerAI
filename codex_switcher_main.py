from multiprocessing import freeze_support

from app.codex_switcher import run

if __name__ == "__main__":
    freeze_support()
    raise SystemExit(run())
