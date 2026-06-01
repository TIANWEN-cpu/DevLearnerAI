from multiprocessing import freeze_support

from app.window import run


if __name__ == "__main__":
    freeze_support()
    raise SystemExit(run())
