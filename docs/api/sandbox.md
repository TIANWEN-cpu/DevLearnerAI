# Python 沙箱安全模型文档

本文档描述 `app.python_runner` 模块的安全机制，包括多层防护、允许/禁止操作和逃逸防护。

---

## 安全架构概述

沙箱采用**纵深防御**策略，包含以下安全层：

```
用户代码
  |
  v
[1] AST 预检 ─── 静态分析，阻止危险模式
  |
  v
[2] 子进程隔离 ─── multiprocessing / subprocess 独立进程
  |
  v
[3] 受限内置函数 ─── 白名单制，仅暴露安全函数
  |
  v
[4] 受限 import ─── 仅允许白名单模块
  |
  v
[5] 文件系统沙箱 ─── 临时目录隔离，目录逃逸检测
  |
  v
[6] 输出限制 ─── stdout 截断，防止内存滥用
  |
  v
[7] 超时控制 ─── 强制终止超时执行
```

---

## 第 1 层: AST 预检

在代码执行前，通过 `ast.parse()` 对源代码进行静态分析。

### 阻止的危险属性访问

以下双下划线属性被禁止访问：

**内省与逃逸相关**:
- `__class__`, `__bases__`, `__mro__`, `__subclasses__` -- 类型链遍历
- `__globals__`, `__code__` -- 函数全局变量和代码对象访问
- `__builtins__` -- 内置函数字典访问
- `__import__`, `__loader__`, `__spec__` -- 导入机制钩子
- `__file__`, `__name__`, `__module__` -- 模块元信息

**协议方法**（全部阻止，防止通过特殊方法逃逸）:
- 所有比较方法 (`__lt__`, `__eq__` 等)
- 所有算术方法 (`__add__`, `__mul__` 等)
- 所有容器方法 (`__getitem__`, `__iter__` 等)
- 所有上下文管理器方法 (`__enter__`, `__exit__`)
- 所有异步方法 (`__await__`, `__aiter__` 等)

### 阻止的函数调用

| 函数 | 阻止原因 |
|------|----------|
| `eval()` | 执行任意表达式 |
| `exec()` | 执行任意代码 |
| `compile()` | 编译代码对象 |
| `breakpoint()` | 进入调试器 |
| `getattr()` | 动态属性访问（含双下划线属性时） |
| `hasattr()` | 属性探测 |
| `delattr()`, `setattr()` | 属性修改 |
| `type()` | 动态类型创建 |
| `object()` | 基类实例化 |
| `super()` | 超类访问 |
| `dir()`, `vars()` | 内省 |
| `globals()`, `locals()` | 作用域泄露 |
| `memoryview()`, `bytearray()` | 内存直接访问 |

### 阻止的字符串模式

源代码中的字符串字面量不得包含：
- `"__builtins__"`
- `"__import__"`

防止通过 `getattr` + 字符串拼接绕过属性名检查。

### 阻止的 import 语句

所有 `import` 和 `from ... import` 语句被阻止。沙箱通过受限的 `__import__` 替代品提供有限的模块访问。

---

## 第 2 层: 子进程隔离

代码在独立子进程中执行，支持两种模式：

### multiprocessing 模式（默认）

- 使用 `spawn` 上下文创建全新进程（不继承父进程内存）
- 通过 `Pipe` 传递结果
- 超时时先 `terminate()`，再 `kill()`

### subprocess 回退模式

当无法使用 multiprocessing 时（如交互式环境），回退到 subprocess：
- 通过 JSON payload 文件传递参数
- 启动新的 Python 解释器进程
- 通过 stdout 传递 JSON 结果

### 超时设置

| 操作 | 默认超时 |
|------|----------|
| 代码执行 | 3 秒 |
| 代码评测 | 4 秒 |

超时后进程被强制终止，返回超时错误。

---

## 第 3 层: 受限内置函数

沙箱仅暴露以下安全的内置函数：

**数据类型**: `int`, `float`, `str`, `bool`, `list`, `dict`, `tuple`, `set`
**迭代工具**: `range`, `sorted`, `enumerate`, `zip`, `map`, `filter`, `reversed`
**数学函数**: `sum`, `min`, `max`, `abs`, `round`
**判断函数**: `isinstance`, `all`, `any`
**输出**: `print`
**长度**: `len`
**异常类型**: `Exception`, `TypeError`, `ValueError`

`open()` 被替换为受限版本（见第 5 层）。

**不提供的内置函数**（与阻止列表一致）: `eval`, `exec`, `compile`, `type`, `object`, `super`, `getattr`, `setattr`, `delattr`, `hasattr`, `dir`, `vars`, `globals`, `locals`, `memoryview`, `bytearray`, `breakpoint` 等。

---

## 第 4 层: 受限 import

通过替换 `__import__` 函数实现模块白名单：

### 允许的模块

```
argparse    collections   datetime    functools
itertools   json          logging     math
pathlib     re            statistics
```

### 禁止的模块（示例）

以下模块不可导入：
- `os`, `sys`, `subprocess` -- 系统操作
- `socket`, `http`, `urllib` -- 网络访问
- `ctypes`, `signal` -- 底层系统接口
- `importlib` -- 动态导入
- `pickle`, `shelve` -- 序列化（可能执行代码）
- `threading`, `multiprocessing` -- 并发控制
- `io`, `tempfile` -- 文件系统操作（除受限 open 外）

---

## 第 5 层: 文件系统沙箱

### 工作目录隔离

- 每次执行创建独立的临时目录（前缀 `devlearner-run-` 或 `devlearner-eval-`）
- 执行期间 `os.chdir()` 切换到临时目录
- 执行完毕后恢复原始工作目录并删除临时目录

### 受限 open() 函数

替换标准 `open()` 函数，实现目录逃逸检测：

```python
# 允许：访问临时工作目录内的文件
open("data.txt", "r")           # OK: 相对路径，解析到临时目录
open("./subdir/file.txt", "w")  # OK: 子目录

# 禁止：目录逃逸
open("/etc/passwd", "r")        # ERROR: 绝对路径，不在工作目录内
open("../../secret.txt", "r")   # ERROR: 解析后逃出工作目录
```

**校验逻辑**:
1. 解析目标路径为绝对路径（使用 `Path.resolve()`）
2. 检查解析后的路径是否在工作目录内
3. 不在工作目录内则抛出 `PermissionError`

**写操作支持**: 为 `a`, `w`, `x`, `+` 模式自动创建父目录。

---

## 第 6 层: 输出限制

`LimitedBuffer` 类替代标准 `io.StringIO`：

- 最大写入量：**12000 字节**
- 超过限制时抛出 `RuntimeError("标准输出过长，已被截断。")`
- 防止用户代码通过无限输出导致内存耗尽

---

## 第 7 层: 超时控制

详见第 2 层"子进程隔离"中的超时设置。超时后：
1. 发送 `SIGTERM` 信号
2. 等待 2 秒
3. 如仍存活则 `SIGKILL`
4. 返回超时错误结果

---

## 评测评分模型

Python 代码评测采用 5 维评分：

| 维度 | 分值 | 说明 |
|------|------|------|
| 语法检查 | 20 | `ast.parse()` 成功 |
| 代码结构 | 20 | 期望的 AST 节点类型全部存在 |
| 执行成功 | 10 | 代码在沙箱中无异常执行 |
| 对象定义 | 10 | 期望的名称全部在命名空间中 |
| 测试用例 | 40 | 通过比例计分 |

**通过条件**: 总分 >= 70 且所有测试用例通过 且无缺失结构 且无缺失名称。

---

## 限制与已知边界

1. **非绝对安全**: Python 沙箱难以做到 100% 安全。当前防护覆盖了常见逃逸路径，但不排除存在未知的绕过方式。
2. **性能开销**: 子进程模式比直接执行慢约 50-200ms，但换来进程级隔离。
3. **内存限制**: 依赖操作系统的进程内存限制，沙箱本身不设额外内存上限。
4. **网络隔离**: 未在沙箱层面禁用网络（但已禁止导入网络相关模块）。
5. **时间限制**: 超时精度受系统调度影响，实际可能略超设定值。
