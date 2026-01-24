"""Main Textual application."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane
from textual import events
from .widgets.agent_panel import ClaudeCodePanel, CodexPanel
from .widgets.antigravity_panel import AntigravityPanel
from .widgets.opencode_panel import OpenCodePanel


class AgentopApp(App):
    """Agentop TUI Application."""

    TITLE = "Agentop"

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary;
    }

    ClaudeCodePanel {
        margin-bottom: 1;
    }

    CodexPanel {
        margin-bottom: 1;
    }

    OpenCodePanel {
        margin-bottom: 1;
    }

    #antigravity, #antigravity-panel {
        overflow: hidden;
        scrollbar-size: 0 0;
    }

    .info-text {
        margin-top: 1;
        color: $text-muted;
        text-align: center;
    }

    Footer {
        background: $panel;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with TabbedContent(initial="claude"):
            with TabPane("Claude Code", id="claude"):
                yield ClaudeCodePanel(id="claude-panel")

            with TabPane("Antigravity", id="antigravity"):
                yield AntigravityPanel(id="antigravity-panel")

            with TabPane("OpenCode", id="opencode"):
                yield OpenCodePanel(id="opencode-panel")

            with TabPane("Codex", id="codex"):
                yield CodexPanel(id="codex-panel")

        yield Footer()

    def on_key(self, event: events.Key) -> None:
        """Handle key events to enable Tab navigation."""
        if event.key == "tab":
            event.prevent_default()
            self.action_next_tab()
        elif event.key == "shift+tab":
            event.prevent_default()
            self.action_prev_tab()
        elif event.character == "[" or event.key in ("left_bracket", "left_square_bracket"):
            event.prevent_default()
            self.action_prev_antigravity_page()
        elif event.character == "]" or event.key in ("right_bracket", "right_square_bracket"):
            event.prevent_default()
            self.action_next_antigravity_page()
        elif event.character == "l":
            event.prevent_default()
            self.action_next_opencode_view()
        elif event.character == "k":
            event.prevent_default()
            self.action_prev_opencode_view()
        elif event.character == "t":
            event.prevent_default()
            self.action_opencode_time_range("today")
        elif event.character == "w":
            event.prevent_default()
            self.action_opencode_time_range("week")
        elif event.character == "m":
            event.prevent_default()
            self.action_opencode_time_range("month")
        elif event.character == "a":
            event.prevent_default()
            self.action_opencode_time_range("all")

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_refresh(self) -> None:
        """Manually refresh data."""
        try:
            panel = self.query_one("#claude-panel", ClaudeCodePanel)
            panel.refresh_data()
        except Exception:
            pass

        try:
            codex_panel = self.query_one("#codex-panel", CodexPanel)
            codex_panel.refresh_data()
        except Exception:
            pass

        try:
            antigravity_panel = self.query_one("#antigravity-panel", AntigravityPanel)
            antigravity_panel.refresh_data()
        except Exception:
            pass

        try:
            opencode_panel = self.query_one("#opencode-panel", OpenCodePanel)
            opencode_panel.refresh_data()
        except Exception:
            pass

    def action_next_tab(self) -> None:
        """Switch to next tab."""
        tabs = self.query_one(TabbedContent)
        tab_ids = ["claude", "antigravity", "opencode", "codex"]
        current = tabs.active
        try:
            current_idx = tab_ids.index(current)
            next_idx = (current_idx + 1) % len(tab_ids)
            tabs.active = tab_ids[next_idx]
        except Exception:
            tabs.active = "claude"

    def action_prev_tab(self) -> None:
        """Switch to previous tab."""
        tabs = self.query_one(TabbedContent)
        tab_ids = ["claude", "antigravity", "opencode", "codex"]
        current = tabs.active
        try:
            current_idx = tab_ids.index(current)
            prev_idx = (current_idx - 1) % len(tab_ids)
            tabs.active = tab_ids[prev_idx]
        except Exception:
            tabs.active = "claude"

    def action_next_antigravity_page(self) -> None:
        """Advance Antigravity model page when that tab is active."""
        tabs = self.query_one(TabbedContent)
        if tabs.active != "antigravity":
            return
        try:
            panel = self.query_one("#antigravity-panel", AntigravityPanel)
            panel.next_page()
        except Exception:
            pass

    def action_prev_antigravity_page(self) -> None:
        """Go to previous Antigravity model page when that tab is active."""
        tabs = self.query_one(TabbedContent)
        if tabs.active != "antigravity":
            return
        try:
            panel = self.query_one("#antigravity-panel", AntigravityPanel)
            panel.prev_page()
        except Exception:
            pass

    def action_next_opencode_view(self) -> None:
        tabs = self.query_one(TabbedContent)
        if tabs.active != "opencode":
            return
        try:
            panel = self.query_one("#opencode-panel", OpenCodePanel)
            panel.next_view()
        except Exception:
            pass

    def action_prev_opencode_view(self) -> None:
        tabs = self.query_one(TabbedContent)
        if tabs.active != "opencode":
            return
        try:
            panel = self.query_one("#opencode-panel", OpenCodePanel)
            panel.prev_view()
        except Exception:
            pass

    def action_opencode_time_range(self, time_range: str) -> None:
        """Set OpenCode time range."""
        tabs = self.query_one(TabbedContent)
        if tabs.active != "opencode":
            return
        try:
            panel = self.query_one("#opencode-panel", OpenCodePanel)
            panel.set_time_range(time_range)
        except Exception:
            pass


def main():
    """Main entry point."""
    app = AgentopApp()
    app.run()


if __name__ == "__main__":
    main()
