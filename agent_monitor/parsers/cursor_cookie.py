"""Cursor cookie extraction helpers."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class CursorCookieProvider:
    """Provide Cursor dashboard cookies with light caching."""

    def __init__(self) -> None:
        self.last_error: Optional[str] = None

    def get_cookie(self) -> Optional[str]:
        """Return cookie header string for cursor.com, if available."""
        candidates = self.get_candidate_cookies()
        if not candidates:
            return None
        return candidates[0]

    def get_candidate_cookies(self) -> list[str]:
        """Return a list of candidate cookie headers in priority order."""
        file_cookie = self._load_cookie_file()
        if file_cookie:
            self.last_error = None
            return [self._normalize_cookie(file_cookie)]

        env_cookie = os.getenv("CURSOR_DASHBOARD_COOKIE")
        if env_cookie:
            self.last_error = None
            return [self._normalize_cookie(env_cookie)]
        self.last_error = "CURSOR_DASHBOARD_COOKIE not set"
        return []

    def _load_cookie_file(self) -> Optional[str]:
        path = os.getenv("CURSOR_DASHBOARD_COOKIE_FILE")
        if not path:
            return None
        try:
            content = Path(path).read_text(encoding="utf-8").strip()
        except Exception:
            self.last_error = "failed to read CURSOR_DASHBOARD_COOKIE_FILE"
            return None
        if not content:
            self.last_error = "CURSOR_DASHBOARD_COOKIE_FILE is empty"
            return None
        return content

    def _cookie_header_from_map(self, cookies: dict[str, str]) -> Optional[str]:
        if not cookies:
            return None
        if "WorkosCursorSessionToken" not in cookies:
            return None
        preferred = [
            "WorkosCursorSessionToken",
            "cursor_anonymous_id",
            "htjs_anonymous_id",
            "htjs_sesh",
        ]
        ordered = []
        for name in preferred:
            if name in cookies:
                ordered.append(f"{name}={cookies[name]}")
        for name, value in cookies.items():
            if name in preferred:
                continue
            ordered.append(f"{name}={value}")
        return "; ".join(ordered)

    def _normalize_cookie(self, cookie: str) -> str:
        cookie = cookie.strip()
        if (cookie.startswith('"') and cookie.endswith('"')) or (
            cookie.startswith("'") and cookie.endswith("'")
        ):
            cookie = cookie[1:-1]
        return cookie
