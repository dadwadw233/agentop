"""Main entry point for Agentop."""

from .ui.app import AgentopApp


def main():
    """Main entry point."""
    app = AgentopApp()
    app.run()


if __name__ == "__main__":
    main()
