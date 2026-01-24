from unittest.mock import Mock

from textual.widgets import TabbedContent

from agentop.ui.app import AgentopApp


def test_opencode_view_switching_only_when_active():
    app = AgentopApp()
    tabs = Mock()
    panel = Mock()

    def query_one(selector, *_args, **_kwargs):
        if selector == TabbedContent:
            return tabs
        if selector == "#opencode-panel":
            return panel
        raise AssertionError("unexpected selector")

    app.query_one = query_one

    tabs.active = "opencode"
    app.action_next_opencode_view()
    panel.next_view.assert_called_once()

    panel.next_view.reset_mock()
    tabs.active = "claude"
    app.action_next_opencode_view()
    panel.next_view.assert_not_called()

    tabs.active = "opencode"
    app.action_prev_opencode_view()
    panel.prev_view.assert_called_once()
