"""Main Textual application."""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, TabbedContent, TabPane
from textual import events
from .widgets.agent_panel import ClaudeCodePanel, CodexPanel, CursorPanel
from .widgets.antigravity_panel import AntigravityPanel


class AgentMonitorApp(App):
    """Agent Monitor TUI Application."""

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
                
            with TabPane("Cursor", id="cursor"):
                yield CursorPanel(id="cursor-panel")
                
            with TabPane("Antigravity", id="antigravity"):
                yield AntigravityPanel(id="antigravity-panel")
                
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
            cursor_panel = self.query_one("#cursor-panel", CursorPanel)
            cursor_panel.refresh_data()
        except Exception:
            pass

    def action_next_tab(self) -> None:
        """Switch to next tab."""
        tabs = self.query_one(TabbedContent)
        tab_ids = ["claude", "cursor", "antigravity", "codex"]
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
        tab_ids = ["claude", "cursor", "antigravity", "codex"]
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


def main():
    """Main entry point."""
    app = AgentMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
