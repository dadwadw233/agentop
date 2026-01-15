"""Cursor dashboard API client.

Uses private Cursor dashboard endpoints to fetch billing usage.
Authentication is provided via CURSOR_DASHBOARD_COOKIE env var.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import os
import time
import logging

import httpx

from ..core.models import CursorUsageAggregate

logger = logging.getLogger(__name__)


@dataclass
class CursorUsageSnapshot:
    """Parsed usage snapshot for the current billing period."""

    period_start_ms: int
    period_end_ms: int
    total_input_tokens: int
    total_output_tokens: int
    total_cache_write_tokens: int
    total_cache_read_tokens: int
    total_cost_cents: float
    aggregations: List[CursorUsageAggregate] = field(default_factory=list)
    captured_at: Optional[datetime] = None

    @property
    def total_tokens(self) -> int:
        return (
            self.total_input_tokens
            + self.total_output_tokens
            + self.total_cache_write_tokens
            + self.total_cache_read_tokens
        )


class CursorDashboardClient:
    """Client for Cursor dashboard usage endpoints (private API)."""

    BASE_URL = "https://cursor.com/api/dashboard"
    TIMEOUT = 15.0

    def __init__(self, cache_ttl_seconds: int = 60):
        self.cache_ttl_seconds = max(30, cache_ttl_seconds)
        self._cached_snapshot: Optional[CursorUsageSnapshot] = None
        self._cached_at: Optional[float] = None
        self.last_error: Optional[str] = None

    def get_usage_snapshot(self) -> Optional[CursorUsageSnapshot]:
        """Fetch usage snapshot for current billing period."""
        if self._cached_snapshot and self._cached_at:
            age = time.time() - self._cached_at
            if age < self.cache_ttl_seconds:
                return self._cached_snapshot

        cookie = os.getenv("CURSOR_DASHBOARD_COOKIE")
        if not cookie:
            self.last_error = "CURSOR_DASHBOARD_COOKIE not set"
            return None

        now_ms = int(time.time() * 1000)
        period = self._fetch_monthly_invoice(cookie, now_ms)
        if not period:
            return None

        period_start_ms, period_end_ms = period
        snapshot = self._fetch_usage(cookie, period_start_ms, period_end_ms)
        if snapshot:
            self._cached_snapshot = snapshot
            self._cached_at = time.time()
        return snapshot

    def _fetch_monthly_invoice(self, cookie: str, now_ms: int) -> Optional[tuple[int, int]]:
        payload = {
            "year": datetime.now().year,
            "cycleFilterType": "CYCLE_TYPE_START_TIME",
            "startTimeMs": str(now_ms),
        }
        response = self._post(cookie, "get-monthly-invoice", payload)
        if not response:
            return None

        if response.status_code != 200:
            self.last_error = f"billing API returned {response.status_code}"
            return None

        try:
            data = response.json()
        except Exception:
            self.last_error = "billing API JSON parse failed"
            return None

        start_ms = data.get("periodStartMs")
        end_ms = data.get("periodEndMs")
        if not start_ms or not end_ms:
            self.last_error = "billing period not found"
            return None

        try:
            return int(start_ms), int(end_ms)
        except (TypeError, ValueError):
            self.last_error = "billing period parse failed"
            return None

    def _fetch_usage(
        self, cookie: str, period_start_ms: int, period_end_ms: int
    ) -> Optional[CursorUsageSnapshot]:
        team_id = os.getenv("CURSOR_TEAM_ID", "-1")
        try:
            team_id_value = int(team_id)
        except ValueError:
            team_id_value = -1

        payload = {"teamId": team_id_value, "startDate": period_start_ms}
        response = self._post(cookie, "get-aggregated-usage-events", payload)
        if not response:
            return None

        if response.status_code != 200:
            self.last_error = f"usage API returned {response.status_code}"
            return None

        try:
            data = response.json()
        except Exception:
            self.last_error = "usage API JSON parse failed"
            return None

        aggregations = []
        for item in data.get("aggregations", []) or []:
            aggregations.append(
                CursorUsageAggregate(
                    model_intent=str(item.get("modelIntent", "unknown")),
                    input_tokens=int(item.get("inputTokens", 0) or 0),
                    output_tokens=int(item.get("outputTokens", 0) or 0),
                    cache_write_tokens=int(item.get("cacheWriteTokens", 0) or 0),
                    cache_read_tokens=int(item.get("cacheReadTokens", 0) or 0),
                    total_cents=float(item.get("totalCents", 0.0) or 0.0),
                    tier=item.get("tier"),
                )
            )

        snapshot = CursorUsageSnapshot(
            period_start_ms=period_start_ms,
            period_end_ms=period_end_ms,
            total_input_tokens=int(data.get("totalInputTokens", 0) or 0),
            total_output_tokens=int(data.get("totalOutputTokens", 0) or 0),
            total_cache_write_tokens=int(data.get("totalCacheWriteTokens", 0) or 0),
            total_cache_read_tokens=int(data.get("totalCacheReadTokens", 0) or 0),
            total_cost_cents=float(data.get("totalCostCents", 0.0) or 0.0),
            aggregations=aggregations,
            captured_at=datetime.now(),
        )

        return snapshot

    def _post(self, cookie: str, path: str, payload: dict) -> Optional[httpx.Response]:
        try:
            with httpx.Client(timeout=self.TIMEOUT) as client:
                return client.post(
                    f"{self.BASE_URL}/{path}",
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Origin": "https://cursor.com",
                        "Referer": "https://cursor.com/cn/dashboard?tab=billing",
                        "Cookie": cookie,
                    },
                    json=payload,
                )
        except Exception as exc:
            self.last_error = f"network error: {exc}"
            logger.warning("Cursor dashboard request failed")
            return None
