"""Tests for OpenCode panel."""

from unittest.mock import Mock


def test_panel_initializes():
    """Test that OpenCodePanel can be instantiated."""
    from agentop.ui.widgets.opencode_panel import OpenCodePanel

    panel = OpenCodePanel()
    assert panel is not None
    assert panel.monitor is not None
    assert panel.current_time_range == "all"


def test_panel_refresh_data_calls_monitor():
    """Test that refresh_data calls monitor and updates panel."""
    from agentop.ui.widgets.opencode_panel import OpenCodePanel
    from agentop.core.models import OpenCodeMetrics, OpenCodeTokenUsage

    panel = OpenCodePanel()

    # Mock the monitor's get_metrics method
    panel.monitor = Mock()
    mock_metrics = OpenCodeMetrics(
        agent_type="opencode",
        processes=[],
        is_active=False,
        total_tokens=OpenCodeTokenUsage(),
        tokens_today=OpenCodeTokenUsage(),
        active_sessions=0,
        total_sessions_today=0,
    )
    panel.monitor.get_metrics.return_value = mock_metrics

    # Mock the _render_metrics method to avoid Rich rendering in tests
    panel._render_metrics = Mock(return_value="Test Output")

    # Call refresh_data
    panel.refresh_data()

    # Verify monitor was called
    panel.monitor.get_metrics.assert_called_once()
    # Verify _render_metrics was called with metrics
    panel._render_metrics.assert_called_once_with(mock_metrics)


def test_panel_switches_subviews():
    """Test that panel can switch between subviews."""
    from agentop.ui.widgets.opencode_panel import OpenCodePanel

    panel = OpenCodePanel()

    # Check initial view
    assert panel.current_view == "overview"

    # Switch to next view
    panel.next_view()
    assert panel.current_view == "projects"

    # Switch to next view
    panel.next_view()
    assert panel.current_view == "models"

    # Switch to next view
    panel.next_view()
    assert panel.current_view == "agents"

    # Switch to next view
    panel.next_view()
    assert panel.current_view == "timeline"

    # Cycle back to first
    panel.next_view()
    assert panel.current_view == "overview"

    # Test previous view
    panel.prev_view()
    assert panel.current_view == "timeline"

    panel.prev_view()
    assert panel.current_view == "agents"


def test_panel_renders_view_title():
    from agentop.ui.widgets.opencode_panel import OpenCodePanel
    from agentop.core.models import OpenCodeMetrics, OpenCodeTokenUsage

    panel = OpenCodePanel()
    panel.current_view = "models"

    metrics = OpenCodeMetrics(
        agent_type="opencode",
        processes=[],
        is_active=False,
        total_tokens=OpenCodeTokenUsage(),
        tokens_today=OpenCodeTokenUsage(),
        active_sessions=0,
        total_sessions_today=0,
        by_model={"glm-4.7": OpenCodeTokenUsage(input_tokens=1)},
    )

    rendered = panel._render_metrics(metrics)
    assert "Models" in str(rendered.title)


def test_panel_renders_view_hint():
    from typing import cast
    from rich.console import Group
    from rich.text import Text
    from agentop.ui.widgets.opencode_panel import OpenCodePanel
    from agentop.core.models import OpenCodeMetrics, OpenCodeTokenUsage

    panel = OpenCodePanel()

    metrics = OpenCodeMetrics(
        agent_type="opencode",
        processes=[],
        is_active=False,
        total_tokens=OpenCodeTokenUsage(),
        tokens_today=OpenCodeTokenUsage(),
        active_sessions=0,
        total_sessions_today=0,
    )

    rendered = panel._render_metrics(metrics)
    render_group = cast(Group, rendered.renderable)
    renderables = render_group.renderables
    hint = cast(Text, renderables[-1])
    hint_text = str(hint)
    assert "k/l: switch views" in hint_text or "Time:" in hint_text or "Updated:" in hint_text


def test_panel_sets_time_range():
    """Test that time range can be changed."""
    from agentop.ui.widgets.opencode_panel import OpenCodePanel

    panel = OpenCodePanel()

    # Test setting different time ranges
    panel.set_time_range("today")
    assert panel.current_time_range == "today"

    panel.set_time_range("week")
    assert panel.current_time_range == "week"

    panel.set_time_range("month")
    assert panel.current_time_range == "month"

    panel.set_time_range("all")
    assert panel.current_time_range == "all"

    # Test invalid range is ignored
    panel.set_time_range("invalid")
    assert panel.current_time_range == "all"
