# 沙箱问题排查

本文档汇总与代码执行沙箱和练习评测相关的常见问题及解决方案。

---

## 代码执行问题

### Q: 代码中不允许使用 import 语句？

沙箱禁止所有 `import` 语句，但允许使用以下白名单模块：

```python
ALLOWED_IMPORTS = {
    "argparse", "collections", "datetime", "functools",
    "itertools", "json", "logging", "math", "pathlib",
    "re", "statistics",
}
```

**正确做法**: 使用内置函数和白名单内的功能，不要尝试 `import`。

```python
# 错误 - 沙箱不允许
import math
result = math.sqrt(16)

# 正确 - 使用内置函数
# 数学运算使用基本运算符
result = 16 ** 0.5
```

> 注意：沙箱中 `math` 模块的函数需要通过其他方式实现，如 `x ** 0.5` 替代 `math.sqrt(x)`。

---

### Q: 不允许调用 eval() / exec()？

沙箱拦截以下危险内置函数：

```python
_DANGEROUS_BUILTINS_CALLS = frozenset({
    "eval", "exec", "compile", "breakpoint",
    "getattr", "hasattr", "delattr", "setattr",
    "type", "object", "super", "dir", "vars",
    "globals", "locals", "memoryview", "bytearray",
})
```

**解决方案**: 使用安全的替代方法：

```python
# 错误
data = eval("{'name': 'Alice'}")

# 正确
data = {"name": "Alice"}
# 或使用 json（如果可用）
import json  # json 在白名单中
data = json.loads('{"name": "Alice"}')
```

---

### Q: 不允许访问 __class__ 等双下划线属性？

沙箱拦截所有双下划线属性访问，防止沙箱逃逸：

```python
# 这些代码都会被拦截
obj.__class__
obj.__bases__
obj.__subclasses__()
getattr(obj, "__builtins__")
```

**说明**: 这是安全限制，对于正常编程练习不需要这些属性。

---

### Q: 不允许调用 getattr() 对双下划线属性？

```python
# 被拦截
getattr(some_object, "__class__")

# 被拦截
hasattr(some_object, "__subclasses__")
```

**解决方案**: 直接使用点号访问非双下划线属性：

```python
# 正常属性访问是允许的
name = person.name
age = person.age
```

---

### Q: 文件操作被限制？

沙箱中的 `open()` 函数被替换为受限版本，只能访问临时工作目录内的文件：

```python
# 允许 - 在临时目录中读写
with open("data.txt", "w") as f:
    f.write("hello")

# 不允许 - 目录逃逸
with open("/etc/passwd", "r") as f:  # PermissionError
    content = f.read()

with open("../../secret.txt", "r") as f:  # PermissionError
    content = f.read()
```

---

### Q: 代码执行超时？

**默认超时**:
- 代码执行：3 秒
- 代码评测：4 秒

**超时后**: 子进程被终止，返回超时错误。

**常见原因**:

```python
# 死循环 - 没有退出条件
while True:
    print("loop")

# 修正
count = 0
while count < 10:
    print("loop")
    count += 1
```

```python
# 递归过深
def factorial(n):
    return n * factorial(n - 1)  # 缺少基本情况

# 修正
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

---

### Q: 标准输出被截断？

沙箱限制标准输出为 12KB（约 12,000 字符）。超出时会抛出 RuntimeError。

```python
# 可能触发输出截断
for i in range(10000):
    print(f"Line {i}: {'x' * 100}")

# 优化：减少输出量
for i in range(10):  # 只输出前 10 行
    print(f"Line {i}: {'x' * 100}")
```

---

### Q: 代码可以执行但评测得 0 分？

评测采用多维度评分：

```text
语法检查:   20 分  (代码是否可以被解析)
结构检查:   20 分  (是否包含期望的 AST 节点)
安全执行:   10 分  (是否在沙箱中成功执行)
对象检查:   10 分  (是否定义了要求的名称)
测试用例:   40 分  (测试用例通过率)
```

**常见原因**:

1. **函数名不匹配**: 题目要求 `add`，你定义了 `addition`
2. **缺少 return**: 题目要求 Return 节点，但你只用了 `print`
3. **测试用例未通过**: 检查 `expression` 和 `expected` 的关系

```python
# 得 0 分的示例
def addition(a, b):  # 名字应为 add
    print(a + b)     # 应该 return，不是 print

# 满分示例
def add(a, b):       # 名字匹配 required_names
    return a + b     # 包含 Return 节点
```

---

### Q: 评测通过但分数不满分？

评分规则：通过条件是 `score >= 70 且 全部测试通过 且 无缺失节点`。

可能得 70-100 分的情况：

- 存在不需要的代码（但不扣分）
- 部分测试用例通过（得部分测试分）

---

## SQL 评测问题

### Q: SQL 查询可以执行但结果不匹配？

SQL 评测使用内存数据库真实执行，结果与参考答案逐行比对。

**检查要点**:

1. **列顺序**: SELECT 的列顺序必须与参考答案一致
2. **数据类型**: 注意字符串引号和数值精度
3. **NULL 处理**: NULL 与空字符串不同
4. **排序**: 默认无序比对，除非 fixture 指定 `ordered: true`

```sql
-- 参考答案期望: (1, 'Alice', 25)

-- 错误 - 列顺序不对
SELECT name, id, age FROM users;  -- ('Alice', 1, 25) ≠ (1, 'Alice', 25)

-- 正确
SELECT id, name, age FROM users;
```

---

### Q: DDL 练习（CREATE TABLE）如何评测？

DDL 练习通过检查数据库结构变更来评测：

```python
# 例如 db-design-enrollment-table 练习
# 评测器检查: enrollments 表是否存在 student_id 和 course_id 列
columns = {row[1] for row in conn.execute("PRAGMA table_info(enrollments)").fetchall()}
return {"student_id", "course_id"}.issubset(columns)
```

**确保**: 表名和列名与题目要求完全匹配。

---

### Q: SQL 中使用了 forbidden_keywords？

某些练习禁止使用特定关键字（如 `DROP`、`DELETE`）。如果需要修改表结构，请使用 `ALTER TABLE` 而非 `DROP + CREATE`。

---

## C/C# 评测问题

### Q: C/C# 练习只能做结构检查？

是的。当前 C/C# 评测使用关键字和结构检查，暂不支持编译执行。

**评测方式**: 检查代码中是否包含所有 `required_keywords`，以及是否不包含 `forbidden_keywords`。

```json
{
  "required_keywords": ["printf", "include", "stdio.h", "main"],
  "forbidden_keywords": ["system"]
}
```

---

## 调试技巧

### 测试沙箱安全性

> 完整的沙箱安全架构详见 [安全模型](../concepts/security-model.md)。

```python
from app.python_runner import _validate_code_safety

# 测试是否会被拦截
try:
    _validate_code_safety("eval('1+1')")
    print("未被拦截 - 这不应该发生")
except SyntaxError as e:
    print(f"被拦截: {e}")
```

### 测试代码执行

```python
from app.python_runner import run_python_code

result = run_python_code("""
def add(a, b):
    return a + b
print(add(3, 5))
""", timeout_sec=3)

print(result)
# {'ok': True, 'stdout': '8', 'duration_sec': 0}
```

### 测试代码评测

```python
from app.python_runner import evaluate_python_code

result = evaluate_python_code(
    code="def add(a, b): return a + b",
    expected_nodes=["FunctionDef", "Return"],
    required_names=["add"],
    tests=[
        {"expression": "add(3, 5)", "expected": 8},
        {"expression": "add(-2, 7)", "expected": 5},
    ],
    timeout_sec=4,
)

print(f"得分: {result['score']}")
print(f"通过: {result['passed']}")
print(f"反馈:")
for line in result['feedback_lines']:
    print(f"  - {line}")
```

### 测试 SQL 评测

```python
from app.practice.exercise_loader import load_exercises
from app.practice.evaluator import evaluate_sql

exercises = load_exercises()
ex = next(e for e in exercises if e.id == "db-select-users")
result = evaluate_sql(ex, "SELECT * FROM users;")
print(f"得分: {result.score}, 通过: {result.passed}")
for line in result.feedback_lines:
    print(f"  - {line}")
```

---

## 相关文档

- [安全模型](../concepts/security-model.md) - 沙箱安全架构详情
- [ADR-002: 沙箱方案](../adr/002-sandbox-approach.md) - 设计决策
- [练习创建指南](../guides/exercise-creation.md) - 如何创建练习
