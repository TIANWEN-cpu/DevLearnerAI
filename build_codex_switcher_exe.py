import os

import PyInstaller.__main__


project_path = os.path.dirname(os.path.abspath(__file__))
main_script = os.path.join(project_path, "codex_switcher_main.py")

PyInstaller.__main__.run(
    [
        main_script,
        "--onefile",
        "--windowed",
        "--name=CodexAccountSwitcher",
        "--noconfirm",
        "--add-data=app;app",
    ]
)

print("\n打包完成，请检查 dist 目录中的 CodexAccountSwitcher.exe")
