"""Tests for app.content_service -- content parsing, caching, discovery.

Covers:
- Helper functions: _looks_corrupt, _clean_text, _clean_list
- Dataclass properties: Module.key, Track.lessons
- ContentService: lazy loading, cache, track/module/lesson discovery, error handling
"""

import json
from pathlib import Path
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
# _looks_corrupt
# ---------------------------------------------------------------------------
class TestLooksCorrupt:
    """Detect garbled / mojibake text."""

    def test_empty_string_is_corrupt(self):
        assert _looks_corrupt("") is True

    def test_none_like_falsy_is_corrupt(self):
        assert _looks_corrupt("") is True

    def test_normal_text_is_not_corrupt(self):
        assert _looks_corrupt("Python 基础入门") is False

    def test_question_marks_corrupt(self):
        assert _looks_corrupt("what???") is True

    def test_single_double_question_mark_corrupt(self):
        assert _looks_corrupt("hello??world") is True

    def test_kun_char_corrupt(self):
        assert _looks_corrupt("锟斤拷") is True

    def test_replacement_char_corrupt(self):
        assert _looks_corrupt("text�end") is True

    def test_xuan_char_corrupt(self):
        assert _looks_corrupt("璇") is True

    def test_zhou_char_corrupt(self):
        assert _looks_corrupt("妯") is True

    def test_deng_char_corrupt(self):
        assert _looks_corrupt("鍩") is True

    def test_qi_char_corrupt(self):
        assert _looks_corrupt("绮") is True

    def test_lu_char_not_corrupt(self):
        """路 is a common Chinese character (road), not mojibake."""
        assert _looks_corrupt("路") is False

    def test_mixed_text_with_corrupt_token(self):
        assert _looks_corrupt("hello ??? world") is True


# ---------------------------------------------------------------------------
# _clean_text
# ---------------------------------------------------------------------------
class TestCleanText:
    """Clean text with fallback for corrupt or missing values."""

    def test_normal_text_returned(self):
        assert _clean_text("hello", "fallback") == "hello"

    def test_stripped(self):
        assert _clean_text("  hello  ", "fallback") == "hello"

    def test_empty_returns_fallback(self):
        assert _clean_text("", "fallback") == "fallback"

    def test_corrupt_returns_fallback(self):
        assert _clean_text("???", "fallback") == "fallback"

    def test_non_string_returns_fallback(self):
        assert _clean_text(123, "fallback") == "fallback"

    def test_none_returns_fallback(self):
        assert _clean_text(None, "fallback") == "fallback"

    def test_list_returns_fallback(self):
        assert _clean_text([1, 2], "fallback") == "fallback"


# ---------------------------------------------------------------------------
# _clean_list
# ---------------------------------------------------------------------------
class TestCleanList:
    """Clean list of strings, filtering out corrupt entries."""

    def test_normal_list(self):
        assert _clean_list(["a", "b", "c"]) == ["a", "b", "c"]

    def test_corrupt_items_filtered(self):
        assert _clean_list(["good", "???", "also good"]) == ["good", "also good"]

    def test_empty_list_returns_fallback(self):
        assert _clean_list([], ["fallback"]) == ["fallback"]

    def test_all_corrupt_returns_fallback(self):
        assert _clean_list(["???", "锟"]) == []

    def test_non_list_returns_fallback(self):
        assert _clean_list("not a list", ["fallback"]) == ["fallback"]

    def test_none_input_returns_fallback(self):
        assert _clean_list(None, ["fb"]) == ["fb"]

    def test_default_fallback_is_empty(self):
        assert _clean_list([]) == []

    def test_non_string_items_converted(self):
        assert _clean_list([42, True]) == ["42", "True"]

    def test_mixed_corrupt_and_non_string(self):
        result = _clean_list([42, "???", "hello"])
        assert result == ["42", "hello"]


# ---------------------------------------------------------------------------
# Dataclass properties
# ---------------------------------------------------------------------------
class TestModuleKey:
    """Module.key should return module id."""

    def test_key_equals_id(self):
        m = Module(id="mod1", title="M", summary="S")
        assert m.key == "mod1"


class TestTrackLessons:
    """Track.lessons should flatten lessons across modules."""

    def test_flattens_lessons(self):
        l1 = Lesson(id="l1", title="L1", summary="", path="", difficulty="", estimated_minutes=10)
        l2 = Lesson(id="l2", title="L2", summary="", path="", difficulty="", estimated_minutes=10)
        l3 = Lesson(id="l3", title="L3", summary="", path="", difficulty="", estimated_minutes=10)
        m1 = Module(id="m1", title="M1", summary="", lessons=[l1, l2])
        m2 = Module(id="m2", title="M2", summary="", lessons=[l3])
        track = Track(id="t1", title="T", icon="", summary="", modules=[m1, m2])
        assert track.lessons == [l1, l2, l3]

    def test_empty_modules(self):
        track = Track(id="t1", title="T", icon="", summary="", modules=[])
        assert track.lessons == []

    def test_modules_with_no_lessons(self):
        m = Module(id="m1", title="M", summary="", lessons=[])
        track = Track(id="t1", title="T", icon="", summary="", modules=[m])
        assert track.lessons == []


# ---------------------------------------------------------------------------
# ContentService -- _discover_tracks
# ---------------------------------------------------------------------------
class TestDiscoverTracks:
    """Track discovery from metadata file."""

    def test_missing_file_returns_empty(self, tmp_path):
        cs = ContentService(metadata_path=tmp_path / "nonexistent.json")
        assert cs._tracks_index == []

    def test_invalid_json_returns_empty(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("not valid json {{{", encoding="utf-8")
        cs = ContentService(metadata_path=p)
        assert cs._tracks_index == []

    def test_valid_json_extracts_tracks(self, tmp_path):
        data = {"tracks": [{"id": "t1", "title": "Track 1"}]}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        assert len(cs._tracks_index) == 1
        assert cs._tracks_index[0]["id"] == "t1"

    def test_empty_tracks_list(self, tmp_path):
        data = {"tracks": []}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        assert cs._tracks_index == []

    def test_missing_tracks_key(self, tmp_path):
        data = {"other": "data"}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        assert cs._tracks_index == []


# ---------------------------------------------------------------------------
# ContentService -- _build_track
# ---------------------------------------------------------------------------
class TestBuildTrack:
    """Track building from raw dict data."""

    @pytest.fixture
    def service(self, tmp_path):
        p = tmp_path / "map.json"
        p.write_text(json.dumps({"tracks": []}), encoding="utf-8")
        return ContentService(metadata_path=p)

    def test_full_track_data(self, service):
        track_data = {
            "id": "py",
            "title": "Python",
            "icon": "🐍",
            "summary": "Learn Python",
            "modules": [
                {
                    "id": "basics",
                    "title": "Basics",
                    "summary": "Basic concepts",
                    "lessons": [
                        {
                            "id": "l1",
                            "title": "Variables",
                            "summary": "About variables",
                            "path": "py/variables.md",
                            "difficulty": "beginner",
                            "estimated_minutes": 15,
                            "tags": ["vars"],
                            "prerequisites": [],
                            "outcomes": ["understand vars"],
                        }
                    ],
                }
            ],
        }
        track = service._build_track(track_data)
        assert track.id == "py"
        assert track.title == "Python"
        assert track.icon == "🐍"
        assert len(track.modules) == 1
        assert track.modules[0].lessons[0].id == "l1"

    def test_missing_fields_use_defaults(self, service):
        track_data = {}
        track = service._build_track(track_data)
        assert track.id == "track"
        assert track.title == "未命名主线"
        assert track.icon == "📘"
        assert "按主线推进" in track.summary
        assert track.modules == []

    def test_corrupt_title_gets_fallback(self, service):
        track_data = {"title": "???", "modules": []}
        track = service._build_track(track_data)
        assert track.title == "未命名主线"

    def test_lesson_missing_fields_use_defaults(self, service):
        track_data = {"modules": [{"lessons": [{}]}]}
        track = service._build_track(track_data)
        lesson = track.modules[0].lessons[0]
        assert lesson.id == "lesson"
        assert lesson.title == "未命名课程"
        assert lesson.estimated_minutes == 25
        assert lesson.difficulty == "基础"

    def test_module_missing_fields_use_defaults(self, service):
        track_data = {"modules": [{}]}
        track = service._build_track(track_data)
        module = track.modules[0]
        assert module.id == "module"
        assert module.title == "未命名模块"


# ---------------------------------------------------------------------------
# ContentService -- caching and lazy loading
# ---------------------------------------------------------------------------
class TestContentServiceCaching:
    """Cache behavior for loaded tracks."""

    def _make_service(self, tmp_path, tracks_data):
        data = {"tracks": tracks_data}
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return ContentService(metadata_path=p)

    def test_tracks_property_loads_and_caches(self, tmp_path):
        tracks = [{"id": "t1", "title": "T1", "modules": []}]
        cs = self._make_service(tmp_path, tracks)
        assert "t1" not in cs._cache  # not yet loaded
        result = cs.tracks
        assert len(result) == 1
        assert "t1" in cs._cache

    def test_tracks_returns_cached_on_second_access(self, tmp_path):
        tracks = [{"id": "t1", "title": "T1", "modules": []}]
        cs = self._make_service(tmp_path, tracks)
        first = cs.tracks
        second = cs.tracks
        assert first[0] is second[0]  # same object

    def test_track_by_id_caches(self, tmp_path):
        tracks = [{"id": "t1", "title": "T1", "modules": []}]
        cs = self._make_service(tmp_path, tracks)
        track = cs.track_by_id("t1")
        assert track is not None
        assert track.id == "t1"
        # second call should return cached
        assert cs.track_by_id("t1") is track

    def test_track_by_id_not_found(self, tmp_path):
        tracks = [{"id": "t1", "title": "T1", "modules": []}]
        cs = self._make_service(tmp_path, tracks)
        assert cs.track_by_id("nonexistent") is None


# ---------------------------------------------------------------------------
# ContentService -- lesson discovery
# ---------------------------------------------------------------------------
class TestLessonDiscovery:
    """Lesson lookup and enumeration."""

    def _make_service(self, tmp_path):
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
                                {"id": "l1", "title": "L1", "path": "l1.md"},
                                {"id": "l2", "title": "L2", "path": "l2.md"},
                            ],
                        }
                    ],
                },
                {
                    "id": "t2",
                    "title": "T2",
                    "modules": [
                        {
                            "id": "m2",
                            "title": "M2",
                            "lessons": [
                                {"id": "l3", "title": "L3", "path": "l3.md"},
                            ],
                        }
                    ],
                },
            ]
        }
        p = tmp_path / "map.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return ContentService(metadata_path=p)

    def test_lesson_by_id_found(self, tmp_path):
        cs = self._make_service(tmp_path)
        result = cs.lesson_by_id("l2")
        assert result is not None
        track, module, lesson = result
        assert track.id == "t1"
        assert module.id == "m1"
        assert lesson.id == "l2"

    def test_lesson_by_id_not_found(self, tmp_path):
        cs = self._make_service(tmp_path)
        assert cs.lesson_by_id("nonexistent") is None

    def test_all_lessons_returns_all(self, tmp_path):
        cs = self._make_service(tmp_path)
        all_l = cs.all_lessons()
        assert len(all_l) == 3
        ids = [lesson.id for _, _, lesson in all_l]
        assert ids == ["l1", "l2", "l3"]

    def test_all_lessons_empty_tracks(self, tmp_path):
        p = tmp_path / "map.json"
        p.write_text(json.dumps({"tracks": []}), encoding="utf-8")
        cs = ContentService(metadata_path=p)
        assert cs.all_lessons() == []


# ---------------------------------------------------------------------------
# ContentService -- lesson_markdown
# ---------------------------------------------------------------------------
class TestLessonMarkdown:
    """Reading lesson markdown files with error handling."""

    @pytest.fixture
    def service(self, tmp_path):
        p = tmp_path / "map.json"
        p.write_text(json.dumps({"tracks": []}), encoding="utf-8")
        return ContentService(metadata_path=p)

    def test_success(self, service, tmp_path):
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        md_file = md_dir / "lesson.md"
        md_file.write_text("# Hello", encoding="utf-8")

        lesson = Lesson(id="l1", title="L1", summary="", path="lesson.md", difficulty="", estimated_minutes=10)
        with patch("app.content_service.CONTENT_DIR", md_dir):
            result = service.lesson_markdown(lesson)
        assert result == "# Hello"

    def test_file_not_found(self, service, tmp_path):
        lesson = Lesson(id="l1", title="L1", summary="", path="missing.md", difficulty="", estimated_minutes=10)
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        with patch("app.content_service.CONTENT_DIR", md_dir):
            result = service.lesson_markdown(lesson)
        assert "文档文件暂时缺失" in result
        assert "L1" in result

    def test_other_exception(self, service, tmp_path):
        lesson = Lesson(id="l1", title="L1", summary="", path="lesson.md", difficulty="", estimated_minutes=10)
        md_dir = tmp_path / "content"
        md_dir.mkdir()
        # Create a directory with the lesson name to trigger IsADirectoryError-like behavior
        (md_dir / "lesson.md").mkdir()
        with patch("app.content_service.CONTENT_DIR", md_dir):
            result = service.lesson_markdown(lesson)
        # On Windows, reading a directory may raise PermissionError or similar
        assert "加载文档时出现错误" in result or "文档文件暂时缺失" in result


# ---------------------------------------------------------------------------
# ContentService -- default metadata_path
# ---------------------------------------------------------------------------
class TestContentServiceDefaultPath:
    """Test that ContentService uses METADATA_DIR / course_map.json by default."""

    def test_default_path(self):
        with patch("app.content_service.METADATA_DIR", Path("/fake/metadata")):
            cs = ContentService()
            assert cs.metadata_path == Path("/fake/metadata/course_map.json")
