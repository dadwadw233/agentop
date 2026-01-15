"""Debug tool for Cursor dashboard usage API."""

from __future__ import annotations

import json
import os

from .parsers.cursor_dashboard_api import CursorDashboardClient


def main() -> None:
    cookie = os.getenv("CURSOR_DASHBOARD_COOKIE")
    if not cookie:
        print("CURSOR_DASHBOARD_COOKIE is not set.")
        print("Export it from browser DevTools: WorkosCursorSessionToken=...")
        return

    client = CursorDashboardClient(cache_ttl_seconds=0)
    snapshot = client.get_usage_snapshot()
    if not snapshot:
        print("No usage snapshot returned.")
        if client.last_error:
            print(f"Error: {client.last_error}")
        return

    output = {
        "billing_period": {
            "start_ms": snapshot.period_start_ms,
            "end_ms": snapshot.period_end_ms,
        },
        "totals": {
            "input_tokens": snapshot.total_input_tokens,
            "output_tokens": snapshot.total_output_tokens,
            "cache_write_tokens": snapshot.total_cache_write_tokens,
            "cache_read_tokens": snapshot.total_cache_read_tokens,
            "total_tokens": snapshot.total_tokens,
            "total_cost_cents": snapshot.total_cost_cents,
        },
        "aggregations": [
            {
                "model_intent": agg.model_intent,
                "total_tokens": agg.total_tokens,
                "total_cents": agg.total_cents,
                "input_tokens": agg.input_tokens,
                "output_tokens": agg.output_tokens,
                "cache_write_tokens": agg.cache_write_tokens,
                "cache_read_tokens": agg.cache_read_tokens,
                "tier": agg.tier,
            }
            for agg in snapshot.aggregations
        ],
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
