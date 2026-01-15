"""Debug tool for Cursor dashboard usage API."""

from __future__ import annotations

import json
import os
import time

import httpx

from .parsers.cursor_dashboard_api import CursorDashboardClient


def main() -> None:
    cookie = os.getenv("CURSOR_DASHBOARD_COOKIE")
    if not cookie:
        print("CURSOR_DASHBOARD_COOKIE is not set.")
        print("Export it from browser DevTools: WorkosCursorSessionToken=...")
        return

    if os.getenv("CURSOR_DEBUG_RAW") == "1":
        _debug_raw_requests(cookie)
        return

    client = CursorDashboardClient(cache_ttl_seconds=0)
    snapshot = client.get_usage_snapshot()
    if not snapshot:
        print("No usage snapshot returned.")
        if client.last_error:
            print(f"Error: {client.last_error}")
        print("Tip: set CURSOR_DEBUG_RAW=1 to inspect raw responses.")
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


def _debug_raw_requests(cookie: str) -> None:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://cursor.com",
        "Referer": "https://cursor.com/cn/dashboard?tab=billing",
        "Cookie": cookie,
        "User-Agent": "Mozilla/5.0",
    }

    now_ms = int(time.time() * 1000)
    invoice_payload = {
        "year": time.localtime().tm_year,
        "cycleFilterType": "CYCLE_TYPE_START_TIME",
        "startTimeMs": str(now_ms),
    }

    with httpx.Client(timeout=15.0) as client:
        invoice = client.post(
            "https://cursor.com/api/dashboard/get-monthly-invoice",
            headers=headers,
            json=invoice_payload,
        )
        print(f"get-monthly-invoice: {invoice.status_code}")
        print(invoice.text[:1000])

        if invoice.status_code != 200:
            return

        try:
            invoice_json = invoice.json()
        except Exception:
            return

        start_ms = invoice_json.get("periodStartMs")
        if not start_ms:
            print("No periodStartMs in invoice response.")
            return

        team_id = os.getenv("CURSOR_TEAM_ID", "-1")
        try:
            team_id_value = int(team_id)
        except ValueError:
            team_id_value = -1

        usage_payload = {"teamId": team_id_value, "startDate": int(start_ms)}
        usage = client.post(
            "https://cursor.com/api/dashboard/get-aggregated-usage-events",
            headers=headers,
            json=usage_payload,
        )
        print(f"get-aggregated-usage-events: {usage.status_code}")
        print(usage.text[:2000])


if __name__ == "__main__":
    main()
