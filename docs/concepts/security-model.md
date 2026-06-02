# 安全模型

本文档描述 DevLearnerAI 的多层安全防护体系，包括代码执行沙箱、凭证管理、数据传输安全和 XSS 防护。

---

## 安全架构总览

```text
┌──────────────────────────────────────────────────────────┐
│                    用户输入层                              │
│  练习代码 / AI 消息 / 课程内容 / API 密钥                   │
└──────────────┬───────────────────────────────────────────┘
               │
    ┌──────────┼──────────┬──────────┬──────────┐
    ▼          ▼          ▼          ▼          ▼
┌────────┐┌────────┐┌────────┐┌────────┐┌────────┐
│ 代码   ││ 凭证   ││ 传输   ││  输出   ││  XSS   │
│ 沙箱   ││ 存储   ││ 安全   ││  限制   ││  防护   │
│        ││        ││        ││        ││        │
│ AST    ││WCM/    ││HTTPS   ││12KB    ││白名单  │
│ 预检   ││keyring ││+TLS    ││stdout  ││HTML    │
│ 进程   ││Base64  ││证书    ││3s 超时 ││净化    │
│ 隔离   ││回退    ││验证    ││        ││        │
└────────┘└────────┘└────────┘└────────┘└────────┘
```

---

## 1. 代码执行沙箱

### 架构

代码执行沙箱位于 `app/python_runner.py`，提供多层防护：

```text
用户代码输入
    │
    ▼
┌───────────────────────────────┐
│ 第 1 层: AST 静态分析预检      │
│ - 拦截 import 语句             │
│ - 拦截危险内置函数调用          │
│ - 拦截双下划线属性访问          │
│ - 拦截危险字符串常量            │
└──────────────┬────────────────┘
               ▼
┌───────────────────────────────┐
│ 第 2 层: 受限内置函数环境       │
│ - SAFE_BUILTINS 白名单         │
│ - 受限 open() (临时目录内)     │
│ - 受限 __import__ (模块白名单)  │
└──────────────┬────────────────┘
               ▼
┌───────────────────────────────┐
│ 第 3 层: 进程隔离              │
│ - multiprocessing.spawn       │
│ - Pipe 通信                   │
│ - 超时 terminate → kill       │
└──────────────┬────────────────┘
               ▼
┌───────────────────────────────┐
│ 第 4 层: 输出限制              │
│ - LimitedBuffer (12KB 上限)   │
│ - 临时工作目录自动清理          │
└───────────────────────────────┘
```

### AST 静态分析

`_validate_code_safety()` 函数解析代码的 AST，检查以下危险模式：

```python
# 拦截的危险属性
_DANGEROUS_ATTRS = frozenset({
    "__class__", "__bases__", "__subclasses__", "__mro__",
    "__builtins__", "__globals__", "__code__", "__import__",
    "__loader__", "__spec__", "__file__", "__name__",
    # ... 更多双下划线属性
})

# 拦截的危险内置函数
_DANGEROUS_BUILTINS_CALLS = frozenset({
    "eval", "exec", "compile", "breakpoint",
    "getattr", "hasattr", "delattr", "setattr",
    "type", "object", "super", "dir", "vars",
    "globals", "locals", "memoryview", "bytearray",
})
```

检查规则：

| 检查项 | 规则 | 示例 |
|--------|------|------|
| `import` 语句 | 全部拦截 | `import os` → SyntaxError |
| `eval()`/`exec()` | 全部拦截 | `eval("1+1")` → SyntaxError |
| `__class__` 等 | 属性和调用均拦截 | `obj.__class__` → SyntaxError |
| `getattr` + 双下划线 | 字符串参数检查 | `getattr(x, "__builtins__")` → SyntaxError |
| 危险字符串常量 | 含 `__builtins__` 的字符串 | `"__builtins__"` → SyntaxError |

### 受限内置函数

```python
SAFE_BUILTINS = {
    "print": print, "len": len, "range": range,
    "int": int, "float": float, "str": str, "bool": bool,
    "list": list, "dict": dict, "tuple": tuple, "set": set,
    "sorted": sorted, "enumerate": enumerate, "zip": zip,
    "map": map, "filter": filter,
    "sum": sum, "min": min, "max": max, "abs": abs, "round": round,
    "isinstance": isinstance, "all": all, "any": any,
    "reversed": reversed,
    "Exception": Exception, "TypeError": TypeError, "ValueError": ValueError,
}
```

不允许使用的内置函数包括：`eval`、`exec`、`compile`、`open`（被替换为受限版本）、`__import__`（被替换为白名单版本）。

### 模块白名单

```python
ALLOWED_IMPORTS = {
    "argparse", "collections", "datetime", "functools",
    "itertools", "json", "logging", "math", "pathlib",
    "re", "statistics",
}
```

### 文件系统隔离

```python
def _safe_open_factory(workdir: Path):
    def _safe_open(file, mode="r", *args, **kwargs):
        target = Path(file)
        resolved = (workdir / target).resolve() if not target.is_absolute() else target.resolve()

        # 防止目录逃逸
        if workdir != resolved and workdir not in resolved.parents:
            raise PermissionError("练习环境只允许访问临时工作目录内的文件。")
        return open(resolved, mode, *args, **kwargs)
    return _safe_open
```

### 进程隔离

代码在 `multiprocessing.spawn` 创建的子进程中执行：

```python
def _run_with_timeout(target, mode, args, timeout_sec):
    ctx = mp.get_context("spawn")
    parent_conn, child_conn = ctx.Pipe(duplex=False)
    process = ctx.Process(target=target, args=(child_conn, *args))
    process.start()

    if parent_conn.poll(timeout_sec):
        return parent_conn.recv()
    else:
        process.terminate()   # 先尝试优雅终止
        process.join(2)
        if process.is_alive():
            process.kill()    # 强制终止
```

---

## 2. 凭证安全存储

### 存储策略

凭证管理模块 (`app/credentials.py`) 实现三级回退策略：

```text
优先级 1: Windows Credential Manager (加密存储)
    │
    ├── 通过 ctypes 调用 Advapi32.dll 的 CredWriteW / CredReadW
    ├── 数据以 UTF-16-LE 编码存储
    ├── 持久化方式: CRED_PERSIST_LOCAL_MACHINE
    └── 仅 Windows 平台可用
    │
优先级 2: keyring 后端
    │
    ├── 依赖 keyring 库（>=24.0）
    ├── 支持 macOS Keychain、Linux Secret Service 等
    └── 非 Windows 平台的推荐方案
    │
优先级 3: Base64 编码文件回退
    │
    ├── 存储路径: ~/.devlearnerai/api_key.txt
    ├── 编码方式: Base64（非加密，仅混淆）
    └── 最低安全级别，适用于无 keyring 环境
```

### API 接口

```python
# 保存密钥
save_secret(target: str, secret: str, username: str = "DevLearnerAI")

# 读取密钥
load_secret(target: str) -> Optional[str]

# 删除密钥
delete_secret(target: str) -> bool
```

### 旧版密钥迁移

系统自动将旧版数据库中的明文 API 密钥迁移到安全存储：

```python
def _migrate_legacy_api_key_if_needed(self):
    row = self.fetchone("SELECT host, api_key, key_alias, model FROM mentor_api_config WHERE id = 1")
    if row:
        host, legacy_api_key, key_alias, model = row
        if legacy_api_key and not key_alias:  # 有明文密钥但未迁移
            save_secret(API_CREDENTIAL_ALIAS, legacy_api_key)
            # 将数据库中的密钥字段清空
```

---

## 3. 传输安全

### HTTPS 强制

所有 AI API 通信强制使用 HTTPS：

```python
def require_https(host: str) -> None:
    if not host.lower().startswith("https://"):
        raise ValueError("出于安全考虑，仅允许 HTTPS 连接。请将 API Host 改为 https:// 开头的地址。")
```

### SSL 证书验证

```python
def create_ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()  # 启用完整的证书链验证
```

---

## 4. XSS 防护

### HTML 净化

`app/ai/markdown_renderer.py` 实现了基于白名单的 HTML 净化器。

**白名单标签**：

```python
ALLOWED_TAGS = frozenset({
    "p", "br", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "code", "pre", "strong", "em", "b", "i",
    "a", "blockquote", "table", "tr", "td", "th", "thead", "tbody",
    "hr", "span",
})

STRIP_TAGS = frozenset({"script", "style", "iframe", "object", "embed"})
```

**属性过滤规则**：

| 标签 | 允许的属性 | 说明 |
|------|-----------|------|
| `<a>` | `href`（仅 http/https/相对路径） | 移除 javascript: / data: / vbscript: |
| `<span>` | `class` | 用于代码语法高亮 |
| 其他 | 无 | 移除所有属性 |

**事件处理器过滤**：

```python
RE_EVENT_ATTR = re.compile(r"^on", re.IGNORECASE)           # onclick, onerror...
RE_JAVASCRIPT_URI = re.compile(r"^\s*javascript\s*:", re.IGNORECASE)
RE_DATA_URI = re.compile(r"^\s*data\s*:", re.IGNORECASE)
RE_VBSCRIPT_URI = re.compile(r"^\s*vbscript\s*:", re.IGNORECASE)
```

---

## 5. 输出限制

### 标准输出限制

`LimitedBuffer` 类限制代码执行的输出大小为 12KB：

```python
class LimitedBuffer(io.StringIO):
    def __init__(self, limit: int = 12000):
        super().__init__()
        self.limit = limit

    def write(self, data):
        remaining = self.limit - self.tell()
        if remaining <= 0:
            raise RuntimeError("标准输出过长，已被截断。")
```

### 超时控制

| 场景 | 超时 | 说明 |
|------|------|------|
| 代码执行 | 3 秒 | `run_python_code(timeout_sec=3)` |
| 代码评测 | 4 秒 | `evaluate_python_code(timeout_sec=4)` |
| AI API 连接测试 | 20 秒 | `test_connection()` |
| AI API 模型列表 | 30 秒 | `fetch_models()` |
| AI API 聊天请求 | 90 秒 | `send_chat()` / `send_chat_stream()` |

---

## 6. 数据库安全

### WAL 模式

```python
conn.execute("PRAGMA journal_mode = WAL")   # 预写日志模式
conn.execute("PRAGMA foreign_keys = ON")     # 外键约束
```

### 写操作锁

所有写操作通过全局锁保护：

```python
_db_lock = threading.Lock()

@contextmanager
def connect(self):
    _db_lock.acquire()
    conn = get_connection(str(self.db_path))
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        _db_lock.release()
```

---

## 安全检查清单

开发者在修改安全相关代码时，应确认以下项目：

- [ ] 沙箱中不允许新增 `__import__` 或 `eval`/`exec` 到白名单
- [ ] 新增的内置函数不具有文件系统或网络访问能力
- [ ] HTML 净化白名单不包含 `script`、`iframe` 等标签
- [ ] API 通信不支持 HTTP 降级
- [ ] 凭证数据不明文存储在配置文件或数据库中
- [ ] 新的数据库表都使用了适当的索引

---

## 相关文档

- [沙箱问题排查](../troubleshooting/sandbox-issues.md) - 沙箱相关故障排除
- [ADR-002: 沙箱方案](../adr/002-sandbox-approach.md) - 沙箱设计决策
- [API 集成参考](../reference/api-integration.md) - API 通信详情
