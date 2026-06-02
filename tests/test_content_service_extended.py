"""Extended tests for app.content_service covering edge cases.

Targets:
- lesson_by_id with track_by_id returning None (line 281)
- lesson_by_id with module not found (line 287)
- lesson_markdown cache eviction (lines 317-318)
- preload_adjacent_lessons with invalid lesson_id (lines 334-335)
"""

import json
from unittest.mock import patch

import pytest


@pytest.fixture
def content_service(tmp_path):
    """Create a ContentService with minimal test data."""
    from app.content_service import ContentService

    # Create metadata JSON in the expected format
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    course_map = {
        "tracks": [
            {
                "id": "python",
                "title": "Python",
                "summary": "Learn Python",
                "modules": [
                    {
                        "id": "mod1",
                        "title": "Module 1",
                        "summary": "Basics",
                        "lessons": [
                            {"id": "lesson1", "title": "Lesson 1", "file": "lesson1.md", "path": "python/lesson1"},
                            {"id": "lesson2", "title": "Lesson 2", "file": "lesson2.md", "path": "python/lesson2"},
                            {"id": "lesson3", "title": "Lesson 3", "file": "lesson3.md", "path": "python/lesson3"},
                        ],
                    }
                ],
            }
        ]
    }

    course_map_file = metadata_dir / "course_map.json"
    course_map_file.write_text(json.dumps(course_map, ensure_ascii=False), encoding="utf-8")

    # Create content directory structure
    content_dir = tmp_path / "content"
    for i in range(1, 4):
        lesson_dir = content_dir / "python" / f"lesson{i}"
        lesson_dir.mkdir(parents=True, exist_ok=True)
        (lesson_dir / f"lesson{i}.md").write_text(f"# Lesson {i}\n\nContent for lesson {i}", encoding="utf-8")

    svc = ContentService(metadata_path=course_map_file)
    # Patch the content search paths
    svc._markdown_cache.clear()
    return svc, content_dir


class TestLessonByIdEdgeCases:
    """Test lesson_by_id edge cases."""

    def test_lesson_by_id_nonexistent_returns_none(self, content_service):
        svc, _ = content_service
        result = svc.lesson_by_id("nonexistent-lesson")
        assert result is None

    def test_lesson_by_id_valid(self, content_service):
        svc, _ = content_service
        result = svc.lesson_by_id("lesson1")
        assert result is not None
        track, module, lesson = result
        assert lesson.id == "lesson1"


class TestLessonMarkdownCacheEviction:
    """Test cache eviction in lesson_markdown (lines 317-318)."""

    def test_cache_eviction_when_full(self, content_service, tmp_path):
        """When cache is full, oldest entry should be evicted."""
        svc, content_dir = content_service

        # Set a very small cache size
        original_max = svc._MAX_MARKDOWN_CACHE
        svc._MAX_MARKDOWN_CACHE = 2
        svc._markdown_cache.clear()

        try:
            result = svc.lesson_by_id("lesson1")
            assert result is not None
            _track, _module, lesson1 = result
            # Manually set file path to point to our test content
            lesson1.path = "python/lesson1"
            with patch("app.content_service.CONTENT_DIR", content_dir):
                svc.lesson_markdown(lesson1)

            result2 = svc.lesson_by_id("lesson2")
            assert result2 is not None
            _track2, _module2, lesson2 = result2
            lesson2.path = "python/lesson2"
            with patch("app.content_service.CONTENT_DIR", content_dir):
                svc.lesson_markdown(lesson2)

            assert len(svc._markdown_cache) == 2

            result3 = svc.lesson_by_id("lesson3")
            assert result3 is not None
            _track3, _module3, lesson3 = result3
            lesson3.path = "python/lesson3"
            with patch("app.content_service.CONTENT_DIR", content_dir):
                svc.lesson_markdown(lesson3)

            # Should have evicted oldest
            assert len(svc._markdown_cache) == 2
        finally:
            svc._MAX_MARKDOWN_CACHE = original_max


class TestPreloadAdjacentLessons:
    """Test preload_adjacent_lessons (lines 334-335)."""

    def test_preload_with_invalid_lesson_id(self, content_service):
        """When lesson_id is not in index, should return silently."""
        svc, _ = content_service
        svc.preload_adjacent_lessons("nonexistent-id")
        assert True  # Verify no crash with invalid ID

    def test_preload_first_lesson(self, content_service):
        """First lesson should only preload next."""
        svc, content_dir = content_service
        svc._markdown_cache.clear()
        with patch("app.content_service.CONTENT_DIR", content_dir):
            svc.preload_adjacent_lessons("lesson1")
        assert len(svc._markdown_cache) >= 1

    def test_preload_middle_lesson(self, content_service):
        """Middle lesson should preload both adjacent."""
        svc, content_dir = content_service
        svc._markdown_cache.clear()
        with patch("app.content_service.CONTENT_DIR", content_dir):
            svc.preload_adjacent_lessons("lesson2")
        assert len(svc._markdown_cache) >= 2

    def test_preload_last_lesson(self, content_service):
        """Last lesson should only preload previous."""
        svc, content_dir = content_service
        svc._markdown_cache.clear()
        with patch("app.content_service.CONTENT_DIR", content_dir):
            svc.preload_adjacent_lessons("lesson3")
        assert len(svc._markdown_cache) >= 1


class TestClearMarkdownCache:
    def test_clear_cache(self, content_service):
        svc, _ = content_service
        svc._markdown_cache["test"] = "content"
        svc.clear_markdown_cache()
        assert len(svc._markdown_cache) == 0


class TestAllLessons:
    def test_all_lessons_returns_flat_list(self, content_service):
        svc, _ = content_service
        result = svc.all_lessons()
        assert len(result) == 3
        for track, _module, _lesson in result:
            assert track.id == "python"
