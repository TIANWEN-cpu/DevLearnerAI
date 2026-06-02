# ADR-002: 代码执行沙箱方案

## 状态

已采纳

## 背景

DevLearnerAI 的练习评测需要安全执行用户提交的代码。用户群体为编程初学者，代码可能包含：

- 死循环或长时间运行的代码
- 文件系统访问（可能破坏系统文件）
- 恶意代码尝试（如 `os.system("rm -rf /")`）
- 尝试逃逸沙箱（如通过 `__class__.__bases__` 链访问系统模块）

## 决策

采用 **AST 静态分析 + 受限内置函数 + 进程隔离 + 超时控制** 的多层防御方案。

## 理由

### 备选方案对比

| 方案 | 说明 | 优缺点 |
|------|------|--------|
| **A: AST + 受限环境 + 子进程** (采纳) | 多层防护，深度防御 | 安全性高，实现复杂度中等 |
| B: Docker 容器隔离 | 每次执行启动 Docker 容器 | 安全性最高，但依赖 Docker，启动慢 |
| C: WebAssembly (Pyodide) | 在浏览器沙箱中执行 | 受限于浏览器能力，库支持有限 |
| D: 仅限制内置函数 | 只替换 __builtins__ | 容易被 __class__ 链绕过 |
| E: 操作系统沙箱 (seccomp) | Linux 系统调用过滤 | 不支持 Windows |

### 选择方案 A 的理由

1. **零外部依赖**: 不依赖 Docker、浏览器或其他系统工具，仅使用 Python 标准库（`ast`、`multiprocessing`、`tempfile`）。

2. **多层防御**: 即使某一层被绕过，其他层仍能提供保护：
   - AST 预检：在代码执行前就拦截危险模式
   - 受限内置函数：移除 `eval`、`exec`、`__import__` 等
   - 进程隔离：子进程崩溃不影响主进程
   - 超时控制：防止死循环
   - 输出限制：防止内存滥用

3. **启动速度**: 子进程使用 `multiprocessing.spawn` 创建，启动开销远低于 Docker 容器。

4. **跨平台**: 在 Windows、macOS、Linux 上均可工作。

5. **可扩展**: 新增语言支持时，可以复用进程隔离和超时控制框架。

## 实现细节

### 防御层次

```text
用户代码 → AST 预检 → 受限 __builtins__ → 子进程执行 → 超时控制
              │              │                  │            │
              ▼              ▼                  ▼            ▼
          拦截 eval       移除 os          Pipe 通信      terminate()
          拦截 import    受限 open()      隔离命名空间    kill() 回退
          拦截 __class__  白名单 import   临时目录
```

### AST 预检覆盖的攻击向量

| 攻击向量 | 拦截方式 |
|---------|---------|
| `eval("os.system('...')")` | 拦截 `eval` 函数调用 |
| `import os` | 拦截 `import` 语句 |
| `().__class__.__bases__[0].__subclasses__()` | 拦截 `__class__`、`__bases__`、`__subclasses__` 属性 |
| `getattr(x, "__builtins__")` | 拦截 `getattr` 对双下划线属性的字符串参数 |
| `"__builtins__" in "..."` | 拦截包含敏感双下划线的字符串常量 |
| `type(obj)(...)` | 拦截 `type` 函数调用 |

### 回退机制

当无法使用 `multiprocessing`（如在交互式环境中）时，回退到 `subprocess` 方案：

```python
def _should_use_subprocess_fallback() -> bool:
    main_file = getattr(sys.modules.get("__main__"), "__file__", "")
    return not main_file or str(main_file).startswith("<")
```

subprocess 方案通过 JSON 文件传递参数，以独立 Python 进程执行代码。

## 影响

### 正面影响

- 沙箱测试覆盖了所有已知攻击向量
- 用户代码的执行结果对主进程完全透明
- 超时机制防止了 UI 卡死
- 输出限制防止了内存滥用

### 负面影响

- 子进程启动有一定延迟（约 100-300ms）
- 部分合法代码被误拦截（如 `import` 语句被禁止，但允许通过白名单的模块）
- 沙箱限制了部分 Python 功能（如 `open()` 只能访问临时目录）

### 缓解措施

- 使用 `ALLOWED_IMPORTS` 白名单允许常用标准库
- `open()` 替换为受限版本，允许在临时目录中进行文件操作
- 评测评分结构（语法 20 + 结构 20 + 执行 10 + 对象 10 + 测试 40）为部分失败保留了得分空间

## 相关文档

- [安全模型](../concepts/security-model.md) - 沙箱安全详情
- [沙箱问题排查](../troubleshooting/sandbox-issues.md) - 常见问题
