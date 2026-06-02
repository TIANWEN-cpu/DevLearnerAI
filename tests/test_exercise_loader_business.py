"""Tests for app.practice.exercise_loader -- load_exercises and fallback patching."""

import json
from unittest.mock import patch


class TestLoadExercises:
    """Test the load_exercises function with patched metadata."""

    def _make_exercise_json(self, exercises):
        return json.dumps({"exercises": exercises})

    def test_load_valid_exercises(self, tmp_path):
        from app.practice.exercise_loader import load_exercises

        data = self._make_exercise_json(
            [
                {
                    "id": "ex1",
                    "title": "Hello",
                    "track_id": "python",
                    "difficulty": "basic",
                    "prompt": "Write hello",
                    "lesson_id": "l1",
                    "hints": ["hint1"],
                    "starter_code": "print()",
                    "tests": [{"expected": "hello"}],
                }
            ]
        )
        meta = tmp_path / "exercises.json"
        meta.write_text(data, encoding="utf-8")

        with patch("app.practice.exercise_loader.get_exercise_fallbacks", return_value={}):
            result = load_exercises(meta)
        assert len(result) == 1
        assert result[0].id == "ex1"
        assert result[0].title == "Hello"

    def test_load_exercises_applies_fallback_for_corrupt_title(self, tmp_path):
        from app.practice.exercise_loader import load_exercises

        data = self._make_exercise_json(
            [
                {
                    "id": "ex1",
                    "title": "bad?title",
                    "track_id": "python",
                    "difficulty": "basic",
                    "prompt": "Write code",
                    "lesson_id": "l1",
                }
            ]
        )
        meta = tmp_path / "exercises.json"
        meta.write_text(data, encoding="utf-8")

        fallbacks = {"ex1": {"title": "Fixed Title"}}
        with patch("app.practice.exercise_loader.get_exercise_fallbacks", return_value=fallbacks):
            result = load_exercises(meta)
        assert result[0].title == "Fixed Title"

    def test_load_exercises_applies_fallback_for_corrupt_hints(self, tmp_path):
        from app.practice.exercise_loader import load_exercises

        data = self._make_exercise_json(
            [
                {
                    "id": "ex1",
                    "title": "Good Title",
                    "track_id": "python",
                    "difficulty": "basic",
                    "prompt": "Write code",
                    "lesson_id": "l1",
                    "hints": ["bad?hint"],
                }
            ]
        )
        meta = tmp_path / "exercises.json"
        meta.write_text(data, encoding="utf-8")

        fallbacks = {"ex1": {"hints": ["fixed hint"]}}
        with patch("app.practice.exercise_loader.get_exercise_fallbacks", return_value=fallbacks):
            result = load_exercises(meta)
        assert result[0].hints == ["fixed hint"]

    def test_load_exercises_applies_fallback_for_corrupt_starter_code(self, tmp_path):
        from app.practice.exercise_loader import load_exercises

        data = self._make_exercise_json(
            [
                {
                    "id": "ex1",
                    "title": "Good",
                    "track_id": "python",
                    "difficulty": "basic",
                    "prompt": "Write code",
                    "lesson_id": "l1",
                    "starter_code": "bad?code",
                }
            ]
        )
        meta = tmp_path / "exercises.json"
        meta.write_text(data, encoding="utf-8")

        fallbacks = {"ex1": {"starter_code": "fixed_code()"}}
        with patch("app.practice.exercise_loader.get_exercise_fallbacks", return_value=fallbacks):
            result = load_exercises(meta)
        assert result[0].starter_code == "fixed_code()"

    def test_load_exercises_applies_fallback_for_corrupt_tests(self, tmp_path):
        from app.practice.exercise_loader import load_exercises

        data = self._make_exercise_json(
            [
                {
                    "id": "ex1",
                    "title": "Good",
                    "track_id": "python",
                    "difficulty": "basic",
                    "prompt": "Write code",
                    "lesson_id": "l1",
                    "tests": [{"expected": "bad?expected"}],
                }
            ]
        )
        meta = tmp_path / "exercises.json"
        meta.write_text(data, encoding="utf-8")

        fallbacks = {"ex1": {"tests": [{"expected": "correct"}]}}
        with patch("app.practice.exercise_loader.get_exercise_fallbacks", return_value=fallbacks):
            result = load_exercises(meta)
        assert result[0].tests == [{"expected": "correct"}]

    def test_load_exercises_file_not_found(self, tmp_path):
        from app.practice.exercise_loader import load_exercises

        meta = tmp_path / "nonexistent.json"
        result = load_exercises(meta)
        assert result == []

    def test_load_exercises_invalid_json(self, tmp_path):
        from app.practice.exercise_loader import load_exercises

        meta = tmp_path / "bad.json"
        meta.write_text("not json", encoding="utf-8")
        result = load_exercises(meta)
        assert result == []

    def test_load_exercises_empty_list(self, tmp_path):
        from app.practice.exercise_loader import load_exercises

        data = self._make_exercise_json([])
        meta = tmp_path / "exercises.json"
        meta.write_text(data, encoding="utf-8")

        with patch("app.practice.exercise_loader.get_exercise_fallbacks", return_value={}):
            result = load_exercises(meta)
        assert result == []

    def test_load_exercises_no_fallback_needed(self, tmp_path):
        """Exercises with clean data should not be patched."""
        from app.practice.exercise_loader import load_exercises

        data = self._make_exercise_json(
            [
                {
                    "id": "ex1",
                    "title": "Clean Title",
                    "track_id": "python",
                    "difficulty": "basic",
                    "prompt": "Clean prompt",
                    "lesson_id": "l1",
                    "hints": ["clean hint"],
                    "starter_code": "clean_code()",
                }
            ]
        )
        meta = tmp_path / "exercises.json"
        meta.write_text(data, encoding="utf-8")

        with patch("app.practice.exercise_loader.get_exercise_fallbacks", return_value={}):
            result = load_exercises(meta)
        assert result[0].title == "Clean Title"
        assert result[0].hints == ["clean hint"]
        assert result[0].starter_code == "clean_code()"

    def test_load_exercises_fallback_for_corrupt_difficulty(self, tmp_path):
        from app.practice.exercise_loader import load_exercises

        data = self._make_exercise_json(
            [
                {
                    "id": "ex1",
                    "title": "Good",
                    "track_id": "python",
                    "difficulty": "ba?ic",
                    "prompt": "Write code",
                    "lesson_id": "l1",
                }
            ]
        )
        meta = tmp_path / "exercises.json"
        meta.write_text(data, encoding="utf-8")

        fallbacks = {"ex1": {"difficulty": "basic"}}
        with patch("app.practice.exercise_loader.get_exercise_fallbacks", return_value=fallbacks):
            result = load_exercises(meta)
        assert result[0].difficulty == "basic"

    def test_load_exercises_fallback_for_corrupt_prompt(self, tmp_path):
        from app.practice.exercise_loader import load_exercises

        data = self._make_exercise_json(
            [
                {
                    "id": "ex1",
                    "title": "Good",
                    "track_id": "python",
                    "difficulty": "basic",
                    "prompt": "bad?prompt",
                    "lesson_id": "l1",
                }
            ]
        )
        meta = tmp_path / "exercises.json"
        meta.write_text(data, encoding="utf-8")

        fallbacks = {"ex1": {"prompt": "fixed prompt"}}
        with patch("app.practice.exercise_loader.get_exercise_fallbacks", return_value=fallbacks):
            result = load_exercises(meta)
        assert result[0].prompt == "fixed prompt"
