# 依赖审计报告

**日期**: 2026-06-02
**工具**: pip-audit 2.10.0, pip list --outdated
**项目**: devlearner-ai v7.0

---

## 1. 依赖变更总览

### 移除的依赖（未使用）

| 包名 | 原因 |
|------|------|
| `requests` | 代码中无任何导入；API 通信使用 stdlib `urllib.request` |
| `Pygments` | 代码中无任何导入；语法高亮使用自定义 `QSyntaxHighlighter` 子类 |

### 版本约束更新

| 包名 | 旧约束 | 新约束 | 原因 |
|------|--------|--------|------|
| `pytest` | `>=8.0` | `>=9.0` | 修复 CVE-2025-71176（需 >=9.0.3） |

---

## 2. 安全漏洞审计

### 项目直接依赖（requirements.txt / pyproject.toml）

pip-audit 对 requirements.txt 的扫描结果：**无已知漏洞**。

移除 `requests` 后，原本潜在的 CVE-2024-47081 和 CVE-2026-25645 不再影响本项目。

### 全局环境发现的漏洞（供参考）

以下漏洞存在于全局 Python 环境中，非本项目直接依赖，但值得关注：

| 包名 | 当前版本 | CVE | 修复版本 |
|------|---------|-----|---------|
| aiohttp | 3.12.4 | CVE-2026-34515 等 19 项 | >=3.13.4 |
| curl-cffi | 0.13.0 | CVE-2026-33752 | >=0.15.0 |
| idna | 3.13 | CVE-2026-45409 | >=3.15 |
| pip | 25.0.1 | CVE-2025-8869 等 4 项 | >=26.1 |
| pytest | 8.4.0 | CVE-2025-71176 | >=9.0.3 |
| python-dotenv | 1.1.0 | CVE-2026-28684 | >=1.2.2 |
| requests | 2.32.3 | CVE-2024-47081, CVE-2026-25645 | >=2.33.0 |
| starlette | 1.0.0 | PYSEC-2026-161 | >=1.0.1 |

---

## 3. 过期包检查

以下为全局环境中与项目相关的过期包：

| 包名 | 当前版本 | 最新版本 | 说明 |
|------|---------|---------|------|
| pytest | 8.4.0 | 9.0.3 | 已通过约束更新修复 |
| ruff | 0.15.13 | 0.15.15 | 小版本更新，可选升级 |
| requests | 2.32.3 | 2.34.2 | 已从项目移除 |
| pip | 25.0.1 | 26.1.2 | 建议全局升级 |

项目核心依赖（PyQt5、mistune、keyring）均在约束范围内，无需更新。

---

## 4. 未使用依赖分析

扫描所有 `.py` 文件的 import 语句后发现：

| 包名 | 在 requirements.txt 中 | 在代码中导入 | 结论 |
|------|----------------------|-------------|------|
| PyQt5 | 是 | 是（多处） | 保留 |
| mistune | 是 | 是（`app/ai/markdown_renderer.py`） | 保留 |
| keyring | 是 | 是（`app/credentials.py`） | 保留 |
| requests | 是 | **否** | **已移除** |
| Pygments | 是 | **否** | **已移除** |

注：`requests` 仅在教程内容文件 `content/python/py_http_api.md` 中作为示例代码出现，不属于项目运行时依赖。

---

## 5. 修改的文件

- `D:\codelearnhleper\requirements.txt` — 移除 requests、Pygments
- `D:\codelearnhleper\pyproject.toml` — 移除 requests、Pygments，pytest 约束升级至 >=9.0
- `D:\codelearnhleper\.github\workflows\security-audit.yml` — 新增 pip-audit CI 工作流

---

## 6. 建议后续操作

1. 运行 `pip install -U pytest>=9.0` 以实际安装修复版本
2. 运行 `pip uninstall requests Pygments` 清理未使用包
3. 全局环境运行 `pip install -U pip` 升级 pip
4. 定期（建议每月）运行 `pip-audit` 检查新漏洞
