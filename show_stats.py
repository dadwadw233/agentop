#!/usr/bin/env python3
"""Display detailed Claude Code statistics."""

from agentop.parsers.stats_parser import ClaudeStatsParser
from agentop.monitors.claude_code import ClaudeCodeMonitor


def main():
    """Display detailed statistics."""
    print("\n" + "=" * 70)
    print("📊 Claude Code - Detailed Statistics")
    print("=" * 70)

    parser = ClaudeStatsParser()
    monitor = ClaudeCodeMonitor()

    # Get metrics
    metrics = monitor.get_metrics()

    # Display current status
    print("\n🔧 CURRENT STATUS")
    print("-" * 70)
    status = "🟢 Active" if metrics.is_active else "⚪ Idle"
    print(f"  Status: {status}")
    print(f"  Active sessions: {metrics.active_sessions}")
    print(f"  Running processes: {metrics.process_count}")
    if metrics.processes:
        for proc in metrics.processes:
            print(f"    • PID {proc.pid}: {proc.name}")
            print(f"      CPU: {proc.cpu_percent:.1f}%  Memory: {proc.memory_mb:.0f} MB")
            print(f"      Uptime: {proc.uptime / 3600:.1f} hours")

    # Get total usage
    total_usage = parser.get_total_usage()

    print("\n📈 USAGE STATISTICS")
    print("-" * 70)

    print(f"\n  📅 Today ({parser.stats_file.name} last updated: see below)")
    print(f"    Sessions: {metrics.total_sessions_today}")
    if metrics.tokens_today.total_tokens > 0:
        print(f"    Tokens: {metrics.tokens_today.total_tokens:,}")
        print(f"      • Input:  {metrics.tokens_today.input_tokens:,}")
        print(f"      • Output: {metrics.tokens_today.output_tokens:,}")
        print(f"    Cost: ${metrics.cost_today.amount:.2f}")
    else:
        print(f"    No data for today yet (stats file may not be updated)")

    print(f"\n  📆 This Month")
    print(f"    Tokens: {metrics.tokens_this_month.total_tokens:,}")
    print(f"      • Input:  {metrics.tokens_this_month.input_tokens:,}")
    print(f"      • Output: {metrics.tokens_this_month.output_tokens:,}")
    print(f"    Cost: ${metrics.cost_this_month.amount:.2f}")

    print(f"\n  📊 All Time")
    print(f"    Total sessions: {total_usage['total_sessions']}")
    print(f"    Total messages: {total_usage['total_messages']}")
    print(f"    Total tokens: {total_usage['tokens'].total_tokens:,}")
    print(f"      • Input:  {total_usage['tokens'].input_tokens:,}")
    print(f"      • Output: {total_usage['tokens'].output_tokens:,}")
    print(f"    Estimated cost: ${total_usage['cost']:.2f}")

    # Model breakdown
    stats = parser.parse_stats()
    model_usage = stats.get("modelUsage", {})

    if model_usage:
        print("\n  🤖 By Model (All Time)")
        for model, usage in model_usage.items():
            # Shorten model name
            short_name = model.replace("claude-", "").replace("-20250929", "").replace(
                "-20251001", ""
            )
            input_tokens = usage.get("inputTokens", 0)
            output_tokens = usage.get("outputTokens", 0)
            total = input_tokens + output_tokens
            print(f"    • {short_name}")
            print(f"      Tokens: {total:,} (↓{input_tokens:,} ↑{output_tokens:,})")

    # Last update info
    last_computed = stats.get("lastComputedDate", "Unknown")
    print(f"\n  ℹ️  Stats file last updated: {last_computed}")
    print(f"     File location: {parser.stats_file}")

    print("\n" + "=" * 70)
    print("💡 Tip: Run 'agentop' for real-time TUI monitoring")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
