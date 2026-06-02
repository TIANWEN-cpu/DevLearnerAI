# DevLearner AI -- 高级安全审计报告

**审计日期:** 2026-06-02
**审计范围:** D:\codelearnhleper 全部 Python 源码
**审计方法:** 静态代码分析 + 已有测试套件审查

---

## 1. 沙箱渗透测试 (Python Sandbox)

### 1.1 已阻断的攻击向量

| 攻击技术 | 状态 | 防御层 |
|---|---|---|
| `__class__.__bases__` 链式遍历 | 已阻断 | AST 预检 (`_DANGEROUS_ATTRS`) |
| `type()` 重建攻击 | 已阻断 | `_DANGEROUS_BUILTINS_CALLS` |
| `import` 语句 | 已阻断 | AST `Import/ImportFrom` 检查 |
| `eval()` / `exec()` / `compile()` | 已阻断 | `_DANGEROUS_BUILTINS_CALLS` |
| `__builtins__` / `__import__` 字符串引用 | 已阻断 | AST 常量字符串检查 |
| `getattr(obj, '__dunder__')` 间接访问 | 已阻断 | AST 参数字符串检查 |
| `setattr` / `delattr` / `dir` / `vars` / `globals` / `locals` | 已阻断 | `_DANGEROUS_BUILTINS_CALLS` |
| `breakpoint()` | 已阻断 | `_DANGEROUS_BUILTINS_CALLS` |
| `bytearray` / `memoryview` | 已阻断 | `_DANGEROUS_BUILTINS_CALLS` |
| 文件系统路径逃逸 (`../../etc/passwd`) | 已阻断 | `_safe_open_factory` + `resolve()` 校验 |
| 绝对路径访问 (`C:\Windows\...`) | 已阻断 | `_safe_open_factory` + `is_absolute()` 检查 |
| 网络模块导入 (`socket`, `urllib`, `http`) | 已阻断 | AST + `_safe_import` 白名单 |
| `__globals__` / `__code__` / `__loader__` / `__spec__` / `__file__` / `__self__` / `__func__` 属性访问 | 已阻断 | `_DANGEROUS_ATTRS` |

### 1.2 测试覆盖

已有测试文件 `tests/test_security_sandbox_escape.py` 覆盖了以下类别的攻击:

- `TestClassBasesChainEscape` (10 个测试)
- `TestTypeReconstructionEscape` (5 个测试)
- `TestImportViaDunderImport` (16 个测试)
- `TestEvalExecEscape` (6 个测试)
- `TestFileSystemAccessEscape` (6 个测试)
- `TestNetworkAccessEscape` (9 个测试)
- `TestIndirectEscapeAttempts` (17 个测试)
- `TestDangerousDunderMethods` (参数化测试，覆盖 16 个 dunder 属性)

### 1.3 发现的问题

**[MEDIUM] 沙箱内 `chr()` / 字符串拼接绕过 AST 检查**

AST 预检仅阻止包含 `"__builtins__"` 或 `"__import__"` 子字符串的字面量字符串常量。攻击者可通过 `chr()` 拼接绕过:

```python
# 理论绕过路径 (chr 未在 SAFE_BUILTINS 中，但 str 类型可用)
s = chr(95) + chr(95) + "builtins" + chr(95) + chr(95)
```

**评估:** 由于 `chr()` 未包含在 `SAFE_BUILTINS` 白名单中，此绕过路径实际上不可行。风险等级降为 **LOW**。

**[LOW] 子进程隔离模式下的资源限制**

`_run_with_timeout` 使用 `multiprocessing` 的 `spawn` 上下文创建子进程，有超时保护（默认 3-4 秒），但未设置内存限制（如 `resource.setrlimit`）。恶意代码可在超时前消耗大量内存。

**建议:** 对于桌面应用场景，超时保护已足够。若需进一步加固，可考虑在子进程中设置 `resource.setrlimit(RLIMIT_AS, ...)` 内存上限。

### 1.4 沙箱安全评级: PASS (良好)

多层防御（AST 预检 + 受限内置函数 + `_safe_import` 白名单 + `_safe_open_factory` 路径校验 + 子进程隔离 + 超时控制 + 输出缓冲限制）构建了有效的纵深防御。已知攻击向量均有对应测试覆盖。

---

## 2. SQL 注入审计

### 2.1 应用数据库操作 (database.py)

**状态: PASS (安全)**

所有 `AppDatabase` 方法均使用参数化查询:

- `fetchall(sql, params)` / `fetchone(sql, params)` / `execute(sql, params)` 使用 `?` 占位符
- 所有 `INSERT` / `UPDATE` / `DELETE` / `SELECT` 语句均使用参数绑定
- `executemany` 用于批量操作，同样使用参数化
- `search_bookmarks` 和 `search_notes` 的 LIKE 查询通过 `f"%{query}%"` 构造模式字符串后作为参数传入，**非字符串拼接 SQL**

**PRAGMA 使用审查:**

```python
_connection.execute(f"PRAGMA cache_size = {_CACHE_SIZE_KIB}")   # 常量 -8000
_connection.execute(f"PRAGMA mmap_size = {_MMAP_SIZE_BYTES}")   # 常量 268435456
```

这两处使用了 f-string，但值来自硬编码常量（非用户输入），无注入风险。

### 2.2 SQL 练习评测 (practice/evaluator.py)

**[HIGH] 用户 SQL 直接执行 -- 已知设计决策，需文档化**

```python
# evaluate_sql_fixture 中:
rows = conn.execute(code).fetchall()       # 第 106 行
conn.executescript(code)                    # 第 118 行
plan_rows = conn.execute(code).fetchall()  # 第 130 行
conn.executescript(code)                    # 第 137 行
```

用户提交的 SQL 代码直接在内存 SQLite 数据库上执行。这是 **设计意图**（练习评测需要执行用户 SQL），但存在以下风险:

**风险 1: ATTACH DATABASE 攻击**

用户可通过以下语句访问宿主文件系统上的其他 SQLite 数据库:

```sql
ATTACH DATABASE 'C:\Users\SuLi\AppData\Roaming\DevLearnerAI\data\app.db' AS app;
SELECT * FROM app.mentor_api_config;
```

**风险 2: 资源耗尽**

```sql
WITH RECURSIVE cte(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cte) SELECT * FROM cte;
```

**风险 3: 读取任意文件 (通过 `.import` 或 SQLite 特性)**

**缓解措施（已存在）:**
- 使用内存数据库 (`:memory:`)，不连接应用主数据库
- 每次评测创建新的 `conn` 实例并在 `finally` 块中关闭
- 无超时保护

**建议的加固措施:**

1. **阻断 ATTACH/DETACH:** 在执行用户 SQL 前，检查是否包含 `ATTACH` 或 `DETACH` 关键字
2. **设置执行超时:** 使用 `conn.set_progress_handler()` 或在独立线程中执行并设置超时
3. **限制递归深度:** 执行前 `PRAGMA recursive_triggers = OFF`
4. **使用 `forbidden_keywords` 列表:** 已有机制，应确保 `ATTACH`、`DETACH`、`LOAD_EXTENSION` 被加入

### 2.3 SQL 注入审计评级: CONDITIONAL PASS

应用数据库操作完全安全。SQL 练习执行存在已知风险，需通过阻断危险 PRAGMA 和添加超时机制来加固。

---

## 3. 凭证安全审计

### 3.1 凭证存储 (credentials.py)

**状态: PASS (良好)**

存储优先级链设计合理:

1. **Windows:** Windows Credential Manager (Advapi32 CredWriteW/CredReadW) -- 加密存储
2. **非 Windows + keyring:** 通过 `keyring` 库访问系统密钥链
3. **回退:** Base64 编码文件 (`~/.devlearnerai/api_key.txt`)

**发现:**

- 密钥迁移逻辑 (`_migrate_legacy_api_key_if_needed`) 正确地将明文数据库中的 API key 迁移到 keyring，迁移后清空数据库中的明文字段
- `save_api_config` 始终通过 `save_secret()` 存储密钥，数据库中仅保留空字符串
- `load_api_config` 通过 `key_alias` 从 keyring 读取

**[MEDIUM] 回退存储使用 Base64 而非加密**

非 Windows 且未安装 keyring 时，密钥以 Base64 编码存储在 `~/.devlearnerai/api_key.txt`。Base64 不是加密，任何有文件读取权限的进程均可解码。

**建议:** 在日志中已有 warning 提示。考虑使用 `Fernet` (cryptography 库) 进行真正的加密回退，或在安装文档中强调 keyring 的必要性。

### 3.2 凭证日志泄露检查

**状态: PASS**

搜索所有 `logging.debug/info/warning/error` 调用，未发现任何记录 `api_key`、`secret`、`password`、`token` 值的情况。

连接测试缓存键使用 `api_key[-8:]`（仅最后 8 个字符），用于缓存去重而非日志记录，风险可接受。

### 3.3 凭证轮换

支持通过 AI 设置对话框更新密钥（`save_config` -> `save_api_config` -> `save_secret`）。删除旧密钥后保存新密钥即可完成轮换。

### 3.4 凭证安全评级: PASS (有条件)

在 Windows 平台上完全安全。非 Windows 回退存储需改进。

---

## 4. 文件系统安全

### 4.1 沙箱文件访问

**状态: PASS**

`_safe_open_factory` 的路径校验逻辑:

```python
if target.is_absolute():
    resolved = target.resolve()
else:
    resolved = (workdir / target).resolve()

if workdir != resolved and workdir not in resolved.parents:
    raise PermissionError(...)
```

正确处理了绝对路径、相对路径、`..` 遍历和符号链接（`resolve()` 会解析符号链接）。

### 4.2 内容加载路径遍历

**[LOW] 课程 Markdown 加载无路径边界校验**

```python
# content_service.py 第 365 行
path = CONTENT_DIR / lesson.path
content = path.read_text(encoding="utf-8")
```

`lesson.path` 来源于 `course_map.json` 元数据文件。如果元数据文件被篡改为包含 `../../etc/passwd` 的路径，理论上可读取 CONTENT_DIR 之外的文件。

**缓解措施:**
- 元数据文件随应用分发，通常不可被终端用户修改
- 在 PyInstaller 打包后，元数据嵌入可执行文件中

**建议:** 添加路径边界校验:

```python
resolved = (CONTENT_DIR / lesson.path).resolve()
if CONTENT_DIR.resolve() not in resolved.parents:
    raise ValueError("Invalid lesson path")
```

### 4.3 知识库文件加载

**[LOW] 知识库文件无路径限制**

```python
# chat_handler.py 第 864-866 行
@staticmethod
def _read_file_excerpt(path: str) -> str:
    raw = Path(path).read_text(encoding="utf-8")
    return raw[:6000]
```

用户可通过文件对话框添加任意本地文件到知识库，文件路径存储在数据库中。这是 **设计意图**（用户主动选择文件），但:

- 路径无白名单限制
- 摘录截断为 6000 字符，限制了敏感数据暴露量
- 文件选择通过 `QFileDialog` 进行，用户明确知情

**评级:** 可接受风险。这是桌面应用的正常行为。

### 4.4 符号链接攻击

沙箱的 `_safe_open_factory` 使用 `Path.resolve()` 解析符号链接后再进行边界检查，因此符号链接逃逸已被阻断。

应用自身不创建符号链接，无相关攻击面。

### 4.5 文件系统安全评级: PASS

---

## 5. 网络安全

### 5.1 HTTPS 强制

**状态: PASS (严格)**

```python
# api_client.py 第 41-44 行
def require_https(host: str) -> None:
    if not host.lower().startswith("https://"):
        raise ValueError("出于安全考虑，仅允许 HTTPS 连接。")
```

所有 API 调用（`test_connection`、`fetch_models`、`send_chat`、`send_chat_stream`）均在入口处调用 `require_https()`。不允许 HTTP 连接。

### 5.2 SSL 证书验证

**状态: PASS**

```python
def create_ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context()
```

使用 `ssl.create_default_context()` 创建 SSL 上下文，该上下文:
- 验证服务器证书
- 使用系统证书存储
- 禁用不安全的协议版本
- 验证主机名

### 5.3 SSRF 向量

**[LOW] API Host 由用户配置**

用户可将 API Host 设置为内网地址（如 `https://192.168.1.1/v1`）。对于桌面应用，这是正常行为（支持自托管 API 端点），SSRF 风险可接受。

### 5.4 Markdown 渲染安全 (XSS 防护)

**状态: PASS (健壮)**

`_HTMLSanitizer` 实现了白名单净化策略:

- **标签白名单:** 仅允许 `p`, `br`, `h1-h6`, `ul`, `ol`, `li`, `code`, `pre`, `strong`, `em`, `b`, `i`, `a`, `blockquote`, `table`, `tr`, `td`, `th`, `thead`, `tbody`, `hr`, `span`
- **标签黑名单:** 完全剥离 `script`, `style`, `iframe`, `object`, `embed` 及其内容
- **事件属性:** 阻断所有 `on*` 事件处理器（`onclick`, `onerror` 等）
- **危险 URI:** 阻断 `javascript:`, `data:`, `vbscript:` URI
- **链接安全:** `<a>` 标签仅允许 `http://`、`https://` 和相对路径的 `href`
- **注释剥离:** 移除所有 HTML 注释（防止 IE 条件注释攻击）

### 5.5 网络安全评级: PASS

---

## 6. 综合评估

### 6.1 发现汇总

| 编号 | 类别 | 严重性 | 描述 | 状态 |
|---|---|---|---|---|
| V-01 | SQL 执行 | HIGH | 用户 SQL 可执行 ATTACH DATABASE 访问宿主数据库 | **已修复** |
| V-02 | SQL 执行 | MEDIUM | 用户 SQL 无执行超时保护 | **已修复** |
| V-03 | 凭证存储 | MEDIUM | 非 Windows 回退使用 Base64 而非加密 | 已知限制 |
| V-04 | 文件系统 | LOW | 课程 Markdown 加载无路径边界校验 | **已修复** |
| V-05 | 沙箱 | LOW | 子进程无内存限制 | 已知限制 |
| V-06 | 内容路径 | LOW | 知识库文件加载无路径白名单 | 设计意图 |

### 6.2 已通过的安全控制

- [x] Python 沙箱多层防御（AST + 受限内置 + 白名单导入 + 路径校验 + 进程隔离 + 超时）
- [x] 所有应用数据库操作使用参数化查询
- [x] Windows Credential Manager 集成
- [x] 密钥从明文数据库迁移到 keyring
- [x] 日志中无凭证泄露
- [x] HTTPS 强制（所有 API 调用）
- [x] SSL 证书验证（`ssl.create_default_context`）
- [x] XSS 防护（HTML 白名单净化）
- [x] 沙箱文件路径逃逸阻断（`resolve()` + 边界检查）
- [x] 符号链接攻击防护
- [x] 输出缓冲限制（`LimitedBuffer` 12KB 上限）
- [x] 请求去重（防止 API 重复请求）
- [x] 连接状态缓存（5 分钟 TTL）

### 6.3 已应用的修复

**P0 修复 (已应用):**

1. **SQL ATTACH/DETACH 阻断** -- 在 `app/practice/evaluator.py` 中添加 `_check_sql_safety()` 预检函数，在执行用户 SQL 前扫描并阻断 `ATTACH`、`DETACH`、`LOAD_EXTENSION`、`READFILE`、`WRITEFILE` 等危险关键字以及危险 PRAGMA。
2. **SQL 执行超时保护** -- 使用 `conn.set_progress_handler()` 设置 5 秒超时，每 1000 条 VM 指令检查一次，超时后中止查询执行。
3. **课程路径边界校验** -- 在 `app/content_service.py` 的 `lesson_markdown()` 方法中添加 `resolve()` 路径验证，确保加载的 Markdown 文件始终位于 `CONTENT_DIR` 内。

### 6.4 剩余建议（未修复，按优先级排列）

**P1 (近期改进):**

- 非 Windows 平台考虑使用 `Fernet` 加密回退替代 Base64 存储凭证

**P2 (长期加固):**

- 子进程沙箱内存限制（`resource.setrlimit`）
- 知识库文件路径白名单（当前依赖用户通过 `QFileDialog` 主动选择）

---

*审计完成。整体安全态势良好，核心防御机制健全有效。主要风险点集中在 SQL 练习执行区域，该区域因功能需求（评测用户代码）而存在已知的安全张力，建议通过 P0 级修复降低风险。*
