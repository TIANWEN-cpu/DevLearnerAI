"""课程内容加载与 Markdown 渲染性能基准测试。

覆盖场景:
- ContentService 初始化与 Track 构建
- lesson_by_id 查找
- lesson_markdown 读取 (含缓存命中)
- render_message_html / sanitize_html 渲染
- bubble_html 构建
"""

import json
import textwrap
from unittest.mock import patch

import pytest

from app.ai.markdown_renderer import bubble_html, render_message_html, sanitize_html
from app.content_service import ContentService, _clean_list, _clean_text

# ── 内容服务基准 ────────────────────────────────────────────────────────────


def _make_course_map(n_tracks: int = 3, n_modules: int = 4, n_lessons: int = 5) -> dict:
    """构造包含指定数量 Track / Module / Lesson 的课程元数据。"""
    tracks = []
    for t in range(n_tracks):
        modules = []
        for m in range(n_modules):
            lessons = []
            for li in range(n_lessons):
                lid = f"t{t}-m{m}-l{li}"
                lessons.append(
                    {
                        "id": lid,
                        "title": f"课程 {lid}",
                        "summary": f"这是课程 {lid} 的简介。",
                        "path": f"track{t}/module{m}/{lid}.md",
                        "difficulty": "基础",
                        "estimated_minutes": 25,
                        "tags": ["tag-a", "tag-b"],
                        "prerequisites": [],
                        "outcomes": ["掌握基本概念"],
                    }
                )
            modules.append(
                {
                    "id": f"t{t}-m{m}",
                    "title": f"模块 {t}-{m}",
                    "summary": f"模块 {t}-{m} 的简介。",
                    "lessons": lessons,
                }
            )
        tracks.append(
            {
                "id": f"track-{t}",
                "title": f"技术栈 {t}",
                "icon": "📘",
                "summary": f"技术栈 {t} 的简介。",
                "modules": modules,
            }
        )
    return {"tracks": tracks}


@pytest.fixture()
def content_service(tmp_path):
    """构造使用临时文件的 ContentService 实例。"""
    course_map = _make_course_map()
    meta_path = tmp_path / "course_map.json"
    meta_path.write_text(json.dumps(course_map, ensure_ascii=False), encoding="utf-8")
    return ContentService(metadata_path=meta_path)


class TestContentServiceInit:
    """基准: ContentService 初始化。"""

    def test_init_small(self, benchmark, tmp_path):
        data = _make_course_map(2, 2, 3)
        meta = tmp_path / "cm.json"
        meta.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        benchmark(ContentService, metadata_path=meta)

    def test_init_large(self, benchmark, tmp_path):
        data = _make_course_map(5, 6, 10)
        meta = tmp_path / "cm.json"
        meta.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        benchmark(ContentService, metadata_path=meta)


class TestLessonLookup:
    """基准: lesson_by_id 查找。"""

    def test_lesson_by_id_hit(self, benchmark, content_service):
        # t0-m0-l0 应存在
        benchmark(content_service.lesson_by_id, "t0-m0-l0")

    def test_lesson_by_id_miss(self, benchmark, content_service):
        benchmark(content_service.lesson_by_id, "nonexistent-id")


class TestMarkdownRead:
    """基准: lesson_markdown 读取。"""

    def test_markdown_first_read(self, benchmark, content_service, tmp_path):
        """首次读取（含磁盘 I/O）。"""
        lesson_path = tmp_path / "content" / "track0" / "module0"
        lesson_path.mkdir(parents=True, exist_ok=True)
        (lesson_path / "t0-m0-l0.md").write_text(
            "# 测试课程\n\n这是课程内容。" * 50,
            encoding="utf-8",
        )
        content_service.clear_markdown_cache()
        result = content_service.lesson_by_id("t0-m0-l0")
        lesson = result[2]
        # patch CONTENT_DIR to use tmp_path
        with patch("app.content_service.CONTENT_DIR", tmp_path / "content"):
            benchmark(content_service.lesson_markdown, lesson)

    def test_markdown_cache_hit(self, benchmark, content_service, tmp_path):
        """缓存命中时读取。"""
        lesson_path = tmp_path / "content" / "track0" / "module0"
        lesson_path.mkdir(parents=True, exist_ok=True)
        (lesson_path / "t0-m0-l0.md").write_text(
            "# 缓存测试\n\n缓存内容。" * 50,
            encoding="utf-8",
        )
        content_service.clear_markdown_cache()
        result = content_service.lesson_by_id("t0-m0-l0")
        lesson = result[2]
        with patch("app.content_service.CONTENT_DIR", tmp_path / "content"):
            content_service.lesson_markdown(lesson)  # populate cache
            benchmark(content_service.lesson_markdown, lesson)


# ── 文本清洗基准 ────────────────────────────────────────────────────────────


class TestTextCleaning:
    """基准: 文本清洗函数。"""

    def test_clean_text_normal(self, benchmark):
        benchmark(_clean_text, "正常的课程标题文本", "回退值")

    def test_clean_text_corrupt(self, benchmark):
        benchmark(_clean_text, "???锟斤拷璇???", "回退值")

    def test_clean_list_small(self, benchmark):
        benchmark(_clean_list, ["标签A", "标签B", "标签C"])

    def test_clean_list_large(self, benchmark):
        tags = [f"tag-{i}" for i in range(50)]
        benchmark(_clean_list, tags)


# ── Markdown 渲染基准 ────────────────────────────────────────────────────────


MARKDOWN_SHORT = "这是一段简短的 **Markdown** 文本，包含 `代码片段`。"
MARKDOWN_MEDIUM = textwrap.dedent("""\
    # 标题一

    这是第一段正文，包含一些 **加粗** 和 *斜体* 文本。

    ## 标题二

    - 列表项 1
    - 列表项 2
    - 列表项 3

    ```python
    def hello():
        print("Hello, World!")
    ```

    > 这是一段引用文本，用于展示 blockquote 的渲染效果。

    | 列1 | 列2 | 列3 |
    |-----|-----|-----|
    | A   | B   | C   |
    | D   | E   | F   |
""")
MARKDOWN_LARGE = "\n\n".join(
    [f"## 章节 {i}\n\n" + f"这是第 {i} 章的内容。" + "\n\n" + "段落文本。" * 20 for i in range(30)]
)


class TestMarkdownRendering:
    """基准: render_message_html 不同体量。"""

    def test_render_short(self, benchmark):
        benchmark(render_message_html, MARKDOWN_SHORT, True)

    def test_render_medium(self, benchmark):
        benchmark(render_message_html, MARKDOWN_MEDIUM, True)

    def test_render_large(self, benchmark):
        benchmark(render_message_html, MARKDOWN_LARGE, True)

    def test_render_plain_text(self, benchmark):
        """纯文本模式（无 Markdown 解析）。"""
        benchmark(render_message_html, MARKDOWN_MEDIUM, False)


class TestSanitizeHtml:
    """基准: HTML 净化。"""

    def test_sanitize_simple(self, benchmark):
        html = "<p>简单段落</p><a href='https://example.com'>链接</a>"
        benchmark(sanitize_html, html)

    def test_sanitize_complex(self, benchmark):
        html = (
            "<div><h1>标题</h1><p onclick='alert(1)'>段落</p>"
            "<script>alert('xss')</script>"
            "<a href='javascript:void(0)'>危险链接</a>"
            "<table><tr><td>单元格</td></tr></table>" + "<p>重复段落</p>" * 20
        )
        benchmark(sanitize_html, html)


class TestBubbleHtml:
    """基准: bubble_html 构建。"""

    def test_bubble_user(self, benchmark):
        benchmark(bubble_html, "user", "请问如何使用 Python 的列表推导式？")

    def test_bubble_assistant(self, benchmark):
        benchmark(bubble_html, "assistant", MARKDOWN_MEDIUM)
