"""Test time range switching in OpenCode panel."""

import pytest
from agentop.ui.widgets.opencode_panel import OpenCodePanel


def test_panel_initializes_with_all_time_range():
    """Panel initializes with 'all' as default time range."""
    panel = OpenCodePanel()
    assert panel.current_time_range == "all"


def test_panel_set_time_range():
    """Panel can set different time ranges."""
    panel = OpenCodePanel()

    panel.set_time_range("today")
    assert panel.current_time_range == "today"

    panel.set_time_range("week")
    assert panel.current_time_range == "week"

    panel.set_time_range("month")
    assert panel.current_time_range == "month"

    panel.set_time_range("all")
    assert panel.current_time_range == "all"


def test_panel_set_invalid_time_range_ignored():
    """Panel ignores invalid time ranges."""
    panel = OpenCodePanel()
    original_range = panel.current_time_range

    panel.set_time_range("invalid")
    assert panel.current_time_range == original_range
