"""Antigravity monitoring panel."""

from textual.widgets import Static
from rich.panel import Panel
from datetime import datetime
import math

from ...monitors.antigravity import AntigravityMonitor


class AntigravityPanel(Static):
    """Panel for displaying Antigravity/Gemini quota metrics."""

    def __init__(self, **kwargs):
        """Initialize panel."""
        super().__init__(**kwargs)
        self.monitor = AntigravityMonitor()
        self.page_index = 0
        self.page_size = 6
        self._effective_page_size = self.page_size

    def on_mount(self) -> None:
        """Set up periodic refresh."""
        self.set_interval(5.0, self.refresh_data)  # 5 second refresh
        self._update_page_size()
        self.refresh_data()

    def refresh_data(self) -> None:
        """Refresh the display with current metrics."""
        self._update_page_size()
        metrics = self.monitor.get_metrics()
        self.update(self._render_metrics(metrics))

    def next_page(self) -> None:
        """Move to the next model page."""
        self.page_index += 1
        self.refresh_data()

    def prev_page(self) -> None:
        """Move to the previous model page."""
        self.page_index = max(0, self.page_index - 1)
        self.refresh_data()

    def _render_metrics(self, metrics) -> Panel:
        """
        Render metrics as a Rich Panel.
        
        Args:
            metrics: AntigravityMetrics object
            
        Returns:
            Rich Panel with formatted metrics
        """
        # Check authentication
        if not metrics.is_authenticated:
            title = "🚀 ANTIGRAVITY ❌ Not Authenticated"
            content_lines = [
                "[yellow]⚠️  Google auth token not found[/yellow]",
                "",
                "To enable Antigravity monitoring:",
                "1. Login to Antigravity",
                "2. Keep Antigravity running once to save tokens",
                "3. The monitor will auto-detect the token",
                "",
                f"[dim]Error: {metrics.auth_error}[/dim]" if metrics.auth_error else "",
            ]
            return Panel("\n".join(content_lines), title=title, border_style="yellow")
        
        # Check forbidden status
        if metrics.is_forbidden:
            title = "🚀 ANTIGRAVITY ⚠️  Forbidden"
            content_lines = [
                "[yellow]Account does not have access to Gemini API[/yellow]",
                "",
                "Your Google account may not be enrolled in",
                "the Gemini/Antigravity program.",
                "",
                f"[dim]Subscription: {metrics.subscription_tier or 'Unknown'}[/dim]",
            ]
            return Panel("\n".join(content_lines), title=title, border_style="yellow")
        
        # Check for API error
        if metrics.auth_error and not metrics.models:
            title = "🚀 ANTIGRAVITY ⚠️  API Error"
            content_lines = [
                "[yellow]Failed to fetch quota data[/yellow]",
                "",
                f"[dim]Error: {metrics.auth_error}[/dim]",
            ]
            return Panel("\n".join(content_lines), title=title, border_style="yellow")
        
        # Success - show quota data
        title = "🚀 ANTIGRAVITY 🟢 Active"
        
        content_parts = []
        
        # Subscription tier
        if metrics.subscription_tier:
            content_parts.append(f"[b]Subscription:[/b]  {metrics.subscription_tier}")
            content_parts.append("")
        
        # Models quota
        if metrics.models:
            content_parts.append("[b]Model Quotas:[/b]")
            content_parts.append("")

            models = sorted(
                metrics.models,
                key=lambda model: (model.percentage, model.name.lower()),
            )

            page_size = max(1, self._effective_page_size)
            total_pages = max(1, math.ceil(len(models) / page_size))
            self.page_index = min(self.page_index, total_pages - 1)
            start = self.page_index * page_size
            page_models = models[start : start + page_size]

            for model in page_models:
                # Shorten model name for display
                display_name = model.name.split('/')[-1] if '/' in model.name else model.name
                
                # Color based on quota percentage
                if model.percentage >= 70:
                    color = "green"
                elif model.percentage >= 30:
                    color = "yellow"
                else:
                    color = "red"
                
                # Create progress bar
                bar = self._create_bar(model.percentage, 100, 15)
                
                content_parts.append(f"  [bold]{display_name}[/bold]")
                content_parts.append(f"    {bar} [{color}]{model.percentage}%[/{color}] remaining")
                
                # Show reset time if available
                if model.reset_time:
                    reset_str = self._format_reset_time(model.reset_time)
                    if reset_str:
                        content_parts.append(f"    [dim]Resets at: {reset_str}[/dim]")
                    else:
                        content_parts.append(f"    [dim]Resets: {model.reset_time[:16]}[/dim]")
                
                content_parts.append("")

            if total_pages > 1:
                content_parts.append(
                    f"[dim]Page {self.page_index + 1}/{total_pages} • Use [ and ] to navigate[/dim]"
                )
        else:
            content_parts.append("[dim]No model quota data available[/dim]")
            content_parts.append("")
        
        # Last updated
        if metrics.last_updated:
            time_str = metrics.last_updated.strftime("%H:%M:%S")
            content_parts.append(f"[dim]Last updated: {time_str}[/dim]")
        
        content = "\n".join(content_parts)
        
        return Panel(content, title=title, border_style="green")

    def _create_bar(self, value: int, total: int, width: int = 15) -> str:
        """Create a simple progress bar."""
        if total == 0:
            return "░" * width
        
        filled = int((value / total) * width)
        filled = min(filled, width)
        empty = width - filled
        
        # Color based on percentage
        pct = value  # value is already a percentage (0-100)
        if pct >= 70:
            color = "green"
        elif pct >= 30:
            color = "yellow"
        else:
            color = "red"
        
        bar = f"[{color}]{'█' * filled}[/{color}]{'░' * empty}"
        return bar

    def _format_reset_time(self, reset_time: str) -> str:
        """Format ISO reset time string to HH:MM."""
        if not reset_time:
            return ""
        try:
            reset_dt = datetime.fromisoformat(reset_time.replace("Z", "+00:00"))
        except ValueError:
            return ""
        if reset_dt.tzinfo is not None:
            reset_dt = reset_dt.astimezone().replace(tzinfo=None)
        return reset_dt.strftime("%H:%M")

    def _update_page_size(self) -> None:
        """Compute a stable page size from screen height."""
        app = getattr(self, "app", None)
        height = getattr(getattr(app, "size", None), "height", 0) or 0
        if height <= 0:
            return

        overhead_lines = 12  # header/footer + panel padding + headings
        available = max(0, height - overhead_lines)
        per_model = 4
        max_models = max(3, available // per_model)
        self._effective_page_size = min(self.page_size, max_models)
