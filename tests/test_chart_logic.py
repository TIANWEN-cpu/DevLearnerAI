"""Tests for app.widgets.charts -- chart data computation business logic.

Tests internal geometry computation, data handling, and edge cases.
Every test asserts specific values -- no empty tests.
"""

import math

from app.widgets.charts.bar_chart import BarChart

# Import after conftest has mocked PyQt5
from app.widgets.charts.line_chart import LineChart
from app.widgets.charts.radar_chart import _MAX_VALUE, RadarChart

# ---------------------------------------------------------------------------
# Helper: mock widget dimensions for geometry tests
# ---------------------------------------------------------------------------


def _make_chart_with_size(chart_cls, data=None, labels=None, width=400, height=300, **kwargs):
    """Create a chart widget with mocked width/height for geometry testing."""
    chart = chart_cls(data=data, labels=labels, **kwargs)
    chart.width = lambda: width
    chart.height = lambda: height
    return chart


# ===========================================================================
# LineChart tests
# ===========================================================================


class TestLineChartEmptyData:
    """LineChart behavior with no data points."""

    def test_empty_data_points_list(self):
        chart = _make_chart_with_size(LineChart)
        chart._compute_points()
        assert chart._points == []

    def test_set_data_with_none(self):
        chart = _make_chart_with_size(LineChart)
        chart.set_data(None)
        assert chart._data == []
        assert chart._labels == []

    def test_set_data_with_empty_list(self):
        chart = _make_chart_with_size(LineChart)
        chart.set_data([], labels=[])
        assert chart._data == []
        assert chart._labels == []


class TestLineChartSinglePoint:
    """LineChart with a single data point."""

    def test_single_point_computed(self):
        chart = _make_chart_with_size(LineChart, data=[50.0], labels=["A"])
        chart._compute_points()
        assert len(chart._points) == 1

    def test_single_point_x_is_at_left_margin(self):
        chart = _make_chart_with_size(LineChart, data=[50.0], width=400, height=300)
        chart._compute_points()
        # When n=1, max(n-1, 1) = 1, so x = rect.x() + 0 * rect.width() = rect.x()
        pt = chart._points[0]
        rect = chart._chart_rect()
        assert pt.x() == rect.x()

    def test_single_point_y_value(self):
        chart = _make_chart_with_size(LineChart, data=[100.0], width=400, height=300)
        chart._compute_points()
        rect = chart._chart_rect()
        pt = chart._points[0]
        # max_val = max(100, 1) * 1.1 = 110
        # y = bottom - (100/110) * height
        max_val = 100.0 * 1.1
        expected_y = rect.bottom() - (100.0 / max_val) * rect.height()
        assert abs(pt.y() - expected_y) < 0.01


class TestLineChartMultiplePoints:
    """LineChart with multiple data points -- verify geometry."""

    def test_two_points_computed(self):
        chart = _make_chart_with_size(LineChart, data=[10.0, 20.0], labels=["A", "B"])
        chart._compute_points()
        assert len(chart._points) == 2

    def test_points_are_left_to_right(self):
        chart = _make_chart_with_size(LineChart, data=[10.0, 20.0, 30.0], width=400)
        chart._compute_points()
        assert chart._points[0].x() < chart._points[1].x()
        assert chart._points[1].x() < chart._points[2].x()

    def test_higher_value_means_lower_y(self):
        """In screen coordinates, lower y = higher on screen."""
        chart = _make_chart_with_size(LineChart, data=[10.0, 100.0], width=400, height=300)
        chart._compute_points()
        # 100 > 10, so its y should be smaller (higher on screen)
        assert chart._points[1].y() < chart._points[0].y()

    def test_equal_values_same_y(self):
        chart = _make_chart_with_size(LineChart, data=[50.0, 50.0], width=400, height=300)
        chart._compute_points()
        assert abs(chart._points[0].y() - chart._points[1].y()) < 0.01

    def test_first_point_at_left(self):
        chart = _make_chart_with_size(LineChart, data=[10.0, 20.0], width=400, height=300)
        chart._compute_points()
        rect = chart._chart_rect()
        assert abs(chart._points[0].x() - rect.x()) < 0.01

    def test_last_point_at_right(self):
        chart = _make_chart_with_size(LineChart, data=[10.0, 20.0], width=400, height=300)
        chart._compute_points()
        rect = chart._chart_rect()
        assert abs(chart._points[-1].x() - (rect.x() + rect.width())) < 0.01

    def test_set_data_updates_points(self):
        chart = _make_chart_with_size(LineChart, width=400, height=300)
        chart.set_data([10.0, 20.0], labels=["A", "B"])
        assert len(chart._points) == 2
        chart.set_data([10.0, 20.0, 30.0], labels=["A", "B", "C"])
        assert len(chart._points) == 3


class TestLineChartChartRect:
    """Test LineChart._chart_rect() geometry."""

    def test_chart_rect_uses_margins(self):
        chart = _make_chart_with_size(LineChart, width=400, height=300)
        rect = chart._chart_rect()
        # _MARGIN_LEFT = 48, _MARGIN_TOP = 20
        assert rect.x() == 48
        assert rect.y() == 20

    def test_chart_rect_width(self):
        chart = _make_chart_with_size(LineChart, width=400, height=300)
        rect = chart._chart_rect()
        # width - MARGIN_LEFT(48) - MARGIN_RIGHT(20) = 332
        assert rect.width() == 400 - 48 - 20

    def test_chart_rect_height(self):
        chart = _make_chart_with_size(LineChart, width=400, height=300)
        rect = chart._chart_rect()
        # height - MARGIN_TOP(20) - MARGIN_BOTTOM(36) = 244
        assert rect.height() == 300 - 20 - 36


class TestLineChartHitTest:
    """Test LineChart._hit_test() for point detection."""

    def test_hit_test_returns_minus_one_when_empty(self):
        from PyQt5.QtCore import QPointF

        chart = _make_chart_with_size(LineChart, width=400, height=300)
        chart._compute_points()
        assert chart._hit_test(QPointF(200, 150)) == -1


# ===========================================================================
# BarChart tests
# ===========================================================================


class TestBarChartEmptyData:
    """BarChart behavior with no data."""

    def test_empty_data_bar_rects(self):
        chart = _make_chart_with_size(BarChart)
        chart._compute_bar_rects()
        assert chart._bar_rects == []

    def test_set_data_with_none(self):
        chart = _make_chart_with_size(BarChart)
        chart.set_data(None)
        assert chart._data == []


class TestBarChartSingleItem:
    """BarChart with a single bar."""

    def test_single_bar_rect_count(self):
        chart = _make_chart_with_size(BarChart, data=[50.0], labels=["A"], width=400, height=300)
        chart._compute_bar_rects()
        assert len(chart._bar_rects) == 1

    def test_single_bar_has_correct_index(self):
        chart = _make_chart_with_size(BarChart, data=[50.0], labels=["A"], width=400, height=300)
        chart._compute_bar_rects()
        idx, rect = chart._bar_rects[0]
        assert idx == 0

    def test_single_bar_has_positive_dimensions(self):
        chart = _make_chart_with_size(BarChart, data=[50.0], labels=["A"], width=400, height=300)
        chart._compute_bar_rects()
        _, rect = chart._bar_rects[0]
        assert rect.width() >= 8  # minimum bar width
        assert rect.height() > 0

    def test_single_bar_x_within_chart(self):
        chart = _make_chart_with_size(BarChart, data=[50.0], labels=["A"], width=400, height=300)
        chart._compute_bar_rects()
        _, rect = chart._bar_rects[0]
        chart_rect = chart._chart_rect()
        assert rect.x() >= chart_rect.x()


class TestBarChartMultipleItems:
    """BarChart with multiple bars."""

    def test_bar_count_matches_data(self):
        chart = _make_chart_with_size(BarChart, data=[10, 20, 30], width=400, height=300)
        chart._compute_bar_rects()
        assert len(chart._bar_rects) == 3

    def test_bars_are_left_to_right(self):
        chart = _make_chart_with_size(BarChart, data=[10, 20, 30], width=400, height=300)
        chart._compute_bar_rects()
        x_positions = [r.x() for _, r in chart._bar_rects]
        assert x_positions == sorted(x_positions)

    def test_bars_have_indices_0_to_n(self):
        chart = _make_chart_with_size(BarChart, data=[10, 20, 30, 40], width=400, height=300)
        chart._compute_bar_rects()
        indices = [i for i, _ in chart._bar_rects]
        assert indices == [0, 1, 2, 3]

    def test_higher_value_means_taller_bar(self):
        chart = _make_chart_with_size(BarChart, data=[10, 100], width=400, height=300)
        chart._compute_bar_rects()
        _, rect_small = chart._bar_rects[0]
        _, rect_large = chart._bar_rects[1]
        assert rect_large.height() > rect_small.height()

    def test_equal_values_same_height(self):
        chart = _make_chart_with_size(BarChart, data=[50, 50], width=400, height=300)
        chart._compute_bar_rects()
        _, r1 = chart._bar_rects[0]
        _, r2 = chart._bar_rects[1]
        assert abs(r1.height() - r2.height()) < 0.01

    def test_set_data_updates_bars(self):
        chart = _make_chart_with_size(BarChart, width=400, height=300)
        chart.set_data([10, 20], ["A", "B"])
        assert len(chart._bar_rects) == 2
        chart.set_data([10, 20, 30], ["A", "B", "C"])
        assert len(chart._bar_rects) == 3


class TestBarChartMaxVal:
    """Test BarChart max_val computation (uses max(data) * 1.1 or 1)."""

    def test_max_val_with_positive_data(self):
        chart = _make_chart_with_size(BarChart, data=[100], width=400, height=300)
        # max_val = max(max([100]), 1) * 1.1 = 110
        chart._compute_bar_rects()
        # Bar height should be (100/110) * chart_height
        _, rect = chart._bar_rects[0]
        chart_rect = chart._chart_rect()
        expected_h = (100 / 110) * chart_rect.height()
        assert abs(rect.height() - expected_h) < 0.01

    def test_max_val_with_zero_data(self):
        chart = _make_chart_with_size(BarChart, data=[0], width=400, height=300)
        chart._compute_bar_rects()
        # max_val = max(max([0]), 1) * 1.1 = 1.1, bar_h = 0
        _, rect = chart._bar_rects[0]
        assert rect.height() == 0


# ===========================================================================
# RadarChart tests
# ===========================================================================


class TestRadarChartEmptyData:
    """RadarChart behavior with no data."""

    def test_empty_vertices(self):
        chart = _make_chart_with_size(RadarChart)
        chart._compute_vertices()
        assert chart._vertex_points == []


class TestRadarChartAngleComputation:
    """Test _angle_for() angle computation for each axis."""

    def test_angle_for_first_axis_is_top(self):
        chart = _make_chart_with_size(RadarChart, data=[50, 50, 50])
        # i=0: angle = -pi/2 + (2*pi*0/3) = -pi/2 (pointing up)
        angle = chart._angle_for(0)
        assert abs(angle - (-math.pi / 2)) < 0.001

    def test_angle_for_three_axes_evenly_spaced(self):
        chart = _make_chart_with_size(RadarChart, data=[50, 50, 50])
        a0 = chart._angle_for(0)
        a1 = chart._angle_for(1)
        a2 = chart._angle_for(2)
        # Each should be 120 degrees apart (2*pi/3)
        assert abs((a1 - a0) - (2 * math.pi / 3)) < 0.001
        assert abs((a2 - a1) - (2 * math.pi / 3)) < 0.001

    def test_angle_for_five_axes(self):
        chart = _make_chart_with_size(RadarChart, data=[50] * 5)
        angles = [chart._angle_for(i) for i in range(5)]
        # Should be evenly spaced by 2*pi/5
        for i in range(4):
            diff = angles[i + 1] - angles[i]
            assert abs(diff - (2 * math.pi / 5)) < 0.001

    def test_angle_uses_max_len_3(self):
        """When data has fewer than 3 items, _angle_for uses n=3."""
        chart = _make_chart_with_size(RadarChart, data=[50])
        # _angle_for uses max(len(self._data), 3) = 3
        angle = chart._angle_for(0)
        assert abs(angle - (-math.pi / 2)) < 0.001


class TestRadarChartPointOnAxis:
    """Test _point_on_axis() computation."""

    def test_point_at_center_for_zero_value(self):
        chart = _make_chart_with_size(RadarChart, data=[0, 0, 0], width=400, height=400)
        center = chart._center()
        pt = chart._point_on_axis(0, 0)
        # value=0 means r=0, so point is at center
        assert abs(pt.x() - center.x()) < 0.01
        assert abs(pt.y() - center.y()) < 0.01

    def test_point_at_full_radius_for_max_value(self):
        chart = _make_chart_with_size(RadarChart, data=[50, 50, 50], width=400, height=400)
        center = chart._center()
        radius = chart._radius()
        pt = chart._point_on_axis(0, _MAX_VALUE)
        # At axis 0 (angle = -pi/2): cos(-pi/2)=0, sin(-pi/2)=-1
        # pt.x = center.x + 0 = center.x
        # pt.y = center.y - radius
        assert abs(pt.x() - center.x()) < 0.01
        assert abs(pt.y() - (center.y() - radius)) < 0.01

    def test_point_clamped_above_max(self):
        """Values above _MAX_VALUE should be clamped to _MAX_VALUE."""
        chart = _make_chart_with_size(RadarChart, data=[50, 50, 50], width=400, height=400)
        pt1 = chart._point_on_axis(0, 200)  # way above max
        pt2 = chart._point_on_axis(0, _MAX_VALUE)
        assert abs(pt1.x() - pt2.x()) < 0.01
        assert abs(pt1.y() - pt2.y()) < 0.01

    def test_point_proportional_to_value(self):
        chart = _make_chart_with_size(RadarChart, data=[50, 50, 50], width=400, height=400)
        center = chart._center()
        pt_half = chart._point_on_axis(0, 50)
        pt_full = chart._point_on_axis(0, 100)
        # Distance from center for half should be half of full
        dist_half = math.hypot(pt_half.x() - center.x(), pt_half.y() - center.y())
        dist_full = math.hypot(pt_full.x() - center.x(), pt_full.y() - center.y())
        assert abs(dist_half - dist_full / 2) < 0.01


class TestRadarChartVertices:
    """Test _compute_vertices() with actual data."""

    def test_vertex_count_matches_data(self):
        chart = _make_chart_with_size(RadarChart, data=[30, 60, 90], width=400, height=400)
        chart._compute_vertices()
        assert len(chart._vertex_points) == 3

    def test_five_vertices_for_five_axes(self):
        chart = _make_chart_with_size(RadarChart, data=[10, 20, 30, 40, 50], width=400, height=400)
        chart._compute_vertices()
        assert len(chart._vertex_points) == 5

    def test_vertex_positions_change_with_data(self):
        chart1 = _make_chart_with_size(RadarChart, data=[10, 10, 10], width=400, height=400)
        chart2 = _make_chart_with_size(RadarChart, data=[90, 90, 90], width=400, height=400)
        chart1._compute_vertices()
        chart2._compute_vertices()
        # Higher values should produce vertices farther from center
        center = chart1._center()
        dist1 = math.hypot(chart1._vertex_points[0].x() - center.x(), chart1._vertex_points[0].y() - center.y())
        dist2 = math.hypot(chart2._vertex_points[0].x() - center.x(), chart2._vertex_points[0].y() - center.y())
        assert dist2 > dist1


class TestRadarChartCenterAndRadius:
    """Test _center() and _radius() geometry helpers."""

    def test_center_is_midpoint(self):
        chart = _make_chart_with_size(RadarChart, width=400, height=300)
        center = chart._center()
        assert center.x() == 200.0
        assert center.y() == 150.0

    def test_radius_uses_smaller_dimension(self):
        chart = _make_chart_with_size(RadarChart, width=400, height=300)
        r = chart._radius()
        # min(400, 300) / 2 - 36 = 150 - 36 = 114
        assert r == 114.0

    def test_radius_with_square_widget(self):
        chart = _make_chart_with_size(RadarChart, width=500, height=500)
        r = chart._radius()
        # min(500, 500) / 2 - 36 = 250 - 36 = 214
        assert r == 214.0
