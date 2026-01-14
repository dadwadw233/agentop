#!/usr/bin/env python3
"""Test script for Agent Monitor MVP."""

import sys
from agent_monitor.monitors.process import ProcessMonitor
from agent_monitor.monitors.claude_code import ClaudeCodeMonitor
from agent_monitor.monitors.codex import CodexMonitor
from agent_monitor.core.constants import AgentType


def test_process_monitor():
    """Test process monitoring."""
    print("=" * 60)
    print("Testing Process Monitor")
    print("=" * 60)

    monitor = ProcessMonitor()

    # Test Claude Code detection
    print("\n[Claude Code Processes]")
    claude_processes = monitor.find_agent_processes(AgentType.CLAUDE_CODE)
    if claude_processes:
        for proc in claude_processes:
            print(f"  ✓ PID {proc.pid}: {proc.name}")
            print(f"    CPU: {proc.cpu_percent:.1f}%  Memory: {proc.memory_mb:.0f} MB")
            print(f"    Status: {proc.status}  Uptime: {proc.uptime:.0f}s")
    else:
        print("  No Claude Code processes found")

    # Test Cursor detection
    print("\n[Cursor Processes]")
    cursor_processes = monitor.find_agent_processes(AgentType.CURSOR)
    if cursor_processes:
        print(f"  ✓ Found {len(cursor_processes)} Cursor processes")
        total_cpu = sum(p.cpu_percent for p in cursor_processes)
        total_mem = sum(p.memory_mb for p in cursor_processes)
        print(f"  Total CPU: {total_cpu:.1f}%  Total Memory: {total_mem:.0f} MB")
    else:
        print("  No Cursor processes found")

    # Test Codex detection
    print("\n[Codex Processes]")
    codex_processes = monitor.find_agent_processes(AgentType.CODEX)
    if codex_processes:
        for proc in codex_processes:
            print(f"  ✓ PID {proc.pid}: {proc.name}")
            print(f"    CPU: {proc.cpu_percent:.1f}%  Memory: {proc.memory_mb:.0f} MB")
            print(f"    Status: {proc.status}  Uptime: {proc.uptime:.0f}s")
    else:
        print("  No Codex processes found")

    return (
        len(claude_processes) > 0
        or len(cursor_processes) > 0
        or len(codex_processes) > 0
    )


def test_claude_code_monitor():
    """Test Claude Code monitoring."""
    print("\n" + "=" * 60)
    print("Testing Claude Code Monitor")
    print("=" * 60)

    monitor = ClaudeCodeMonitor()

    try:
        metrics = monitor.get_metrics()

        print(f"\n[Process Info]")
        print(f"  Active: {metrics.is_active}")
        print(f"  Processes: {metrics.process_count}")
        if metrics.process_count > 0:
            print(f"  Total CPU: {metrics.total_cpu:.1f}%")
            print(f"  Total Memory: {metrics.total_memory_mb:.0f} MB")

        print(f"\n[Session Info]")
        print(f"  Active sessions: {metrics.active_sessions}")
        print(f"  Total today: {metrics.total_sessions_today}")

        print(f"\n[Token Usage - Today]")
        print(f"  Input: {metrics.tokens_today.input_tokens:,} tokens")
        print(f"  Output: {metrics.tokens_today.output_tokens:,} tokens")
        print(f"  Total: {metrics.tokens_today.total_tokens:,} tokens")

        print(f"\n[Token Usage - This Month]")
        print(f"  Input: {metrics.tokens_this_month.input_tokens:,} tokens")
        print(f"  Output: {metrics.tokens_this_month.output_tokens:,} tokens")
        print(f"  Total: {metrics.tokens_this_month.total_tokens:,} tokens")

        print(f"\n[Cost Estimates]")
        print(f"  Today: ${metrics.cost_today.amount:.2f}")
        print(f"  This Month: ${metrics.cost_this_month.amount:.2f}")

        if metrics.is_near_quota_limit:
            print(f"\n  ⚠️  WARNING: Near quota limit!")

        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_codex_monitor():
    """Test Codex monitoring."""
    print("\n" + "=" * 60)
    print("Testing Codex Monitor")
    print("=" * 60)

    monitor = CodexMonitor()

    try:
        metrics = monitor.get_metrics()

        print(f"\n[Process Info]")
        print(f"  Active: {metrics.is_active}")
        print(f"  Processes: {metrics.process_count}")
        if metrics.process_count > 0:
            print(f"  Total CPU: {metrics.total_cpu:.1f}%")
            print(f"  Total Memory: {metrics.total_memory_mb:.0f} MB")

        print(f"\n[Session Info]")
        print(f"  Active sessions: {metrics.active_sessions}")
        print(f"  Total today: {metrics.total_sessions_today}")

        print("\n[Usage]")
        print("  Codex CLI does not store local token usage")

        if metrics.rate_limits and (metrics.rate_limits.primary or metrics.rate_limits.secondary):
            print("\n[Rate Limits]")
            for window in [metrics.rate_limits.primary, metrics.rate_limits.secondary]:
                if not window:
                    continue
                label = "5h" if window.window_minutes is None else f"{window.window_minutes}m"
                remaining = window.remaining_percent
                print(f"  {label}: {remaining:.0f}% left")
        else:
            print("\n[Rate Limits]")
            print("  Not available")

        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n🤖 Agent Monitor - MVP Test\n")

    success = True

    # Test 1: Process Monitor
    success &= test_process_monitor()

    # Test 2: Claude Code Monitor
    success &= test_claude_code_monitor()

    # Test 3: Codex Monitor
    success &= test_codex_monitor()

    # Summary
    print("\n" + "=" * 60)
    if success:
        print("✓ All tests passed!")
        print("\nTo run the TUI application:")
        print("  python3 -m agent_monitor")
        print("  # or")
        print("  agent-monitor")
    else:
        print("✗ Some tests failed")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
