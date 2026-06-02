# 构建指南

本文档介绍如何将 DevLearner AI 打包为可独立运行的可执行文件。

---

## 目录

- [构建环境要求](#构建环境要求)
- [快速构建](#快速构建)
- [构建脚本详解](#构建脚本详解)
- [构建产物](#构建产物)
- [自定义构建配置](#自定义构建配置)
- [常见构建问题](#常见构建问题)
- [发布流程](#发布流程)

---

## 构建环境要求

| 要求 | 说明 |
|------|------|
| Python | 3.9+（推荐 3.12） |
| PyInstaller | 最新版 |
| 操作系统 | Windows（构建 Windows 可执行文件） |
| 依赖 | 所有运行时依赖已安装 |

---

## 快速构建

### 安装 PyInstaller

```bash
pip install pyinstaller
```

### 执行构建

```bash
python scripts/build/build_dev_exe.py
```

构建完成后，可执行文件输出到 `dist/` 目录。

---

## 构建脚本详解

构建脚本位于 `scripts/build/build_dev_exe.py`，主要执行以下操作：

1. **清理旧的构建产物** -- 删除 `build/` 和 `dist/` 目录中的旧文件
2. **调用 PyInstaller** -- 使用项目中的 `.spec` 文件进行打包
3. **复制资源文件** -- 确保课程内容、样式等资源被正确包含
4. **输出结果** -- 生成的可执行文件位于 `dist/` 目录

### PyInstaller 配置

项目包含预配置的 `.spec` 文件，定义了：

| 配置项 | 说明 |
|--------|------|
| 入口文件 | `main.py` |
| 包含的数据 | `content/` 目录、`styles/` 目录 |
| 隐藏导入 | 需要但 PyInstaller 未自动检测的模块 |
| 排除模块 | 不需要包含的模块 |
| 控制台模式 | 是否显示控制台窗口 |

---

## 构建产物

### 输出目录

```
dist/
└── DevLearnerAI/
    ├── DevLearnerAI.exe     # 主可执行文件
    ├── _internal/           # 运行时依赖
    │   ├── python3x.dll
    │   ├── PyQt5/
    │   ├── content/         # 课程内容
    │   └── ...
    └── ...
```

### 文件大小

典型的构建产物大小约为 100-200MB，包含：
- Python 解释器
- PyQt5 运行时
- 课程内容文件
- 其他依赖库

### 分发方式

- **文件夹分发** -- 将 `dist/DevLearnerAI/` 整个文件夹打包分发
- **ZIP 压缩** -- 压缩后分发，用户解压后即可运行
- **安装程序** -- 可使用 NSIS 或 Inno Setup 创建安装程序

---

## 自定义构建配置

### 修改应用名称

在 `.spec` 文件中修改 `name` 参数：

```python
exe = EXE(
    ...
    name='DevLearnerAI',
    ...
)
```

### 添加图标

在 `.spec` 文件中设置 `icon` 参数：

```python
exe = EXE(
    ...
    icon='path/to/icon.ico',
    ...
)
```

### 包含额外文件

在 `.spec` 文件的 `datas` 列表中添加：

```python
a = Analysis(
    ...
    datas=[
        ('content', 'content'),
        ('styles', 'styles'),
        ('额外目录', '目标目录'),
    ],
    ...
)
```

### 隐藏导入

如果运行时出现模块找不到的错误，在 `.spec` 文件的 `hiddenimports` 中添加：

```python
a = Analysis(
    ...
    hiddenimports=[
        'some_module',
        'another_module',
    ],
    ...
)
```

---

## 常见构建问题

### 运行时报模块找不到

**问题**：可执行文件运行时报 `ModuleNotFoundError`

**解决**：在 `.spec` 文件的 `hiddenimports` 中添加缺失的模块。

### 课程内容找不到

**问题**：应用启动后课程内容为空

**解决**：
1. 确认 `.spec` 文件的 `datas` 中包含 `content` 目录
2. 确认 `config.py` 中的资源目录查找逻辑能正确定位到打包后的路径

### 文件过大

**问题**：构建产物文件过大

**解决**：
1. 使用 `--exclude-module` 排除不需要的模块
2. 删除不必要的大型资源文件
3. 使用 UPX 压缩（在 `.spec` 中设置 `upx=True`）

### 杀毒软件误报

**问题**：可执行文件被杀毒软件标记

**解决**：
1. 这是 PyInstaller 打包的常见问题
2. 使用代码签名证书对可执行文件签名
3. 向杀毒软件厂商提交误报

---

## 发布流程

### 版本管理

版本号统一管理在 `pyproject.toml` 中：

```toml
[project]
name = "devlearner-ai"
version = "7.0"
```

应用启动时通过 `importlib.metadata` 读取版本号。

### GitHub Actions 自动发布

项目配置了 GitHub Actions 工作流（`.github/workflows/release.yml`），在创建新的 Git tag 时自动构建和发布：

```bash
# 创建 tag
git tag v7.0
git push origin v7.0
```

### 手动发布步骤

1. 更新 `pyproject.toml` 中的版本号
2. 更新 `CHANGELOG.md`
3. 提交并推送
4. 创建 Git tag
5. 运行构建脚本
6. 上传构建产物到 GitHub Releases

---

> 返回：[开发者指南目录](architecture.md)
