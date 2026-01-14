"""Main entry point for Agent Monitor."""

import sys
from .ui.app import AgentMonitorApp


def main():
    """Main entry point."""
    app = AgentMonitorApp()
    app.run()


if __name__ == "__main__":
    main()
