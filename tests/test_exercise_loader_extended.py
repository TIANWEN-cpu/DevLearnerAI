"""Extended tests for app.practice.exercise_loader covering error paths.

Targets:
- load_json_resource FileNotFoundError (line 24-26)
- load_json_resource JSONDecodeError (lines 27-29)
- needs_fallback (line 51)
"""

from unittest.mock import patch


class TestLoadJsonResource:
    """Test load_json_resource error handling (lines 22-29)."""

    def test_file_not_found_returns_empty_dict(self, tmp_path):
        from app.practice.exercise_loader import load_json_resource

        with patch("app.practice.exercise_loader.METADATA_DIR", tmp_path):
            result = load_json_resource("nonexistent.json")
        assert result == {}

    def test_invalid_json_returns_empty_dict(self, tmp_path):
        from app.practice.exercise_loader import load_json_resource

        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json content", encoding="utf-8")

        with patch("app.practice.exercise_loader.METADATA_DIR", tmp_path):
            result = load_json_resource("bad.json")
        assert result == {}

    def test_valid_json_returns_dict(self, tmp_path):
        from app.practice.exercise_loader import load_json_resource

        good_file = tmp_path / "good.json"
        good_file.write_text('{"key": "value"}', encoding="utf-8")

        with patch("app.practice.exercise_loader.METADATA_DIR", tmp_path):
            result = load_json_resource("good.json")
        assert result == {"key": "value"}


class TestNeedsFallback:
    """Test needs_fallback function (line 51)."""

    def test_returns_true_for_question_mark(self):
        from app.practice.exercise_loader import needs_fallback

        assert needs_fallback("some?text") is True
        assert needs_fallback("?") is True

    def test_returns_false_for_normal_text(self):
        from app.practice.exercise_loader import needs_fallback

        assert needs_fallback("normal text") is False
        assert needs_fallback("") is False


class TestGetExerciseFallbacks:
    """Test get_exercise_fallbacks cached function."""

    def test_returns_dict(self):
        from app.practice.exercise_loader import get_exercise_fallbacks

        result = get_exercise_fallbacks()
        assert isinstance(result, dict)


class TestGetSqlQueryFixtures:
    """Test get_sql_query_fixtures cached function."""

    def test_returns_dict_with_tuples(self):
        from app.practice.exercise_loader import get_sql_query_fixtures

        result = get_sql_query_fixtures()
        assert isinstance(result, dict)
        # Check that expected_rows are tuples
        for _key, fixture in result.items():
            if "expected_rows" in fixture:
                for row in fixture["expected_rows"]:
                    assert isinstance(row, tuple)
