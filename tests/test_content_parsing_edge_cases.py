"""Content parsing edge case tests for app.content_service.

Covers:
- Malformed markdown handling
- Very large course files
- Missing metadata fields
- Encoding issues (UTF-8, GBK)
- Cache eviction behavior
- Edge cases in dataclass properties
"""

import json
from unittest.mock import patch

import pytest

from app.content_service import (
    ContentService,
    Lesson,
    Module,
    Track,
    _clean_list,
    _clean_text,
    _looks_corrupt,
)


# ---------------------------------------------------------------------------
# Malformed markdown handling
# ---------------------------------------------------------------------------
class TestMalformedMarkdown:
    """Test lesson_markdown with various malformed content."""

    @pytest.fixture
    def service(self, tmp_path):
        p = tmp_path / "map.json"
        p.write_text(json.dumps({"tracks": []}), encoding="utf-8")
        return ContentService(metadata_path=p)

    def test_empty_markdown(self, service, tmp_path):
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        (md_dir / "lesson.md").write_text("", encoding="utf-8")
        lesson = Lesson(id="l1", title="L1", summary="", path="lesson.md", difficulty="", estimated_minutes=10)
        with patch("app.content_service.CONTENT_DIR", md_dir):
            result = service.lesson_markdown(lesson)
        assert result == ""

    def test_binary_file_as_markdown(self, service, tmp_path):
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        (md_dir / "lesson.md").write_bytes(b"\x00\x01\x02\x03\x04\x05")
        lesson = Lesson(id="l1", title="L1", summary="", path="lesson.md", difficulty="", estimated_minutes=10)
        with patch("app.content_service.CONTENT_DIR", md_dir):
            result = service.lesson_markdown(lesson)
        # Should not raise, may return garbled or replacement chars
        assert isinstance(result, str)

    def test_very_large_markdown(self, service, tmp_path):
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        large_content = "# Title\n\n" + "A" * 1_000_000
        (md_dir / "lesson.md").write_text(large_content, encoding="utf-8")
        lesson = Lesson(id="l1", title="L1", summary="", path="lesson.md", difficulty="", estimated_minutes=10)
        with patch("app.content_service.CONTENT_DIR", md_dir):
            result = service.lesson_markdown(lesson)
        assert len(result) == len(large_content)

    def test_markdown_with_bom(self, service, tmp_path):
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        content = "? Title with BOM"
        (md_dir / "lesson.md").write_text(content, encoding="utf-8")
        lesson = Lesson(id="l1", title="L1", summary="", path="lesson.md", difficulty="", estimated_minutes=10)
        with patch("app.content_service.CONTENT_DIR", md_dir):
            result = service.lesson_markdown(lesson)
        assert "Title with BOM" in result

    def test_markdown_with_only_whitespace(self, service, tmp_path):
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        (md_dir / "lesson.md").write_text("   \n\n  \n   ", encoding="utf-8")
        lesson = Lesson(id="l1", title="L1", summary="", path="lesson.md", difficulty="", estimated_minutes=10)
        with patch("app.content_service.CONTENT_DIR", md_dir):
            result = service.lesson_markdown(lesson)
        assert result.strip() == ""

    def test_path_traversal_in_lesson_path(self, service, tmp_path):
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        lesson = Lesson(id="l1", title="L1", summary="", path="../../etc/passwd", difficulty="", estimated_minutes=10)
        with patch("app.content_service.CONTENT_DIR", md_dir):
            result = service.lesson_markdown(lesson)
        # Should handle gracefully (file not found or path traversal detected)
        assert "暂时缺失" in result or "错误" in result or "无效" in result

    def test_empty_path_lesson(self, service, tmp_path):
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        lesson = Lesson(id="l1", title="L1", summary="", path="", difficulty="", estimated_minutes=10)
        with patch("app.content_service.CONTENT_DIR", md_dir):
            result = service.lesson_markdown(lesson)
        # Empty path should resolve to CONTENT_DIR itself, which is a directory
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# Very large course files
# ---------------------------------------------------------------------------
class TestVeryLargeCourseFiles:
    """Test ContentService with very large course metadata."""

    def test_many_tracks(self, tmp_path):
        tracks = [{"id": f"t{i}", "title": f"Track {i}", "modules": []} for i in range(100)]
        data = {"tracks": tracks}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        assert len(cs._tracks_index) == 100

    def test_many_modules_per_track(self, tmp_path):
        modules = [{"id": f"m{i}", "title": f"Module {i}", "lessons": []} for i in range(50)]
        data = {"tracks": [{"id": "t1", "title": "T1", "modules": modules}]}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        tracks = cs.tracks
        assert len(tracks) == 1
        assert len(tracks[0].modules) == 50

    def test_many_lessons_per_module(self, tmp_path):
        lessons = [
            {
                "id": f"l{i}",
                "title": f"Lesson {i}",
                "summary": f"Summary {i}",
                "path": f"lesson_{i}.md",
                "difficulty": "基础",
                "estimated_minutes": 15,
            }
            for i in range(100)
        ]
        data = {"tracks": [{"id": "t1", "title": "T1", "modules": [{"id": "m1", "title": "M1", "lessons": lessons}]}]}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        all_l = cs.all_lessons()
        assert len(all_l) == 100

    def test_deeply_nested_modules_and_lessons(self, tmp_path):
        """Test with many tracks, each with many modules, each with many lessons."""
        tracks = []
        for t in range(5):
            modules = []
            for m in range(10):
                lessons = [
                    {
                        "id": f"l{t}-{m}-{li}",
                        "title": f"Lesson {t}-{m}-{li}",
                        "path": f"t{t}/m{m}/l{li}.md",
                    }
                    for li in range(10)
                ]
                modules.append({"id": f"m{t}-{m}", "title": f"Module {t}-{m}", "lessons": lessons})
            tracks.append({"id": f"t{t}", "title": f"Track {t}", "modules": modules})
        data = {"tracks": tracks}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        all_l = cs.all_lessons()
        assert len(all_l) == 500  # 5 * 10 * 10

    def test_lesson_by_id_with_many_lessons(self, tmp_path):
        """lesson_by_id should work efficiently with many lessons."""
        lessons = [{"id": f"l{i}", "title": f"L{i}", "path": f"l{i}.md"} for i in range(200)]
        data = {"tracks": [{"id": "t1", "title": "T1", "modules": [{"id": "m1", "title": "M1", "lessons": lessons}]}]}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        result = cs.lesson_by_id("l199")
        assert result is not None
        assert result[2].id == "l199"


# ---------------------------------------------------------------------------
# Missing metadata fields
# ---------------------------------------------------------------------------
class TestMissingMetadataFields:
    """Test ContentService behavior with missing or incomplete metadata."""

    def test_track_with_no_modules(self, tmp_path):
        data = {"tracks": [{"id": "t1", "title": "T1"}]}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        track = cs.track_by_id("t1")
        assert track is not None
        assert track.modules == []

    def test_module_with_no_lessons(self, tmp_path):
        data = {"tracks": [{"id": "t1", "title": "T1", "modules": [{"id": "m1", "title": "M1"}]}]}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        track = cs.track_by_id("t1")
        assert len(track.modules) == 1
        assert track.modules[0].lessons == []

    def test_lesson_with_minimal_fields(self, tmp_path):
        data = {
            "tracks": [{"id": "t1", "title": "T1", "modules": [{"id": "m1", "title": "M1", "lessons": [{"id": "l1"}]}]}]
        }
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        result = cs.lesson_by_id("l1")
        assert result is not None
        lesson = result[2]
        assert lesson.id == "l1"
        assert lesson.title == "未命名课程"
        assert lesson.difficulty == "基础"
        assert lesson.estimated_minutes == 25

    def test_lesson_with_non_numeric_estimated_minutes_raises(self, tmp_path):
        """Non-numeric estimated_minutes now falls back to default 25 gracefully."""
        data = {
            "tracks": [
                {
                    "id": "t1",
                    "title": "T1",
                    "modules": [
                        {
                            "id": "m1",
                            "title": "M1",
                            "lessons": [{"id": "l1", "title": "L1", "estimated_minutes": "not_a_number"}],
                        }
                    ],
                }
            ]
        }
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        track = cs.track_by_id("t1")
        lesson = track.modules[0].lessons[0]
        assert lesson.estimated_minutes == 25

    def test_module_with_empty_id(self, tmp_path):
        data = {"tracks": [{"id": "t1", "title": "T1", "modules": [{"title": "M1", "lessons": []}]}]}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        track = cs.track_by_id("t1")
        assert track.modules[0].id == "module"  # default

    def test_track_with_empty_id(self, tmp_path):
        data = {"tracks": [{"title": "T1", "modules": []}]}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        assert len(cs.tracks) == 1
        assert cs.tracks[0].id == "track"  # default

    def test_lesson_with_none_fields_raises(self, tmp_path):
        """None values for tags/prerequisites/outcomes cause TypeError in _build_search_index."""
        data = {
            "tracks": [
                {
                    "id": "t1",
                    "title": "T1",
                    "modules": [
                        {
                            "id": "m1",
                            "title": "M1",
                            "lessons": [
                                {
                                    "id": "l1",
                                    "title": None,
                                    "summary": None,
                                    "path": None,
                                    "difficulty": None,
                                    "tags": None,
                                    "prerequisites": None,
                                    "outcomes": None,
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        # None tags should be handled gracefully (not crash) during _build_search_index
        cs = ContentService(metadata_path=p)
        assert len(cs.tracks) == 1


# ---------------------------------------------------------------------------
# Encoding issues
# ---------------------------------------------------------------------------
class TestEncodingIssues:
    """Test ContentService behavior with various encoding issues."""

    def test_gbk_encoded_file(self, tmp_path):
        """ContentService reads with utf-8, GBK-encoded file may cause issues."""
        data = {"tracks": []}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        # Write in GBK (not UTF-8)
        gbk_content = "你好世界".encode("gbk")
        (md_dir / "lesson.md").write_bytes(gbk_content)
        lesson = Lesson(id="l1", title="L1", summary="", path="lesson.md", difficulty="", estimated_minutes=10)
        with patch("app.content_service.CONTENT_DIR", md_dir):
            result = cs.lesson_markdown(lesson)
        # Should handle gracefully - may contain replacement chars or error message
        assert isinstance(result, str)

    def test_latin1_encoded_file(self, tmp_path):
        """ContentService reads with utf-8, Latin-1 encoded file may cause issues."""
        data = {"tracks": []}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        latin1_content = "café résumé".encode("latin-1")
        (md_dir / "lesson.md").write_bytes(latin1_content)
        lesson = Lesson(id="l1", title="L1", summary="", path="lesson.md", difficulty="", estimated_minutes=10)
        with patch("app.content_service.CONTENT_DIR", md_dir):
            result = cs.lesson_markdown(lesson)
        assert isinstance(result, str)

    def test_utf8_with_bom_in_json(self, tmp_path):
        """JSON file with UTF-8 BOM should be handled."""
        data = {"tracks": [{"id": "t1", "title": "T1", "modules": []}]}
        content = "﻿" + json.dumps(data, ensure_ascii=False)
        p = tmp_path / "map.json"
        p.write_text(content, encoding="utf-8")
        # This may fail JSON parsing due to BOM
        cs = ContentService(metadata_path=p)
        # Should handle gracefully
        assert isinstance(cs._tracks_index, list)

    def test_json_with_mixed_encoding_content(self, tmp_path):
        """JSON with Unicode characters in various scripts."""
        data = {
            "tracks": [
                {
                    "id": "py",
                    "title": "Python 编程",
                    "modules": [
                        {
                            "id": "basics",
                            "title": "基础语法",
                            "lessons": [
                                {
                                    "id": "l1",
                                    "title": "变量与类型",
                                    "path": "test.md",
                                }
                            ],
                        }
                    ],
                }
            ]
        }
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        assert len(cs.tracks) == 1
        assert cs.tracks[0].title == "Python 编程"

    def test_json_with_ensure_ascii_true(self, tmp_path):
        """JSON written with ensure_ascii=True (escaped Unicode)."""
        data = {
            "tracks": [
                {
                    "id": "py",
                    "title": "编程",
                    "modules": [],
                }
            ]
        }
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=True), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        assert len(cs._tracks_index) == 1
        # After parsing, the Unicode escapes become the actual characters
        assert cs._tracks_index[0]["title"] == "编程"


# ---------------------------------------------------------------------------
# Cache eviction behavior
# ---------------------------------------------------------------------------
class TestCacheEviction:
    """Test markdown cache eviction when it reaches capacity."""

    def test_cache_eviction_on_overflow(self, tmp_path):
        data = {"tracks": []}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        md_dir = tmp_path / "content"
        md_dir.mkdir()

        # Create more files than the cache limit
        max_cache = cs._MAX_MARKDOWN_CACHE
        for i in range(max_cache + 5):
            (md_dir / f"lesson_{i}.md").write_text(f"Content {i}", encoding="utf-8")

        lessons = [
            Lesson(id=f"l{i}", title=f"L{i}", summary="", path=f"lesson_{i}.md", difficulty="", estimated_minutes=10)
            for i in range(max_cache + 5)
        ]

        with patch("app.content_service.CONTENT_DIR", md_dir):
            for lesson in lessons:
                cs.lesson_markdown(lesson)

        # Cache should not exceed the limit
        assert len(cs._markdown_cache) <= max_cache

    def test_clear_markdown_cache(self, tmp_path):
        data = {"tracks": []}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        (md_dir / "l.md").write_text("content", encoding="utf-8")

        lesson = Lesson(id="l1", title="L1", summary="", path="l.md", difficulty="", estimated_minutes=10)
        with patch("app.content_service.CONTENT_DIR", md_dir):
            cs.lesson_markdown(lesson)
        assert len(cs._markdown_cache) == 1

        cs.clear_markdown_cache()
        assert len(cs._markdown_cache) == 0

    def test_cached_content_returned_on_second_access(self, tmp_path):
        data = {"tracks": []}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        (md_dir / "l.md").write_text("cached content", encoding="utf-8")

        lesson = Lesson(id="l1", title="L1", summary="", path="l.md", difficulty="", estimated_minutes=10)
        with patch("app.content_service.CONTENT_DIR", md_dir):
            result1 = cs.lesson_markdown(lesson)
            result2 = cs.lesson_markdown(lesson)
        assert result1 == result2
        assert result1 == "cached content"


# ---------------------------------------------------------------------------
# Dataclass properties edge cases
# ---------------------------------------------------------------------------
class TestDataclassEdgeCases:
    """Test dataclass properties and edge cases."""

    def test_module_key_equals_id(self):
        m = Module(id="test-module", title="TM", summary="S")
        assert m.key == "test-module"

    def test_track_lessons_flatten_across_modules(self):
        l1 = Lesson(id="l1", title="L1", summary="", path="", difficulty="", estimated_minutes=10)
        l2 = Lesson(id="l2", title="L2", summary="", path="", difficulty="", estimated_minutes=10)
        l3 = Lesson(id="l3", title="L3", summary="", path="", difficulty="", estimated_minutes=10)
        l4 = Lesson(id="l4", title="L4", summary="", path="", difficulty="", estimated_minutes=10)
        m1 = Module(id="m1", title="M1", summary="", lessons=[l1, l2])
        m2 = Module(id="m2", title="M2", summary="", lessons=[l3, l4])
        track = Track(id="t1", title="T", icon="", summary="", modules=[m1, m2])
        assert track.lessons == [l1, l2, l3, l4]

    def test_track_lessons_empty_modules(self):
        track = Track(id="t1", title="T", icon="", summary="", modules=[])
        assert track.lessons == []

    def test_track_lessons_modules_with_no_lessons(self):
        m1 = Module(id="m1", title="M1", summary="", lessons=[])
        m2 = Module(id="m2", title="M2", summary="", lessons=[])
        track = Track(id="t1", title="T", icon="", summary="", modules=[m1, m2])
        assert track.lessons == []

    def test_lesson_default_tags(self):
        lesson = Lesson(id="l1", title="L1", summary="", path="", difficulty="", estimated_minutes=10)
        assert lesson.tags == []
        assert lesson.prerequisites == []
        assert lesson.outcomes == []

    def test_module_default_lessons(self):
        module = Module(id="m1", title="M1", summary="")
        assert module.lessons == []

    def test_track_default_modules(self):
        track = Track(id="t1", title="T", icon="", summary="")
        assert track.modules == []


# ---------------------------------------------------------------------------
# _looks_corrupt edge cases
# ---------------------------------------------------------------------------
class TestLooksCorruptEdgeCases:
    """Test _looks_corrupt with additional edge cases."""

    def test_none_input(self):
        assert _looks_corrupt(None) is True

    def test_empty_string(self):
        assert _looks_corrupt("") is True

    def test_single_char(self):
        assert _looks_corrupt("a") is False

    def test_newlines_only(self):
        assert _looks_corrupt("\n\n\n") is False

    def test_tabs_only(self):
        assert _looks_corrupt("\t\t\t") is False

    def test_mixed_whitespace(self):
        assert _looks_corrupt(" \t\n ") is False

    def test_chinese_punctuation(self):
        assert _looks_corrupt("你好，世界！") is False

    def test_japanese_hiragana(self):
        assert _looks_corrupt("こんにちは") is False

    def test_korean_hangul(self):
        assert _looks_corrupt("안녕하세요") is False

    def test_arabic_text(self):
        assert _looks_corrupt("مرحبا") is False

    def test_russian_cyrillic(self):
        assert _looks_corrupt("Привет") is False


# ---------------------------------------------------------------------------
# _clean_text edge cases
# ---------------------------------------------------------------------------
class TestCleanTextEdgeCases:
    """Test _clean_text with additional edge cases."""

    def test_empty_string_returns_fallback(self):
        assert _clean_text("", "default") == "default"

    def test_whitespace_only_returns_fallback(self):
        assert _clean_text("   ", "default") == "default"

    def test_tabs_and_newlines(self):
        assert _clean_text("\t\n", "default") == "default"

    def test_very_long_text(self):
        long = "x" * 10000
        assert _clean_text(long, "default") == long

    def test_special_characters(self):
        assert _clean_text("!@#$%^&*()", "default") == "!@#$%^&*()"

    def test_html_tags(self):
        assert _clean_text("<b>bold</b>", "default") == "<b>bold</b>"

    def test_markdown_syntax(self):
        assert _clean_text("# Header\n**bold**", "default") == "# Header\n**bold**"


# ---------------------------------------------------------------------------
# _clean_list edge cases
# ---------------------------------------------------------------------------
class TestCleanListEdgeCases:
    """Test _clean_list with additional edge cases."""

    def test_empty_strings_filtered(self):
        result = _clean_list(["", "hello", "", "world", ""])
        assert result == ["hello", "world"]

    def test_whitespace_only_items_filtered(self):
        result = _clean_list(["   ", "hello", "\t\n", "world"])
        assert result == ["hello", "world"]

    def test_all_empty_returns_fallback(self):
        result = _clean_list(["", "", ""], ["default"])
        assert result == ["default"]

    def test_nested_list_items(self):
        result = _clean_list([[1, 2], [3, 4]])
        assert result == ["[1, 2]", "[3, 4]"]

    def test_mixed_types(self):
        result = _clean_list([42, 3.14, True, None, "text"])
        assert "42" in result
        assert "3.14" in result
        assert "True" in result
        assert "None" in result
        assert "text" in result

    def test_large_list(self):
        items = [f"item_{i}" for i in range(1000)]
        result = _clean_list(items)
        assert len(result) == 1000


# ---------------------------------------------------------------------------
# Preload adjacent lessons
# ---------------------------------------------------------------------------
class TestPreloadAdjacentLessons:
    """Test lesson preloading behavior."""

    def test_preload_adjacent(self, tmp_path):
        lessons = [{"id": f"l{i}", "title": f"L{i}", "path": f"l{i}.md"} for i in range(5)]
        data = {
            "tracks": [
                {
                    "id": "t1",
                    "title": "T1",
                    "modules": [{"id": "m1", "title": "M1", "lessons": lessons}],
                }
            ]
        }
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        for i in range(5):
            (md_dir / f"l{i}.md").write_text(f"Content {i}", encoding="utf-8")

        with patch("app.content_service.CONTENT_DIR", md_dir):
            cs.preload_adjacent_lessons("l2")
        # l1 and l3 should be cached
        assert "l1.md" in cs._markdown_cache
        assert "l3.md" in cs._markdown_cache

    def test_preload_first_lesson(self, tmp_path):
        lessons = [{"id": f"l{i}", "title": f"L{i}", "path": f"l{i}.md"} for i in range(3)]
        data = {
            "tracks": [
                {
                    "id": "t1",
                    "title": "T1",
                    "modules": [{"id": "m1", "title": "M1", "lessons": lessons}],
                }
            ]
        }
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        for i in range(3):
            (md_dir / f"l{i}.md").write_text(f"Content {i}", encoding="utf-8")

        with patch("app.content_service.CONTENT_DIR", md_dir):
            cs.preload_adjacent_lessons("l0")
        # l1 should be cached but not l-1
        assert "l1.md" in cs._markdown_cache

    def test_preload_nonexistent_lesson(self, tmp_path):
        data = {"tracks": []}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        # Should not raise
        cs.preload_adjacent_lessons("nonexistent")
