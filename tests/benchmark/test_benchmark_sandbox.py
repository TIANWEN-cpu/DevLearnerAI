"""沙箱代码验证与 AST 解析性能基准测试。

覆盖场景:
- validate_code_safety 在不同代码体量下的耗时
- ast.parse 在不同代码体量下的耗时
- 缓解后的 _evaluate_code_impl 路径（语法检查 + 结构检查子集）
"""

import ast
import textwrap

from app.python_runner import _validate_code_safety

# ── helpers ──────────────────────────────────────────────────────────────────


def _make_code_small() -> str:
    """~10 行简单代码。"""
    return textwrap.dedent("""\
        def greet(name):
            return f"Hello, {name}!"

        result = greet("World")
        print(result)
        x = 1 + 2
        y = x * 3
        z = max(x, y)
    """)


def _make_code_medium() -> str:
    """~80 行中等体量代码。"""
    lines = []
    lines.append("def compute(n):")
    lines.append("    result = []")
    lines.append("    for i in range(n):")
    lines.append("        if i % 2 == 0:")
    lines.append("            result.append(i * 2)")
    lines.append("        else:")
    lines.append("            result.append(i + 1)")
    lines.append("    return result")
    lines.append("")
    lines.append("def transform(data):")
    lines.append("    output = {}")
    lines.append("    for idx, val in enumerate(data):")
    lines.append("        key = f'item_{idx}'")
    lines.append("        output[key] = val ** 2 if isinstance(val, (int, float)) else 0")
    lines.append("    return output")
    lines.append("")
    # pad with data definitions to reach ~80 lines
    for i in range(30):
        lines.append(f"DATA_{i} = list(range({i * 10}, {i * 10 + 10}))")
    lines.append("")
    lines.append("final = transform(compute(100))")
    return "\n".join(lines)


def _make_code_large() -> str:
    """~400 行较大体量代码。"""
    lines = []
    for func_idx in range(20):
        lines.append(f"def func_{func_idx}(x):")
        lines.append("    if x < 0:")
        lines.append("        return -x")
        lines.append("    elif x == 0:")
        lines.append("        return 0")
        lines.append("    else:")
        lines.append("        result = 1")
        lines.append("        for i in range(1, x + 1):")
        lines.append("            result = result * i")
        lines.append("        return result")
        lines.append("")
    for var_idx in range(40):
        lines.append(f"CONST_{var_idx} = {var_idx * 17 % 997}")
    lines.append("")
    lines.append("FUNCS = [func_0, func_1, func_2, func_3, func_4,")
    lines.append("    func_5, func_6, func_7, func_8, func_9,")
    lines.append("    func_10, func_11, func_12, func_13, func_14,")
    lines.append("    func_15, func_16, func_17, func_18, func_19]")
    lines.append("")
    lines.append("def main():")
    lines.append("    total = 0")
    lines.append("    for i in range(20):")
    lines.append("        total = total + FUNCS[i](i % 12)")
    lines.append("    print(total)")
    lines.append("")
    lines.append("main()")
    return "\n".join(lines)


# ── benchmarks ───────────────────────────────────────────────────────────────


class TestValidateCodeSafety:
    """基准: validate_code_safety 各体量耗时。"""

    def test_validate_safety_small(self, benchmark):
        code = _make_code_small()
        benchmark(_validate_code_safety, code)

    def test_validate_safety_medium(self, benchmark):
        code = _make_code_medium()
        benchmark(_validate_code_safety, code)

    def test_validate_safety_large(self, benchmark):
        code = _make_code_large()
        benchmark(_validate_code_safety, code)


class TestAstParse:
    """基准: ast.parse 各体量耗时。"""

    def test_parse_small(self, benchmark):
        code = _make_code_small()
        benchmark(ast.parse, code)

    def test_parse_medium(self, benchmark):
        code = _make_code_medium()
        benchmark(ast.parse, code)

    def test_parse_large(self, benchmark):
        code = _make_code_large()
        benchmark(ast.parse, code)


class TestAstWalk:
    """基准: ast.walk 遍历各体量 AST 的耗时。"""

    def _walk(self, code):
        tree = ast.parse(code)
        for _ in ast.walk(tree):
            pass

    def test_walk_small(self, benchmark):
        benchmark(self._walk, _make_code_small())

    def test_walk_medium(self, benchmark):
        benchmark(self._walk, _make_code_medium())

    def test_walk_large(self, benchmark):
        benchmark(self._walk, _make_code_large())
