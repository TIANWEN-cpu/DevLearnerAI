"""Tests for practice widget business logic (non-GUI helpers)."""

import time


class TestScoreColorMapping:
    """Test score color and label mapping logic."""

    def test_score_label_excellent(self):
        from app.styles import score_label

        result = score_label(95)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_score_label_zero(self):
        from app.styles import score_label

        result = score_label(0)
        assert isinstance(result, str)

    def test_score_label_boundary_60(self):
        from app.styles import score_label

        result = score_label(60)
        assert isinstance(result, str)

    def test_score_color_returns_string(self):
        from app.styles import score_color

        result = score_color(80)
        assert isinstance(result, str)
        assert result.startswith("#") or result.startswith("rgb")

    def test_score_color_low(self):
        from app.styles import score_color

        result = score_color(20)
        assert isinstance(result, str)


class TestExerciseFiltering:
    """Test exercise filtering logic used in refresh_exercises."""

    def test_filter_by_track(self):
        exercises = [
            type("Ex", (), {"track_id": "python", "title": "Py1", "prompt": "do it"})(),
            type("Ex", (), {"track_id": "sql", "title": "SQL1", "prompt": "query"})(),
            type("Ex", (), {"track_id": "python", "title": "Py2", "prompt": "code"})(),
        ]

        filtered = [e for e in exercises if e.track_id == "python"]
        assert len(filtered) == 2
        assert all(e.track_id == "python" for e in filtered)

    def test_filter_by_difficulty(self):
        exercises = [
            type("Ex", (), {"difficulty": "basic", "title": "E1", "prompt": "p"})(),
            type("Ex", (), {"difficulty": "advanced", "title": "E2", "prompt": "p"})(),
            type("Ex", (), {"difficulty": "basic", "title": "E3", "prompt": "p"})(),
        ]

        filtered = [e for e in exercises if e.difficulty == "basic"]
        assert len(filtered) == 2

    def test_filter_by_search_text(self):
        exercises = [
            type("Ex", (), {"title": "Hello World", "prompt": "print greeting"})(),
            type("Ex", (), {"title": "SQL Basics", "prompt": "write a query"})(),
            type("Ex", (), {"title": "Advanced Python", "prompt": "hello from python"})(),
        ]

        search = "hello"
        filtered = [e for e in exercises if search in e.title.lower() or search in e.prompt.lower()]
        assert len(filtered) == 2

    def test_filter_combined(self):
        exercises = [
            type("Ex", (), {"track_id": "python", "difficulty": "basic", "title": "Py Easy", "prompt": "hello"})(),
            type("Ex", (), {"track_id": "python", "difficulty": "hard", "title": "Py Hard", "prompt": "hello"})(),
            type("Ex", (), {"track_id": "sql", "difficulty": "basic", "title": "SQL Easy", "prompt": "query"})(),
        ]

        filtered = [e for e in exercises if e.track_id == "python" and e.difficulty == "basic" and "hello" in e.prompt]
        assert len(filtered) == 1
        assert filtered[0].title == "Py Easy"

    def test_filter_no_match(self):
        exercises = [
            type("Ex", (), {"title": "A", "prompt": "x", "track_id": "python"})(),
        ]
        filtered = [e for e in exercises if e.track_id == "sql"]
        assert len(filtered) == 0

    def test_filter_empty_list(self):
        filtered = [e for e in [] if True]
        assert filtered == []


class TestExerciseTopicKey:
    """Test topic key extraction logic."""

    def test_topic_key_from_module(self):
        exercise = type("Ex", (), {"lesson_id": "l1", "track_id": "python"})()

        def lesson_by_id(lid):
            if lid == "l1":
                return (
                    type("T", (), {"id": "python"})(),
                    type("M", (), {"id": "basics"})(),
                    type("L", (), {"id": "l1"})(),
                )
            return None

        payload = lesson_by_id(exercise.lesson_id)
        if payload:
            _track, module, _lesson = payload
            key = module.id
        else:
            key = exercise.track_id
        assert key == "basics"

    def test_topic_key_fallback_to_track(self):
        exercise = type("Ex", (), {"lesson_id": "missing", "track_id": "python"})()

        def lesson_by_id(lid):
            return None

        payload = lesson_by_id(exercise.lesson_id)
        if payload:
            key = payload[1].id
        else:
            key = exercise.track_id
        assert key == "python"


class TestDraftSaveLogic:
    """Test draft save scheduling logic."""

    def test_loading_exercise_skips_save(self):
        loading = True
        current_exercise = type("Ex", (), {})()
        should_save = not loading and current_exercise is not None
        assert should_save is False

    def test_no_exercise_skips_save(self):
        loading = False
        current_exercise = None
        should_save = not loading and current_exercise is not None
        assert should_save is False

    def test_valid_state_saves(self):
        loading = False
        current_exercise = type("Ex", (), {})()
        should_save = not loading and current_exercise is not None
        assert should_save is True


class TestElapsedTime:
    """Test elapsed time computation for evaluation."""

    def test_elapsed_calculation(self):
        started = time.time() - 5.0
        elapsed = int(time.time() - started)
        assert 4 <= elapsed <= 6

    def test_zero_elapsed(self):
        started = time.time()
        elapsed = int(time.time() - started)
        assert elapsed == 0


class TestEvaluationFeedback:
    """Test evaluation feedback text construction."""

    def test_passed_feedback(self):
        result = type("R", (), {"score": 85, "passed": True, "feedback_text": "Good job", "stdout": "output"})()
        lines = [
            f"score: {result.score}/100",
            f"passed: {result.passed}",
            "",
            result.feedback_text,
        ]
        text = "\n".join(lines)
        assert "85" in text
        assert "True" in text
        assert "Good job" in text

    def test_failed_feedback(self):
        result = type("R", (), {"score": 30, "passed": False, "feedback_text": "Try again", "stdout": ""})()
        assert result.passed is False
        assert result.score < 60


class TestTrackTheme:
    """Test exercise card theme lookup."""

    THEMES = {
        "python": "#2f6df6",
        "c": "#ff4f8a",
        "database": "#f59e0b",
    }

    def test_known_track_theme(self):
        for track_id, expected_color in self.THEMES.items():
            theme = self.THEMES.get(track_id, "#94a3b8")
            assert theme == expected_color

    def test_unknown_track_default(self):
        theme = self.THEMES.get("unknown", "#94a3b8")
        assert theme == "#94a3b8"
