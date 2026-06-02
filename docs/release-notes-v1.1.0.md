# DevLearnerAI v1.1.0 发布说明

**发布日期**: 2026-06-02

## 概述

v1.1.0 是 DevLearnerAI 的首个重要版本升级，基于 v1.0.0 进行了全面的成熟度改造。本次更新聚焦于架构重构、测试覆盖、工程化改进和文档完善，不引入新的用户功能，但大幅提升了代码质量、可维护性和开发体验。

## 亮点

### 架构重构

将两个超 1200 行的巨型模块拆分为职责清晰的子包：

- `ai_mentor.py` (1230 行) -> `app/ai/` 包（api_client / chat_handler / markdown_renderer / models）
- `practice_service.py` (1301 行) -> `app/practice/` 包（evaluator / exercise_loader / models / normalizer）

所有拆分均保持向后兼容，外部调用方式不变。

### 测试覆盖

测试用例从 v1.0.0 的 0 条增长至 **1000+** 条，覆盖：

| 模块 | 测试文件数 | 覆盖范围 |
|------|-----------|---------|
| python_runner（沙箱） | 4 | 安全边界、subprocess、扩展场景 |
| database | 5 | CRUD、扩展场景、覆盖率、压力测试 |
| practice_service（评测） | 3 | 评测逻辑、扩展场景 |
| AI 模块 | 5 | chat_handler、API 包、客户端扩展、渲染器 |
| 内容与凭证 | 3 | 内容服务、扩展场景、凭证存储 |
| 集成测试 | 4 | 学习流、练习流、数据库流、AI 流 |
| 安全测试 | 1 | 沙箱逃逸攻击 |
| 边界条件 | 4 | 边界用例、内容解析、评测扩展、加载器扩展 |
| 配置 | 1 | 配置扩展 |

### 工程化工具链

- **Ruff** -- 替代 flake8 + isort + black，统一 lint + format
- **Makefile** -- 一键 lint / format / test / coverage / build / verify-build
- **pyproject.toml** -- 统一声明项目元数据、工具配置和可选依赖
- **GitHub Actions CI** -- Python 3.9 + 3.12 矩阵，lint + test + coverage（最低 40%）

### 构建系统

旧版三个独立构建脚本（`build_exe.py`、`build_dev_exe.py`、`build_codex_switcher_exe.py`）整合为 `scripts/build/build.py`：

```bash
python scripts/build/build.py --variant release       # 正式版
python scripts/build/build.py --variant dev --clean    # 开发版
python scripts/build/build.py --variant codex --no-upx # Codex 切换器
python scripts/build/build.py --variant release --dry-run  # 验证配置
```

构建脚本自动从 `pyproject.toml` 读取版本号并生成 `.spec` 文件。

### 版本管理

版本号统一为单一来源（`pyproject.toml` 的 `version` 字段）：

- `app/config.py` 通过 `importlib.metadata` 动态读取，PyInstaller 环境下使用回退值
- `scripts/build/build.py` 构建时同步读取
- `scripts/version_bump.py` 支持 patch / minor / major 递增和手动设置

## 安全加固

- 移除 `getattr` 白名单中的潜在逃逸路径
- 增强 AST 校验覆盖
- 新增 `test_security_sandbox_escape.py` 专项测试

## Bug 修复

- 修复数据库事务异常时未提交的问题
- 修复 widget 销毁后信号发射的线程安全问题
- 移除 CI 中未使用的 import 和格式化问题
- 清理根目录冗余的构建脚本

## 文档

| 文档 | 说明 |
|------|------|
| CHANGELOG.md | Keep a Changelog 规范的版本变更历史 |
| CONTRIBUTING.md | 贡献指南（开发环境、分支策略、PR 流程、代码规范） |
| docs/improvement-plan.md | 改进路线图 |
| docs/maturity-plan.md | 成熟度计划 |
| docs/distribution.md | 构建与发布指南 |

## 升级指南

从 v1.0.0 升级到 v1.1.0 无需任何操作变更。所有内部模块拆分均保持向后兼容：

```python
# 以下导入方式仍然有效
from app.practice_service import evaluate_python
from app.ai_mentor import AIMentorPanel  # 如果使用了兼容 shim
```

## 已知问题

无已知回归问题。

## 下一步

v1.2.0 计划包括：
- 启动性能优化（splash screen + 延迟加载）
- 数据库 PRAGMA 调优和 ANALYZE
- AI 请求超时和重试机制
- 内存监控和缓存管理
