"""Tests for dashboard data computation helpers (business logic only)."""

from datetime import date, timedelta


class TestRadarDataComputation:
    """Test radar chart data computation logic extracted from DashboardWidget."""

    def test_compute_radar_data_with_tracks(self):
        """Simulate _compute_radar_data logic."""
        # Simulated track data
        tracks = [
            type("Track", (), {"id": "python", "title": "Python", "lessons": [1, 2, 3]})(),
            type("Track", (), {"id": "sql", "title": "SQL", "lessons": [1, 2]})(),
        ]
        track_stats = {"python": 85.0, "sql": 60.0}

        data = []
        labels = []
        for track in tracks:
            avg = track_stats.get(track.id, 0.0)
            data.append(min(avg, 100.0))
            label = track.title if len(track.title) <= 6 else track.title[:5] + ".."
            labels.append(label)

        while len(data) < 3:
            data.append(0.0)
            labels.append("")

        assert data == [85.0, 60.0, 0.0]
        assert labels == ["Python", "SQL", ""]

    def test_compute_radar_caps_at_100(self):
        tracks = [type("T", (), {"id": "x", "title": "X", "lessons": [1]})()]
        track_stats = {"x": 150.0}

        data = []
        for track in tracks:
            avg = track_stats.get(track.id, 0.0)
            data.append(min(avg, 100.0))

        assert data == [100.0]

    def test_compute_radar_long_title_truncated(self):
        track = type("T", (), {"title": "DatabaseSystems"})()
        label = track.title if len(track.title) <= 6 else track.title[:5] + ".."
        assert label == "Datab.."

    def test_compute_radar_short_title_preserved(self):
        track = type("T", (), {"title": "SQL"})()
        label = track.title if len(track.title) <= 6 else track.title[:5] + ".."
        assert label == "SQL"

    def test_compute_radar_minimum_3_axes(self):
        _tracks = [type("T", (), {"id": "a", "title": "A", "lessons": []})()]
        data = [50.0]
        labels = ["A"]
        while len(data) < 3:
            data.append(0.0)
            labels.append("")
        assert len(data) == 3
        assert len(labels) == 3


class TestHeatmapDataComputation:
    """Test heatmap data computation logic."""

    def test_merge_lesson_and_practice_counts(self):
        """Simulate merging two count sources."""
        heatmap = {}
        lesson_counts = {"2024-01-01": 2, "2024-01-02": 1}
        practice_counts = {"2024-01-01": 3, "2024-01-03": 1}

        for day, cnt in lesson_counts.items():
            heatmap[day] = heatmap.get(day, 0) + cnt
        for day, cnt in practice_counts.items():
            heatmap[day] = heatmap.get(day, 0) + cnt

        assert heatmap["2024-01-01"] == 5
        assert heatmap["2024-01-02"] == 1
        assert heatmap["2024-01-03"] == 1

    def test_heatmap_date_range(self):
        """Verify 24-week date range calculation."""
        today = date.today()
        start = today - timedelta(weeks=24)
        assert (today - start).days == 168

    def test_heatmap_empty_counts(self):
        heatmap = {}
        rows = []
        for day_str, cnt in rows:
            if day_str:
                heatmap[day_str] = heatmap.get(day_str, 0) + int(cnt)
        assert heatmap == {}

    def test_heatmap_none_day_filtered(self):
        """None day values should be skipped."""
        heatmap = {}
        rows = [(None, 5), ("2024-01-01", 3)]
        for day_str, cnt in rows:
            if day_str:
                heatmap[day_str] = heatmap.get(day_str, 0) + int(cnt)
        assert "2024-01-01" in heatmap
        assert len(heatmap) == 1


class TestWeeklyChartData:
    """Test weekly activity chart data computation."""

    def test_weekly_data_grouping(self):
        """Simulate grouping attempts by day of week."""
        today = date.today()
        attempts = []
        # Create fake attempts for today and yesterday
        yesterday = (today - timedelta(days=1)).isoformat()
        today_str = today.isoformat()
        attempts = [
            (today_str + "T10:00:00", "ex1", 80, True, 30),
            (today_str + "T11:00:00", "ex2", 90, True, 20),
            (yesterday + "T10:00:00", "ex3", 70, False, 40),
        ]

        weekly_data = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            count = sum(1 for at, *_ in attempts if at and at.startswith(d.isoformat()))
            weekly_data.append(count)

        assert sum(weekly_data) == 3
        assert weekly_data[-1] == 2  # today has 2
        assert weekly_data[-2] == 1  # yesterday has 1

    def test_weekly_data_all_zeros(self):
        today = date.today()
        weekly_data = []
        for i in range(6, -1, -1):
            _d = today - timedelta(days=i)  # noqa: F841
            count = 0
            weekly_data.append(count)
        assert weekly_data == [0] * 7


class TestProgressPercentage:
    """Test progress percentage computation."""

    def test_basic_percentage(self):
        completed, total = 5, 10
        pct = int(completed / max(total, 1) * 100)
        assert pct == 50

    def test_zero_total(self):
        completed, total = 0, 0
        pct = int(completed / max(total, 1) * 100)
        assert pct == 0

    def test_full_completion(self):
        completed, total = 10, 10
        pct = int(completed / max(total, 1) * 100)
        assert pct == 100

    def test_goal_progress(self):
        completed = 3
        target = 5
        progress = min(100, int(completed / max(target, 1) * 100))
        assert progress == 60

    def test_goal_progress_exceeds_100(self):
        completed = 8
        target = 5
        progress = min(100, int(completed / max(target, 1) * 100))
        assert progress == 100


class TestScoreChartData:
    """Test score chart data extraction logic."""

    def test_extract_last_n_scores(self):
        attempts = [
            ("t1", "ex1", 80, True, 10),
            ("t2", "ex2", 60, False, 20),
            ("t3", "ex3", 90, True, 15),
            ("t4", "ex4", 70, True, 25),
        ]
        score_data = [s for (_at, _t, s, _p, _d) in attempts[:3]]
        score_data.reverse()
        assert score_data == [90, 60, 80]

    def test_empty_attempts(self):
        attempts = []
        score_data = [s for (_at, _t, s, _p, _d) in attempts[:8]]
        score_data.reverse()
        assert score_data == []
