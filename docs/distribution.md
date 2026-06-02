# 构建与发布指南

## 概述

DevLearnerAI 使用 PyInstaller 打包为 Windows 可执行文件。项目提供三个构建变体：

| 变体 | 入口文件 | 输出名称 | 说明 |
|------|----------|----------|------|
| `release` | `main.py` | `DevLearnerAI_{version}.exe` | 正式发布版，包含完整功能 |
| `dev` | `dev_main.py` | `DevLearnerAI_{version}_dev.exe` | 开发调试版，DEBUG 日志级别 |
| `codex` | `codex_switcher_main.py` | `CodexAccountSwitcher.exe` | Codex 账号切换器（独立工具） |

## 环境准备

### 安装依赖

```bash
# 安装项目依赖（含开发和构建工具）
pip install -e ".[dev]"

# 或仅安装构建依赖
pip install -e ".[build]"
```

### 系统要求

- Python 3.9 - 3.12
- Windows 10/11（PyInstaller 仅支持当前操作系统打包）
- UPX（可选，用于压缩可执行文件体积）

## 本地构建

### 使用统一构建脚本

```bash
# 构建正式发布版
python scripts/build/build.py --variant release

# 构建开发版（清理旧产物）
python scripts/build/build.py --variant dev --clean

# 构建 Codex 切换器（禁用 UPX 压缩）
python scripts/build/build.py --variant codex --no-upx

# 仅生成 .spec 文件，不执行打包（调试用）
python scripts/build/build.py --variant release --dry-run
```

### 使用 Makefile

```bash
make build-release   # 打包正式发布版
make build-dev       # 打包开发调试版
make build-codex     # 打包 Codex 账号切换器
```

### 输出位置

构建产物位于 `dist/` 目录：

```
dist/
  DevLearnerAI_1.1.0.exe         # release 变体
  DevLearnerAI_1.1.0_dev.exe     # dev 变体
  CodexAccountSwitcher.exe        # codex 变体
```

## 版本管理

版本号以 `pyproject.toml` 中的 `version` 字段为唯一来源。`app/config.py` 在开发模式下通过 `importlib.metadata` 读取，在 PyInstaller 打包后使用回退值。

### 查看当前版本

```bash
python scripts/version_bump.py show
```

### 版本递增

```bash
python scripts/version_bump.py patch    # 1.1.0 -> 1.1.1
python scripts/version_bump.py minor    # 1.1.0 -> 1.2.0
python scripts/version_bump.py major    # 1.1.0 -> 2.0.0
python scripts/version_bump.py set 2.0.0   # 指定版本号
```

版本提升脚本会同步更新：
- `pyproject.toml` 中的 `version` 字段
- `app/config.py` 中的回退版本号

### 发布流程

```bash
# 1. 递增版本号
python scripts/version_bump.py minor

# 2. 提交并打标签
git add -A
git commit -m "release: v1.2.0"
git tag v1.2.0

# 3. 推送触发 GitHub Actions 自动构建
git push origin main --tags
```

## CI/CD

### 持续集成（ci.yml）

触发条件：推送到 `main`/`master` 分支或发起 PR。

- **lint** -- ruff 代码风格检查
- **test** -- pytest 测试（Python 3.9 + 3.12 矩阵）

### 自动发布（release.yml）

触发条件：推送 `v*` 标签。

流程：
1. 在 Windows 环境并行构建三个变体
2. 上传构建产物为 GitHub Actions Artifact
3. 创建 GitHub Release，附带所有 `.exe` 文件
4. 自动从 `CHANGELOG.md` 提取发布说明

## PyInstaller .spec 文件

构建脚本会自动生成 `.spec` 文件。每个变体包含：

- **Hidden imports** -- 显式声明需要打包的内部模块
- **Data files** -- `content/` 和 `app/` 目录（视变体而定）
- **Collect all** -- pygments、mistune 的完整包收集
- **Excludes** -- 排除不必要的大型包（tkinter、matplotlib 等）
- **UPX compression** -- 启用压缩减小体积（可通过 `--no-upx` 禁用）
- **Windowed mode** -- 无控制台窗口

## 常见问题

### 打包后运行报错 "ModuleNotFoundError"

在 `scripts/build/build.py` 的 `VARIANTS` 字典中对应变体的 `hidden_imports` 列表里添加缺失模块。

### 打包体积过大

1. 确保 UPX 已安装并在 PATH 中
2. 在 `VARIANTS` 的 `excludes` 列表中添加不需要的包
3. 检查 `content/` 目录是否有非必要文件

### 版本号不一致

运行 `python scripts/version_bump.py show` 检查。如需修复，使用 `python scripts/version_bump.py set <version>` 手动设置。

---

## 参见 (See Also)

- [构建可执行文件](guides/building.md) - 更详细的 PyInstaller 打包指南
- [开发工作流](guides/development.md) - 日常开发流程和分支策略
- [测试指南](guides/testing.md) - 运行测试和覆盖率管理
- [快速开始](guides/getting-started.md) - 开发环境搭建
