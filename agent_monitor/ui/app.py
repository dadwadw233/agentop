"""Main Textual application."""

from textual.app import App, ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import Header, Footer, Static
from .widgets.agent_panel import ClaudeCodePanel, CodexPanel


class AgentMonitorApp(App):
    """Agent Monitor TUI Application."""

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $primary;
    }

    #main-container {
        height: 100%;
        overflow-y: auto;
        padding: 1 2;
    }

    ClaudeCodePanel {
        margin-bottom: 1;
    }

    CodexPanel {
        margin-bottom: 1;
    }

    #info-text {
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
        ("r", "refresh", "Refresh Now"),
        ("d", "toggle_details", "Details"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield ScrollableContainer(
            ClaudeCodePanel(id="claude-panel"),
            CodexPanel(id="codex-panel"),
            Static(
                "💡 [dim]Auto-refreshing every second. Press Q to quit, R to refresh now[/dim]",
                id="info-text",
            ),
            id="main-container",
        )
        yield Footer()

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()

    def action_refresh(self) -> None:
        """Manually refresh data."""
        panel = self.query_one("#claude-panel", ClaudeCodePanel)
        panel.refresh_data()
        codex_panel = self.query_one("#codex-panel", CodexPanel)
        codex_panel.refresh_data()

    def action_toggle_details(self) -> None:
        """Toggle detailed view."""
        self.notify("Details view coming in Phase 2!")


def main():
    """Main entry point."""
    app = AgentMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
