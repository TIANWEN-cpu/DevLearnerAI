# 构建可执行文件

本文档描述如何将 DevLearnerAI 打包为独立的 Windows 可执行文件。

---

## 构建工具

项目使用 [PyInstaller](https://pyinstaller.org/) 进行打包，构建脚本位于 `scripts/build/` 目录。

---

## 环境准备

### 1. 安装构建依赖

```bash
pip install pyinstaller>=6.0
```

或通过开发依赖安装：

```bash
pip install -e ".[dev]"
```

### 2. 确认依赖完整

```bash
pip install -r requirements.txt
```

---

## 构建命令

### 使用 Makefile（推荐）

```bash
# 开发调试版
make build-dev

# 正式发布版
make build-release

# Codex 账号切换器
make build-codex
```

### 直接调用脚本

```bash
# 构建开发版
python scripts/build/build.py --variant dev --clean

# 构建发布版
python scripts/build/build.py --variant release --clean
```

### 传统方式

```bash
python scripts/build/build_dev_exe.py
```

---

## 构建产物

构建产物输出到 `dist/` 目录：

```text
dist/
├── DevLearnerAI/
│   ├── DevLearnerAI.exe     # 主可执行文件
│   ├── _internal/           # 依赖文件
│   │   ├── python3.dll
│   │   ├── PyQt5/
│   │   ├── mistune/
│   │   └── ...
│   ├── content/             # 课程内容（必须随 exe 分发）
│   └── styles/              # 样式资源
```

---

## 打包配置

### 关键路径处理

在 `app/config.py` 中，`RUNTIME_DIR` 会自动检测 PyInstaller 打包环境：

```python
RUNTIME_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
```

- 开发环境：`RUNTIME_DIR = BASE_DIR`（项目根目录）
- 打包环境：`RUNTIME_DIR = sys._MEIPASS`（PyInstaller 临时目录）

### 资源目录回退

```python
def _resource_dir(name: str) -> Path:
    runtime_candidate = RUNTIME_DIR / name
    if runtime_candidate.exists():
        return runtime_candidate
    source_candidate = BASE_DIR / name
    if source_candidate.exists():
        return source_candidate
    return runtime_candidate
```

这确保了课程内容（`content/`）和样式（`styles/`）在两种环境下都能正确找到。

---

## 用户数据路径

打包后的应用使用 `%APPDATA%/DevLearnerAI/` 存储用户数据：

```python
def _user_data_root() -> Path:
    appdata = os.getenv("APPDATA") or os.getenv("LOCALAPPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / f".{APP_NAME.lower()}"
```

这意味着：
- 数据库、日志、缓存等不会存储在 exe 同目录下
- 用户数据在应用更新后仍然保留
- 支持多用户系统中各用户独立数据

---

## 常见构建问题

### 1. 缺少模块

如果运行时报 `ModuleNotFoundError`，需要在 `.spec` 文件或构建脚本中添加 hidden imports：

```python
hiddenimports = [
    "mistune",
    "keyring.backends.Windows",
    "sqlite3",
]
```

### 2. 资源文件缺失

确保 `content/` 目录被正确包含在打包中：

```python
# 在 .spec 文件中
datas = [
    ('content', 'content'),
    ('styles', 'styles'),
]
```

### 3. 反病毒软件误报

PyInstaller 打包的 exe 可能被某些反病毒软件误报。解决方案：

- 使用代码签名证书对 exe 进行签名
- 向反病毒软件厂商提交误报申诉
- 在 CI/CD 中构建，保持构建环境一致

### 4. 文件体积过大

优化打包体积：

```bash
# 使用 UPX 压缩
pyinstaller --upx-dir=/path/to/upx ...
```

排除不必要的模块：

```python
excludes = [
    "tkinter",
    "matplotlib",
    "numpy",
    "pandas",
]
```

---

## 分发方式

### 直接分发

将整个 `dist/DevLearnerAI/` 目录打包为 ZIP：

```bash
cd dist
tar -czf DevLearnerAI-7.0-windows-x64.tar.gz DevLearnerAI/
```

### 安装程序

可以使用 NSIS 或 Inno Setup 创建 Windows 安装程序。

### 自动发布

项目配置了 GitHub Actions 发布工作流（`.github/workflows/release.yml`），可在创建 tag 时自动构建和发布。

---

## 版本管理

版本号在 `pyproject.toml` 中定义：

```toml
[project]
version = "7.0"
```

查看当前版本：

```bash
make version
```

---

## CI/CD 集成

GitHub Actions 工作流在每次 push 和 PR 时自动运行：

```yaml
# .github/workflows/ci.yml
- name: Run lint
  run: ruff check .

- name: Run tests
  run: pytest -v --tb=short
```

发布工作流在 tag 创建时触发构建和上传。

---

## 相关文档

- [快速开始](getting-started.md) - 开发环境搭建
- [开发工作流](development.md) - 日常开发流程
- [常见问题](../troubleshooting/common-issues.md) - 打包相关问题
